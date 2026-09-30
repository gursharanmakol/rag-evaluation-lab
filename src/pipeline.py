from __future__ import annotations

from dataclasses import dataclass

from src.embed import count_tokens
from src.rerank import rerank
from src.search import Hit

CANDIDATES = 20
TOP_K = 3
CONTEXT_BUDGET = 500


@dataclass
class Retrieval:
    candidates: list[Hit]
    reranked: list[Hit]
    ranked: list[Hit]
    kept: list[Hit]


@dataclass
class Assembly:
    budget: int
    history_tokens: int
    items: list[tuple[str, int, str]]
    used_tokens: int


@dataclass
class Trace:
    question: str
    history: list[dict] | None
    retrieval: Retrieval
    assembly: Assembly
    prompt: str

    def to_dict(self) -> dict:
        def hit_candidate(hit: Hit) -> dict:
            return {
                "chunk": hit.chunk_id,
                "similarity": round(hit.similarity, 4),
            }

        def hit_reranked(hit: Hit) -> dict:
            return {
                "chunk": hit.chunk_id,
                "similarity": round(hit.similarity, 4),
                "boost": None if hit.boost is None else round(hit.boost, 4),
                "score": round(hit.score, 4),
            }

        return {
            "candidates": [hit_candidate(hit) for hit in self.retrieval.candidates],
            "reranked": [hit_reranked(hit) for hit in self.retrieval.reranked],
            "kept": [hit.chunk_id for hit in self.retrieval.kept],
            "assembly": {
                "budget": self.assembly.budget,
                "history_tokens": self.assembly.history_tokens,
                "chunks": [
                    {
                        "chunk": chunk_id,
                        "tokens": tokens,
                        "status": status,
                    }
                    for chunk_id, tokens, status in self.assembly.items
                ],
                "used_tokens": self.assembly.used_tokens,
            },
            "prompt": self.prompt,
        }


def retrieve(index, question, top_k=TOP_K):
    candidates = index.similar(question, CANDIDATES)
    reranked = rerank(index, question, candidates[:top_k])
    seen = {hit.chunk_id for hit in reranked}
    ranked = reranked + [hit for hit in candidates if hit.chunk_id not in seen]
    return Retrieval(
        candidates=candidates,
        reranked=reranked,
        ranked=ranked,
        kept=ranked[:top_k],
    )


def render_history(history) -> str:
    if not history:
        return ""
    return "\n".join(f"{turn['role']}: {turn['text']}" for turn in history)


def assemble(index, kept, history=None, budget=CONTEXT_BUDGET) -> Assembly:
    history_text = render_history(history)
    used = count_tokens(index.model, history_text) if history_text else 0
    history_tokens = used
    items: list[tuple[str, int, str]] = []
    cutting = False
    for hit in kept:
        tokens = index.tokens[hit.chunk_id]
        if cutting:
            items.append((hit.chunk_id, tokens, "cut"))
            continue
        if used + tokens <= budget:
            used += tokens
            items.append((hit.chunk_id, tokens, "reached"))
        else:
            cutting = True
            items.append((hit.chunk_id, tokens, "cut"))
    return Assembly(
        budget=budget,
        history_tokens=history_tokens,
        items=items,
        used_tokens=used,
    )


def render_prompt(index, question, history, assembly) -> str:
    lines = [
        "You are TechNova's support assistant. Answer the customer using the help center context below.",
        "",
    ]
    history_text = render_history(history)
    if history_text:
        lines.append("Conversation so far:")
        lines.append(history_text)
        lines.append("")
    lines.append("Help center context:")
    reached = [
        chunk_id
        for chunk_id, _tokens, status in assembly.items
        if status == "reached"
    ]
    if not reached:
        lines.append("(none)")
    else:
        for chunk_id in reached:
            chunk = index.chunks[chunk_id]
            lines.append(f"[{chunk_id}]")
            lines.append(chunk.text)
            lines.append("")
        if lines[-1] == "":
            lines.pop()
    lines.append("")
    lines.append(f"Customer: {question}")
    return "\n".join(lines)


def run(index, question, history=None, top_k=TOP_K) -> Trace:
    retrieval = retrieve(index, question, top_k=top_k)
    assembly = assemble(index, retrieval.kept, history=history)
    prompt = render_prompt(index, question, history, assembly)
    return Trace(
        question=question,
        history=history,
        retrieval=retrieval,
        assembly=assembly,
        prompt=prompt,
    )
