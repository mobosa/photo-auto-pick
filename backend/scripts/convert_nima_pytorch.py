"""Convert NIMA Keras HDF5 weights to ONNX using PyTorch.

Reads MobileNet v1 weights from idealo/image-quality-assessment,
builds equivalent PyTorch model, exports to ONNX.
"""

import sys
from pathlib import Path

import h5py
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

WEIGHTS_PATH = Path(r"D:\xm\photo-auto-pick\backend\weights\temp_clone\models\MobileNet\weights_mobilenet_aesthetic_0.07.hdf5")
OUTPUT_PATH = Path(r"D:\xm\photo-auto-pick\backend\weights\nima_mobilenet.onnx")


class DepthwiseSeparable(nn.Module):
    """Depthwise separable conv: depthwise + pointwise, each with BN + ReLU."""
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.dw = nn.Conv2d(in_ch, in_ch, 3, stride, 1, groups=in_ch, bias=False)
        self.dw_bn = nn.BatchNorm2d(in_ch)
        self.pw = nn.Conv2d(in_ch, out_ch, 1, bias=False)
        self.pw_bn = nn.BatchNorm2d(out_ch)

    def forward(self, x):
        x = F.relu(self.dw_bn(self.dw(x)), inplace=True)
        x = F.relu(self.pw_bn(self.pw(x)), inplace=True)
        return x


class NIMAMobileNet(nn.Module):
    """MobileNet v1 (alpha=1.0) + GlobalAvgPool + Dense(10)."""
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, 2, 1, bias=False)
        self.conv1_bn = nn.BatchNorm2d(32)

        # MobileNet v1 blocks: (in, out, stride)
        cfg = [
            (32, 64, 1),    # conv_dw/pw_1
            (64, 128, 2),   # 2
            (128, 128, 1),  # 3
            (128, 256, 2),  # 4
            (256, 256, 1),  # 5
            (256, 512, 2),  # 6
            (512, 512, 1),  # 7
            (512, 512, 1),  # 8
            (512, 512, 1),  # 9
            (512, 512, 1),  # 10
            (512, 512, 1),  # 11
            (512, 1024, 2), # 12
            (1024, 1024, 1),# 13
        ]
        self.blocks = nn.ModuleList([
            DepthwiseSeparable(i, o, s) for i, o, s in cfg
        ])
        self.fc = nn.Linear(1024, 10)

    def forward(self, x):
        # Input: (B, 3, 224, 224) — already preprocessed (float32, /127.5 -1)
        x = F.relu(self.conv1_bn(self.conv1(x)), inplace=True)
        for block in self.blocks:
            x = block(x)
        x = F.adaptive_avg_pool2d(x, 1).flatten(1)
        x = self.fc(x)
        return F.softmax(x, dim=1)


def load_hdf5_weights(model: NIMAMobileNet, hdf5_path: Path):
    """Load Keras HDF5 weights into PyTorch model."""
    f = h5py.File(str(hdf5_path), 'r')

    def get(name):
        return np.array(f[name])

    # conv1: Keras (H,W,C_in,C_out) -> PyTorch (C_out,C_in,H,W)
    w = get('conv1/conv1/kernel:0')
    model.conv1.weight.data.copy_(torch.from_numpy(w.transpose(3, 2, 0, 1)))
    _load_bn(model.conv1_bn, f, 'conv1_bn/conv1_bn')

    # depthwise separable blocks
    for i, block in enumerate(model.blocks, 1):
        # depthwise conv: Keras (H,W,C_in,1) -> PyTorch (C_in,1,H,W)
        dw_w = get(f'conv_dw_{i}/conv_dw_{i}/depthwise_kernel:0')
        block.dw.weight.data.copy_(torch.from_numpy(dw_w.transpose(2, 3, 0, 1)))
        _load_bn(block.dw_bn, f, f'conv_dw_{i}_bn/conv_dw_{i}_bn')

        # pointwise conv: Keras (1,1,C_in,C_out) -> PyTorch (C_out,C_in,1,1)
        pw_w = get(f'conv_pw_{i}/conv_pw_{i}/kernel:0')
        block.pw.weight.data.copy_(torch.from_numpy(pw_w.transpose(3, 2, 0, 1)))
        _load_bn(block.pw_bn, f, f'conv_pw_{i}_bn/conv_pw_{i}_bn')

    # dense layer: Keras (1024,10) -> PyTorch (10,1024)
    model.fc.weight.data.copy_(torch.from_numpy(get('dense_1/dense_1/kernel:0').T))
    model.fc.bias.data.copy_(torch.from_numpy(get('dense_1/dense_1/bias:0')))

    f.close()


def _load_bn(bn_layer, f, prefix):
    """Load BatchNorm weights from HDF5."""
    bn_layer.weight.data.copy_(torch.from_numpy(np.array(f[f'{prefix}/gamma:0'])))
    bn_layer.bias.data.copy_(torch.from_numpy(np.array(f'{prefix}/beta:0')))
    bn_layer.running_mean.copy_(torch.from_numpy(np.array(f[f'{prefix}/moving_mean:0'])))
    bn_layer.running_var.copy_(torch.from_numpy(np.array(f[f'{prefix}/moving_variance:0'])))
    bn_layer.num_batches_tracked.fill_(0)


def main():
    print(f"Loading weights from {WEIGHTS_PATH}...")
    model = NIMAMobileNet()
    model.eval()
    load_hdf5_weights(model, WEIGHTS_PATH)

    # Verify: run dummy input
    dummy = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        out = model(dummy)
    probs = out.numpy()[0]
    mean_score = float(np.sum(probs * np.arange(1, 11)))
    print(f"  Output shape: {out.shape}")
    print(f"  Softmax sum:  {probs.sum():.6f}")
    print(f"  Sample score: {mean_score:.2f} / 10.0")

    print(f"Exporting to ONNX...")
    torch.onnx.export(
        model,
        dummy,
        str(OUTPUT_PATH),
        opset_version=13,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    )

    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"\nDone! Saved to {OUTPUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
