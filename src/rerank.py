from __future__ import annotations

import re

from src.search import Hit

RERANK_WEIGHT = 0.15
STOP_WORDS = {
    "a",
    "after",
    "ago",
    "already",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "before",
    "by",
    "can",
    "could",
    "day",
    "days",
    "did",
    "do",
    "does",
    "for",
    "from",
    "get",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "just",
    "long",
    "me",
    "much",
    "my",
    "need",
    "of",
    "on",
    "or",
    "our",
    "same",
    "still",
    "take",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "two",
    "us",
    "was",
    "we",
    "week",
    "weeks",
    "what",
    "when",
    "which",
    "with",
    "you",
    "your",
}
TERM_RE = re.compile(r"[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]")


def terms(text: str) -> list[str]:
    out: list[str] = []
    for match in TERM_RE.findall(text.lower()):
        word = match
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        out.append(word)
    return out


def question_terms(question: str) -> set[str]:
    return set(terms(question)) - STOP_WORDS


def rerank(index, question: str, hits: list[Hit]) -> list[Hit]:
    q_terms = question_terms(question)
    scored: list[Hit] = []
    for hit in hits:
        shared = sorted(q_terms & index.terms[hit.chunk_id])
        boost = RERANK_WEIGHT * sum(index.idf[word] ** 2 for word in shared)
        score = hit.similarity + boost
        scored.append(
            Hit(
                chunk_id=hit.chunk_id,
                similarity=hit.similarity,
                boost=boost,
                score=score,
            )
        )
    scored.sort(key=lambda item: (-item.score, item.chunk_id))
    return scored
