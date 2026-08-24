from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from src.corpus import Chunk, load_chunks
from src.embed import count_tokens, embed_texts, load_model


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    similarity: float
    boost: float | None = None
    score: float = 0.0


@dataclass
class Index:
    chunks: dict[str, Chunk]
    ids: list[str]
    matrix: np.ndarray
    model: object
    tokens: dict[str, int]
    terms: dict[str, set[str]]
    idf: dict[str, float]

    def similar(self, question: str, n: int) -> list[Hit]:
        q = embed_texts(self.model, [question])[0]
        sims = self.matrix @ q
        scored = [
            (self.ids[i], float(sims[i]))
            for i in range(len(self.ids))
        ]
        scored.sort(key=lambda item: (-item[1], item[0]))
        hits: list[Hit] = []
        for chunk_id, similarity in scored[:n]:
            hits.append(
                Hit(
                    chunk_id=chunk_id,
                    similarity=similarity,
                    boost=None,
                    score=similarity,
                )
            )
        return hits


def build_index(chunks=None, model=None) -> Index:
    from src.rerank import terms

    if chunks is None:
        chunks = load_chunks()
    if model is None:
        model = load_model()
    ids = [chunk.id for chunk in chunks]
    matrix = embed_texts(model, [chunk.text for chunk in chunks])
    tokens = {chunk.id: count_tokens(model, chunk.text) for chunk in chunks}
    term_sets = {chunk.id: set(terms(chunk.text)) for chunk in chunks}
    n = len(chunks)
    df: dict[str, int] = {}
    for term_set in term_sets.values():
        for word in term_set:
            df[word] = df.get(word, 0) + 1
    idf = {word: math.log((n + 1) / (count + 0.5)) for word, count in df.items()}
    return Index(
        chunks={chunk.id: chunk for chunk in chunks},
        ids=ids,
        matrix=matrix,
        model=model,
        tokens=tokens,
        terms=term_sets,
        idf=idf,
    )
