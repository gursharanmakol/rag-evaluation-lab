from __future__ import annotations

import argparse
import importlib.metadata
import sys
from pathlib import Path

from src.corpus import load_chunks
from src.embed import MODEL_DIR, count_tokens, load_model, verify_model_checksums

EXPECTED_PACKAGE_VERSIONS = {
    "model2vec": "0.9.0",
    "numpy": "2.5.3",
    "tokenizers": "0.23.2",
    "pyyaml": "6.0.3",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TechNova support assistant: evaluation lab"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("check", help="Check Python, packages, model, and help center")
    sub.add_parser("chunks", help="List help-center chunks")
    args = parser.parse_args()
    if args.command == "check":
        raise SystemExit(run_check())
    if args.command == "chunks":
        raise SystemExit(run_chunks())
    parser.print_help()


def run_check() -> int:
    print("TechNova support assistant: evaluation lab")
    version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    if not (sys.version_info.major == 3 and sys.version_info.minor == 12):
        print(f"[FAIL] Python 3.12 required, found {version}")
        return 1
    print(f"[OK] Python {version}")

    package_ok, package_lines = _package_status_lines()
    for line in package_lines:
        print(line)
    if not package_ok:
        return 1

    model_ok, model_lines = _model_status_lines()
    for line in model_lines:
        print(line)
    if not model_ok:
        return 1

    try:
        chunks = load_chunks()
        doc_ids = {chunk.doc_id for chunk in chunks}
        print(f"[OK] Help center: {len(doc_ids)} documents, {len(chunks)} chunks")
    except Exception as exc:
        print(f"[FAIL] Help center: {exc}")
        return 1

    print("Ready.")
    return 0


def run_chunks() -> int:
    chunks = load_chunks()
    model = load_model()
    for chunk in chunks:
        tokens = count_tokens(model, chunk.text)
        print(f"{chunk.id:<26} {tokens}   {chunk.title}: {chunk.heading}")
    return 0


def _package_status_lines() -> tuple[bool, list[str]]:
    lines: list[str] = []
    parts: list[str] = []
    for name, expected in EXPECTED_PACKAGE_VERSIONS.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return False, [f"[FAIL] Packages: {name} is not installed"]
        if actual != expected:
            lines.append(
                f"[WARN] {name} {actual} installed, the lab was tested with {expected}. Scores may differ."
            )
        parts.append(f"{name} {actual}")
    lines.append("[OK] Packages: " + ", ".join(parts))
    return True, lines


def _model_status_lines() -> tuple[bool, list[str]]:
    root = Path(MODEL_DIR)
    lines: list[str] = []
    if not root.is_dir():
        return False, [f"[FAIL] Embedding model: missing directory {MODEL_DIR}"]
    try:
        load_model(root)
    except Exception as exc:
        return False, [f"[FAIL] Embedding model: {exc}"]
    warnings = verify_model_checksums(root)
    if warnings:
        detail = "; ".join(warnings)
        lines.append(f"[WARN] Embedding model: {detail}. Scores may differ.")
        lines.append("[OK] Embedding model: potion-base-8M (checksum warning)")
        return True, lines
    lines.append("[OK] Embedding model: potion-base-8M (checksum matches)")
    return True, lines


if __name__ == "__main__":
    main()
