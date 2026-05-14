"""Convert NIMA Keras HDF5 weights to ONNX format.

Usage:
    python convert_nima_to_onnx.py --weights path/to/weights_mobilenet_aesthetic_0.11.hdf5

Requires (not in requirements.txt — install temporarily):
    pip install tensorflow>=2.15 tf2onnx>=1.16 h5py

The output file nima_mobilenet.onnx is placed in ../weights/ relative to this script.
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Convert NIMA Keras weights to ONNX")
    parser.add_argument("--weights", required=True, help="Path to .hdf5 weights file")
    parser.add_argument("--output", default=None, help="Output ONNX path (default: backend/weights/nima_mobilenet.onnx)")
    parser.add_argument("--alpha", type=float, default=1.0, help="MobileNet alpha (default 1.0)")
    args = parser.parse_args()

    weights_path = Path(args.weights)
    if not weights_path.exists():
        print(f"Error: weights file not found: {weights_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).resolve().parent.parent / "weights" / "nima_mobilenet.onnx"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading TensorFlow...")
    import tensorflow as tf
    from tensorflow.keras.layers import Dense, Dropout
    from tensorflow.keras.models import Model

    print(f"Building NIMA MobileNet (alpha={args.alpha})...")
    base = tf.keras.applications.MobileNet(
        include_top=False,
        pooling="avg",
        alpha=args.alpha,
        input_shape=(224, 224, 3),
    )
    x = base.output
    x = Dropout(0.75)(x)
    x = Dense(10, activation="softmax")(x)
    model = Model(inputs=base.input, outputs=x)

    print(f"Loading weights from {weights_path}...")
    model.load_weights(str(weights_path))

    print("Converting to ONNX...")
    import tf2onnx
    import numpy as np

    spec = (tf.TensorSpec((None, 224, 224, 3), tf.float32, name="input"),)
    model_proto, _ = tf2onnx.convert.from_keras(
        model,
        input_signature=spec,
        opset=13,
        output_path=str(output_path),
    )

    print(f"Verifying ONNX model...")
    import onnxruntime as ort
    session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
    dummy = np.random.randn(1, 224, 224, 3).astype(np.float32)
    result = session.run(None, {session.get_inputs()[0].name: dummy})
    probs = result[0][0]
    print(f"  Output shape: {result[0].shape}")
    print(f"  Softmax sum:  {probs.sum():.6f} (should be ~1.0)")
    mean_score = float(np.sum(probs * np.arange(1, 11)))
    print(f"  Sample score: {mean_score:.2f} / 10.0")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nDone! ONNX model saved to: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
