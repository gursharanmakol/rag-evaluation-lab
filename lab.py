from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
from pathlib import Path

EXPECTED_PACKAGE_VERSIONS = {
    "model2vec": "0.9.0",
    "numpy": "2.5.3",
    "tokenizers": "0.23.2",
    "pyyaml": "6.0.3",
}
QUESTION_ID_RE = re.compile(r"Q\d+", re.IGNORECASE)
INCIDENT_ID_RE = re.compile(r"I[A-Za-z0-9]+", re.IGNORECASE)


def _load_project_imports() -> None:
    """Import project modules after the Python version gate."""
    global evaluate, load_questions, load_chunks, MODEL_DIR, count_tokens
    global load_model, verify_model_checksums, run, format_evaluation
    global format_incident_list, format_trace, build_index
    from eval.metrics import evaluate, load_questions
    from src.corpus import load_chunks
    from src.embed import MODEL_DIR, count_tokens, load_model, verify_model_checksums
    from src.pipeline import run
    from src.report import format_evaluation, format_incident_list, format_trace
    from src.search import build_index


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TechNova support assistant: evaluation lab"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("check", help="Check Python, packages, model, and help center")
    sub.add_parser("chunks", help="List help-center chunks")
    sub.add_parser("evaluate", help="Score the evaluation questions")
    inspect_parser = sub.add_parser("inspect", help="Run a live question trace")
    inspect_parser.add_argument("arg")
    trace_parser = sub.add_parser("trace", help="Show a recorded incident trace")
    trace_parser.add_argument("incident_id", nargs="?")
    args = parser.parse_args()

    if args.command is None:
        _run(parser.print_help)
        return

    if not (sys.version_info.major == 3 and sys.version_info.minor == 12):
        version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

        def _bad_python() -> int:
            print("TechNova support assistant: evaluation lab")
            print(f"[FAIL] Python 3.12 required, found {version}")
            return 1

        raise SystemExit(_run(_bad_python))

    _load_project_imports()

    if args.command == "check":
        raise SystemExit(_run(run_check))
    if args.command == "chunks":
        raise SystemExit(_run(run_chunks))
    if args.command == "evaluate":
        raise SystemExit(_run(run_evaluate))
    if args.command == "inspect":
        raise SystemExit(_run(run_inspect, args.arg))
    if args.command == "trace":
        raise SystemExit(_run(run_trace, args.incident_id))
    _run(parser.print_help)


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

    try:
        questions = load_questions()
        print(f"[OK] Evaluation questions: {len(questions)}")
    except Exception as exc:
        print(f"[FAIL] Evaluation questions: {exc}")
        return 1

    incident_count = _incident_count()
    print(f"[OK] Incidents: {incident_count}")

    print("Ready. Next: uv run python lab.py evaluate")
    return 0


def run_chunks() -> int:
    chunks = load_chunks()
    model = load_model()
    for chunk in chunks:
        tokens = count_tokens(model, chunk.text)
        print(f"{chunk.id:<26} {tokens}   {chunk.title}: {chunk.heading}")
    return 0


def run_evaluate() -> int:
    index = build_index()
    questions = load_questions()
    result = evaluate(index, questions)
    print(format_evaluation(result))
    return 0


def run_inspect(arg: str) -> int:
    questions = load_questions()
    by_id = {item["id"].lower(): item for item in questions}
    expected = None
    if QUESTION_ID_RE.fullmatch(arg):
        item = by_id.get(arg.lower())
        if item is None:
            print(f"[FAIL] Unknown question id {arg}")
            return 1
        question = item["question"]
        expected = item["expected"]
    else:
        question = arg

    index = build_index()
    trace = run(index, question, history=None)
    record = {
        "question": question,
        "trace": trace.to_dict(),
    }
    print(format_trace(record, expected=expected, live=True))
    return 0


def run_trace(incident_id: str | None) -> int:
    records = _load_incident_records()
    if incident_id is None:
        if not records:
            print("No incidents recorded.")
        else:
            print(format_incident_list(records))
        return 0

    if INCIDENT_ID_RE.fullmatch(incident_id):
        match = next(
            (record for record in records if record["id"].lower() == incident_id.lower()),
            None,
        )
        if match is None:
            print(f"[FAIL] Unknown incident id {incident_id}")
            return 1
        print(format_trace(match, expected=None, live=False))
        return 0

    match = next(
        (record for record in records if record["id"].lower() == incident_id.lower()),
        None,
    )
    if match is None:
        print(f"[FAIL] Unknown incident id {incident_id}")
        return 1
    print(format_trace(match, expected=None, live=False))
    return 0


def _run(func, *args) -> int:
    print()
    try:
        code = func(*args)
    finally:
        print()
    return 0 if code is None else code


def _incident_count() -> int:
    root = Path("incidents")
    if not root.is_dir():
        return 0
    return len(list(root.glob("*.json")))


def _load_incident_records() -> list[dict]:
    root = Path("incidents")
    if not root.is_dir():
        return []
    records: list[dict] = []
    for path in sorted(root.glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    records.sort(key=lambda item: item.get("id", ""))
    return records


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
