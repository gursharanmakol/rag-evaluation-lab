from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    title: str
    heading: str
    body: str
    text: str


def load_chunks(corpus_dir: str | Path = "corpus") -> list[Chunk]:
    root = Path(corpus_dir)
    chunks: list[Chunk] = []
    for path in sorted(root.glob("*.md")):
        chunks.extend(_load_file(path))
    return chunks


def _load_file(path: Path) -> list[Chunk]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"{path.name}: missing document title")
    title = lines[0][2:].strip()
    doc_id = path.stem

    sections: list[tuple[str, str, str]] = []
    current_id: str | None = None
    current_heading: str | None = None
    body_lines: list[str] = []

    def flush() -> None:
        nonlocal current_id, current_heading, body_lines
        if current_id is None or current_heading is None:
            return
        trimmed = list(body_lines)
        while trimmed and trimmed[0].strip() == "":
            trimmed.pop(0)
        while trimmed and trimmed[-1].strip() == "":
            trimmed.pop()
        body = "\n".join(trimmed)
        sections.append((current_id, current_heading, body))
        current_id = None
        current_heading = None
        body_lines = []

    for line in lines[1:]:
        if line.startswith("## "):
            flush()
            heading_line = line[3:]
            marker = " {#"
            if marker not in heading_line or not heading_line.endswith("}"):
                raise ValueError(f"{path.name}: bad section heading: {line}")
            heading, _, rest = heading_line.partition(marker)
            current_heading = heading
            current_id = rest[:-1]
            body_lines = []
        elif current_id is not None:
            body_lines.append(line)
    flush()

    out: list[Chunk] = []
    for section_id, heading, body in sections:
        chunk_id = f"{doc_id}#{section_id}"
        text = f"{title}: {heading}\n\n{body}"
        out.append(
            Chunk(
                id=chunk_id,
                doc_id=doc_id,
                title=title,
                heading=heading,
                body=body,
                text=text,
            )
        )
    return out
