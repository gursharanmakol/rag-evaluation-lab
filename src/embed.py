from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np
from model2vec import StaticModel

MODEL_DIR = "models/potion-base-8M"
MODEL_SHA256 = {
    "model.safetensors": "f65d0f325faadc1e121c319e2faa41170d3fa07d8c89abd48ca5358d9a223de2",
    "tokenizer.json": "273ca9e28ec6990aea6206b0364443754d87e87a5dd28e94026ea9999ba3bf62",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_model_checksums(model_dir: str | Path = MODEL_DIR) -> list[str]:
    root = Path(model_dir)
    warnings: list[str] = []
    for name, expected in MODEL_SHA256.items():
        path = root / name
        if not path.is_file():
            warnings.append(f"missing {name}")
            continue
        actual = _sha256(path)
        if actual != expected:
            warnings.append(f"{name} checksum mismatch")
    return warnings


def load_model(model_dir: str | Path = MODEL_DIR) -> StaticModel:
    os.environ["HF_HUB_OFFLINE"] = "1"
    root = Path(model_dir)
    required = ["config.json", "model.safetensors", "tokenizer.json"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"embedding model incomplete under {root}: missing {', '.join(missing)}"
        )
    return StaticModel.from_pretrained(str(root))


def embed_texts(model: StaticModel, texts) -> np.ndarray:
    encoded = model.encode(list(texts))
    matrix = np.asarray(encoded, dtype=np.float32)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.maximum(norms, np.float32(1e-12))
    return (matrix / norms).astype(np.float32)


def count_tokens(model: StaticModel, text: str) -> int:
    return len(model.tokenizer.encode(text, add_special_tokens=False).ids)
