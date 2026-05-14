"""Convert NIMA MobileNet v1 Keras HDF5 weights to ONNX.

Builds the ONNX computation graph directly using onnx helper functions,
avoiding TensorFlow/PyTorch DLL issues.
"""

import sys
from pathlib import Path

import h5py
import numpy as np
import onnx
from onnx import helper, TensorProto, numpy_helper

WEIGHTS_PATH = Path(r"D:\xm\photo-auto-pick\backend\weights\temp_clone\models\MobileNet\weights_mobilenet_aesthetic_0.07.hdf5")
OUTPUT_PATH = Path(r"D:\xm\photo-auto-pick\backend\weights\nima_mobilenet.onnx")


def _fused_bn_conv_weight(conv_w, bn_gamma, bn_beta, bn_mean, bn_var, eps=1e-5):
    """Fuse Conv + BatchNorm into a single conv with bias.

    conv_w: (C_out, C_in, H, W) for regular; (C_in, 1, H, W) for depthwise
    Returns: (fused_w, fused_bias)
    """
    scale = bn_gamma / np.sqrt(bn_var + eps)
    # Reshape scale for broadcasting with conv weight
    if conv_w.ndim == 4:
        # For both regular and depthwise: scale broadcasts along axis 0 (out_channels)
        shape = [-1] + [1] * (conv_w.ndim - 1)
        fused_w = conv_w * scale.reshape(shape)
    fused_bias = bn_beta - bn_mean * scale
    return fused_w.astype(np.float32), fused_bias.astype(np.float32)


def _make_conv_bn_relu(nodes, tensors, input_name, conv_w, bn_params, out_name, strides, pads, group=1):
    """Create Conv -> BN -> Relu subgraph. Returns output tensor name."""
    conv_name = out_name + "_conv"
    bn_name = out_name + "_bn"
    relu_name = out_name

    bn_gamma, bn_beta, bn_mean, bn_var = bn_params
    fused_w, fused_b = _fused_bn_conv_weight(conv_w, bn_gamma, bn_beta, bn_mean, bn_var)

    tensors.append(numpy_helper.from_array(fused_w, conv_name + "_w"))
    tensors.append(numpy_helper.from_array(fused_b, conv_name + "_b"))

    conv_node = helper.make_node(
        "Conv", [input_name, conv_name + "_w", conv_name + "_b"], [conv_name],
        kernel_shape=list(fused_w.shape[2:]),
        strides=strides, pads=pads, group=group,
    )
    relu_node = helper.make_node("Relu", [conv_name], [relu_name])

    nodes.extend([conv_node, relu_node])
    return relu_name


def build_onnx_model(hdf5_path):
    """Build NIMA MobileNet v1 ONNX model from HDF5 weights."""
    f = h5py.File(str(hdf5_path), 'r')

    def get(name):
        return np.array(f[name]).astype(np.float32)

    nodes = []
    tensors = []  # initializers

    # MobileNet v1 block config: (in_ch, out_ch, stride)
    blocks_cfg = [
        (32, 64, 1), (64, 128, 2), (128, 128, 1),
        (128, 256, 2), (256, 256, 1), (256, 512, 2),
        (512, 512, 1), (512, 512, 1), (512, 512, 1),
        (512, 512, 1), (512, 512, 1), (512, 1024, 2),
        (1024, 1024, 1),
    ]

    prev_name = "input"

    # --- Conv1: 3->32, stride 2 ---
    conv1_w = get('conv1/conv1/kernel:0').transpose(3, 2, 0, 1)  # (32,3,3,3)
    bn1 = (get('conv1_bn/conv1_bn/gamma:0'),
           get('conv1_bn/conv1_bn/beta:0'),
           get('conv1_bn/conv1_bn/moving_mean:0'),
           get('conv1_bn/conv1_bn/moving_variance:0'))
    prev_name = _make_conv_bn_relu(
        nodes, tensors, prev_name, conv1_w, bn1, "conv1_out",
        strides=[2, 2], pads=[1, 1, 1, 1],
    )

    # --- Depthwise Separable Blocks ---
    for i, (in_ch, out_ch, stride) in enumerate(blocks_cfg, 1):
        # Depthwise conv
        dw_w = get(f'conv_dw_{i}/conv_dw_{i}/depthwise_kernel:0').transpose(2, 3, 0, 1)  # (C,1,H,W)
        dw_bn = (get(f'conv_dw_{i}_bn/conv_dw_{i}_bn/gamma:0'),
                 get(f'conv_dw_{i}_bn/conv_dw_{i}_bn/beta:0'),
                 get(f'conv_dw_{i}_bn/conv_dw_{i}_bn/moving_mean:0'),
                 get(f'conv_dw_{i}_bn/conv_dw_{i}_bn/moving_variance:0'))

        dw_out = f"dw{i}_out"
        prev_name = _make_conv_bn_relu(
            nodes, tensors, prev_name, dw_w, dw_bn, dw_out,
            strides=[stride, stride], pads=[1, 1, 1, 1], group=in_ch,
        )

        # Pointwise conv
        pw_w = get(f'conv_pw_{i}/conv_pw_{i}/kernel:0').transpose(3, 2, 0, 1)  # (out,in,1,1)
        pw_bn = (get(f'conv_pw_{i}_bn/conv_pw_{i}_bn/gamma:0'),
                 get(f'conv_pw_{i}_bn/conv_pw_{i}_bn/beta:0'),
                 get(f'conv_pw_{i}_bn/conv_pw_{i}_bn/moving_mean:0'),
                 get(f'conv_pw_{i}_bn/conv_pw_{i}_bn/moving_variance:0'))

        pw_out = f"pw{i}_out"
        prev_name = _make_conv_bn_relu(
            nodes, tensors, prev_name, pw_w, pw_bn, pw_out,
            strides=[1, 1], pads=[0, 0, 0, 0],
        )

    # --- Global Average Pooling ---
    gap_out = "gap_out"
    nodes.append(helper.make_node("GlobalAveragePool", [prev_name], [gap_out]))
    prev_name = gap_out

    # --- Flatten ---
    flat_out = "flat_out"
    nodes.append(helper.make_node("Flatten", [prev_name], [flat_out]))
    prev_name = flat_out

    # --- Dense layer (no dropout at inference) ---
    dense_w = get('dense_1/dense_1/kernel:0').astype(np.float32)  # (1024, 10)
    dense_b = get('dense_1/dense_1/bias:0').astype(np.float32)  # (10,)
    tensors.append(numpy_helper.from_array(dense_w, "fc_w"))
    tensors.append(numpy_helper.from_array(dense_b, "fc_b"))

    matmul_out = "matmul_out"
    add_out = "add_out"
    nodes.append(helper.make_node("MatMul", [prev_name, "fc_w"], [matmul_out]))
    nodes.append(helper.make_node("Add", [matmul_out, "fc_b"], [add_out]))

    # --- Softmax ---
    output_name = "output"
    nodes.append(helper.make_node("Softmax", [add_out], [output_name], axis=1))

    f.close()

    # Build graph
    input_tensor = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, 224, 224])
    output_tensor = helper.make_tensor_value_info(output_name, TensorProto.FLOAT, [1, 10])

    graph = helper.make_graph(nodes, "nima_mobilenet", [input_tensor], [output_tensor], tensors)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    return model


def main():
    print(f"Loading weights from {WEIGHTS_PATH}...")
    model = build_onnx_model(WEIGHTS_PATH)

    print("Validating ONNX model...")
    onnx.checker.check_model(model)

    onnx.save(model, str(OUTPUT_PATH))
    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Saved to {OUTPUT_PATH} ({size_mb:.1f} MB)")

    # Verify with onnxruntime
    import onnxruntime as ort
    from app.utils.onnx_provider import get_providers
    session = ort.InferenceSession(str(OUTPUT_PATH), providers=get_providers())
    dummy = np.random.randn(1, 3, 224, 224).astype(np.float32)
    result = session.run(None, {"input": dummy})
    probs = result[0][0]
    mean_score = float(np.sum(probs * np.arange(1, 11)))
    print(f"  Output shape: {result[0].shape}")
    print(f"  Softmax sum:  {probs.sum():.6f}")
    print(f"  Sample score: {mean_score:.2f} / 10.0")
    print("\nDone!")


if __name__ == "__main__":
    main()
