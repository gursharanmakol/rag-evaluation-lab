from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
from datetime import datetime

from src.pipeline import TOP_K

_RED = "\033[31m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"
_RESET = "\033[0m"
_CHUNK_HEADER = re.compile(
    r"^\[([A-Za-z0-9][A-Za-z0-9-]*#[A-Za-z0-9][A-Za-z0-9.-]*)\]$"
)
_VT_READY: bool | None = None


def format_evaluation(result) -> str:
    n = len(result.questions)
    lines = [
        (
            f"Evaluation: {n} questions. Keep top {result.top_k}. "
            f"Context budget {result.budget} tokens (lab tokenizer)."
        ),
        (
            "Goal: every expected chunk should be in the kept top 3, "
            "and every kept chunk should reach the prompt."
        ),
        "",
        (
            f"{'ID':<4}  {'Expected':<26} {'Position':<9} {'Top 3':<6} "
            f"{'Top 10':<7} {'RR':<5}  Kept chunks in prompt"
        ),
    ]
    for row in result.questions:
        if row.position is None:
            pos = "-"
            rr = "0.00"
        else:
            pos = str(row.position)
            rr = f"{row.rr:.2f}"
        top3 = "yes" if row.in_top_3 else "no"
        top10 = "yes" if row.in_top_10 else "no"
        kept_prompt = f"{len(row.reached)} of {len(row.kept)}"
        lines.append(
            f"{row.id:<4}  {row.expected:<26} {pos:<9} {top3:<6} "
            f"{top10:<7} {rr:<5}  {kept_prompt}"
        )

    failures = [row for row in result.questions if not row.retrieved]
    if failures:
        lines.append("")
        lines.append("Retrieval failures")
        for row in failures:
            pos = "-" if row.position is None else str(row.position)
            lines.append(f"  {row.id}  {row.question}")
            lines.append(f"       expected  {row.expected} (position {pos})")
            lines.append(f"       kept      {', '.join(row.kept)}")

    assembly_failures = [row for row in result.questions if row.cut]
    if assembly_failures:
        lines.append("")
        lines.append("Assembly failures")
        for row in assembly_failures:
            cut_ids = ", ".join(row.cut)
            lines.append(
                f"  {row.id}  cut  {cut_ids}  "
                f"({row.used_tokens} of {result.budget} tokens used before the cut)"
            )

    retrieval_pass = result.retrieval_passed == n and n > 0
    assembly_pass = result.cut_total == 0
    retrieval_status = "PASS" if retrieval_pass else "FAIL"
    assembly_status = "PASS" if assembly_pass else "FAIL"
    recall3 = f"{int(round(result.recall_at_3 * 100))}%"
    recall10 = f"{int(round(result.recall_at_10 * 100))}%"
    mrr = f"{result.mrr:.2f}"

    lines.extend(
        [
            "",
            "Summary",
            "",
            f"Retrieval check    expected chunk in the kept top {result.top_k}",
            _with_status(
                f"                   {result.retrieval_passed} of {n} questions",
                retrieval_status,
            ),
            f"                   recall@3 {recall3}   recall@10 {recall10}   MRR {mrr}",
            "",
            "Assembly check     every kept chunk reached the prompt intact",
            _with_status(
                (
                    f"(invariant)        {result.reached_total} of {result.kept_total} "
                    f"kept chunks, {result.cut_total} cut"
                ),
                assembly_status,
            ),
        ]
    )
    return "\n".join(lines)


def _with_status(left: str, status: str, width: int = 70) -> str:
    pad = width - len(left) - len(status)
    if pad < 1:
        pad = 1
    return left + (" " * pad) + _style_status(status)


def _style_status(status: str) -> str:
    if status != "FAIL" or not _stdout_supports_color():
        return status
    return f"{_RED}{status}{_RESET}"


def _paint(text: str, code: str) -> str:
    if not _stdout_supports_color():
        return text
    return f"{code}{text}{_RESET}"


def _heading(text: str) -> str:
    return _paint(text, _BOLD)


def _chunk(chunk_id: str, width: int | None = None) -> str:
    shown = _paint(chunk_id, _CYAN)
    if width is None:
        return shown
    pad = width - len(chunk_id)
    if pad < 0:
        pad = 0
    return shown + (" " * pad)


def _status_word(status: str) -> str:
    if status == "reached":
        return _paint(status, _GREEN)
    if status == "cut":
        return _paint(status, _RED)
    return status


def _style_prompt_line(line: str) -> str:
    match = _CHUNK_HEADER.fullmatch(line)
    if match is None:
        return f"  {line}"
    return f"  [{_chunk(match.group(1))}]"


def _fit_prompt_line(text: str) -> list[str]:
    """Indent one prompt line, wrapping it inside the terminal window.

    A Windows console drops the character in the last column when a line wraps,
    and some hosts then discard the rest of that line. Stay one column short of
    the window so the whole sentence stays visible.
    """
    if _CHUNK_HEADER.fullmatch(text):
        return [_style_prompt_line(text)]
    indent = "  "
    if not sys.stdout.isatty():
        return [indent + text]
    columns = shutil.get_terminal_size(fallback=(0, 0)).columns
    if columns < 20 or len(indent) + len(text) < columns:
        return [indent + text]
    room = columns - len(indent) - 1
    parts = textwrap.wrap(
        text,
        width=room,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not parts:
        return [indent]
    return [indent + part for part in parts]


def _stdout_supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    stream = sys.stdout
    try:
        is_tty = stream is not None and stream.isatty()
    except (AttributeError, ValueError, OSError):
        return False
    if not is_tty:
        return False
    if sys.platform != "win32":
        return True
    return _windows_virtual_terminal_ready()


def _windows_virtual_terminal_ready() -> bool:
    global _VT_READY
    if _VT_READY is not None:
        return _VT_READY
    _VT_READY = False
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetStdHandle.argtypes = (ctypes.c_ulong,)
        kernel32.GetStdHandle.restype = ctypes.c_void_p
        kernel32.GetConsoleMode.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
        )
        kernel32.GetConsoleMode.restype = ctypes.c_int
        kernel32.SetConsoleMode.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        kernel32.SetConsoleMode.restype = ctypes.c_int

        handle = kernel32.GetStdHandle(ctypes.c_ulong(0xFFFFFFF5))
        if not handle:
            return False
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False
        enable_vt = 0x0004
        if mode.value & enable_vt:
            _VT_READY = True
            return True
        if kernel32.SetConsoleMode(handle, mode.value | enable_vt) == 0:
            return False
        _VT_READY = True
        return True
    except (AttributeError, OSError, ValueError):
        return False


def format_trace(record, expected=None, live=False) -> str:
    lines: list[str] = []
    if live:
        lines.append("Live run on the current code.")
        lines.append("")
    else:
        logged = _format_logged_at(record.get("logged_at", ""))
        channel = record.get("channel", "")
        lines.append(
            f"{_heading('Incident ' + str(record['id']))}   logged {logged}   {channel}"
        )
        lines.append("Recorded trace. This is what the assistant did at the time.")
        lines.append("")

    question = record["question"]
    lines.append(_heading("Question"))
    lines.append(f"  {question}")
    lines.append("")

    trace = record["trace"]
    candidates = trace["candidates"]
    reranked = trace["reranked"]
    kept = trace["kept"]
    assembly = trace["assembly"]

    lines.append(_heading(f"1. Candidates by similarity ({len(candidates)})"))
    lines.append(f"     {'#':<3} {'chunk':<26} similarity")
    for index, hit in enumerate(candidates, start=1):
        marker = ">" if expected is not None and hit["chunk"] == expected else " "
        lines.append(
            f"    {index:>2}{marker}  {_chunk(hit['chunk'], 26)} "
            f"{float(hit['similarity']):.3f}"
        )
    lines.append("")

    lines.append(_heading("2. After reranking (score = similarity + keyword boost)"))
    lines.append(
        f"     {'#':<3} {'chunk':<26} {'similarity':<11} {'boost':<7} score"
    )
    for index, hit in enumerate(reranked, start=1):
        marker = ">" if expected is not None and hit["chunk"] == expected else " "
        boost = hit.get("boost")
        boost_text = "none" if boost is None else f"{float(boost):.3f}"
        lines.append(
            f"    {index:>2}{marker}  {_chunk(hit['chunk'], 26)} "
            f"{float(hit['similarity']):<11.3f} {boost_text:<7} {float(hit['score']):.3f}"
        )
    lines.append("")

    lines.append(_heading(f"3. Kept (top {TOP_K})"))
    lines.append(f"     {', '.join(_chunk(chunk_id) for chunk_id in kept)}")
    lines.append("")

    budget = assembly["budget"]
    lines.append(
        _heading(
            f"4. Prompt assembly (context budget {budget} tokens, lab tokenizer)"
        )
    )
    lines.append(
        f"     {'conversation history':<28} {assembly['history_tokens']:>5}"
    )
    for item in assembly["chunks"]:
        lines.append(
            f"     {_chunk(item['chunk'], 28)} {item['tokens']:>5}   "
            f"{_status_word(item['status'])}"
        )
    lines.append(
        f"     {'total':<28} {assembly['used_tokens']:>5} of {budget}"
    )

    if not live:
        lines.append("")
        lines.append(_heading("5. Prompt sent to the model"))
        lines.append("  ------------------------------------------------------------")
        prompt = trace.get("prompt", "")
        for prompt_line in prompt.splitlines() or [""]:
            lines.extend(_fit_prompt_line(prompt_line))
        lines.append("  ------------------------------------------------------------")
        lines.append("")
        lines.append(_heading("6. Recorded answer"))
        answer = record.get("answer", "")
        for answer_line in str(answer).splitlines() or [""]:
            lines.append(f"  {answer_line}")
        lines.append("")
        lines.append(_heading("Support note"))
        note = record.get("support_note", "")
        for note_line in str(note).splitlines() or [""]:
            lines.append(f"  {note_line}")

    return "\n".join(lines)


def format_incident_list(records) -> str:
    if not records:
        return "No incidents recorded."
    lines: list[str] = []
    for record in records:
        logged = _format_logged_at(record.get("logged_at", ""))
        lines.append(
            f"{record['id']:<4}  {logged:<16}  {record.get('question', '')}"
        )
    return "\n".join(lines)


def _format_logged_at(value: str) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value.replace("T", " ")
    return dt.strftime("%Y-%m-%d %H:%M")
