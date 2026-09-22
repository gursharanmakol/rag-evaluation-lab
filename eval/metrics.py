from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.pipeline import CONTEXT_BUDGET, TOP_K, run


@dataclass
class QuestionResult:
    id: str
    question: str
    expected: str
    position: int | None
    in_top_3: bool
    in_top_10: bool
    rr: float
    retrieved: bool
    kept: list[str]
    reached: list[str]
    cut: list[str]
    used_tokens: int


@dataclass
class EvalResult:
    questions: list[QuestionResult]
    top_k: int
    budget: int
    retrieval_passed: int
    recall_at_3: float
    recall_at_10: float
    mrr: float
    kept_total: int
    reached_total: int
    cut_total: int


def load_questions(path: str | Path = "eval/questions.yaml") -> list[dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a list of questions")
    questions: list[dict] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: question {index} is not a record")
        for field in ("id", "question", "expected"):
            if field not in item or item[field] is None or str(item[field]) == "":
                raise ValueError(f"{path}: question {index} missing {field}")
        questions.append(
            {
                "id": str(item["id"]),
                "question": str(item["question"]),
                "expected": str(item["expected"]),
            }
        )
    return questions


def evaluate(index, questions, top_k=TOP_K) -> EvalResult:
    rows: list[QuestionResult] = []
    retrieval_passed = 0
    top3_hits = 0
    top10_hits = 0
    rr_sum = 0.0
    kept_total = 0
    reached_total = 0
    cut_total = 0

    for item in questions:
        trace = run(index, item["question"], history=None, top_k=top_k)
        ranked_ids = [hit.chunk_id for hit in trace.retrieval.ranked]
        kept_ids = [hit.chunk_id for hit in trace.retrieval.kept]
        reached_ids = [
            chunk_id
            for chunk_id, _tokens, status in trace.assembly.items
            if status == "reached"
        ]
        cut_ids = [
            chunk_id
            for chunk_id, _tokens, status in trace.assembly.items
            if status == "cut"
        ]
        try:
            position = ranked_ids.index(item["expected"]) + 1
        except ValueError:
            position = None
        in_top_3 = position is not None and position <= 3
        in_top_10 = position is not None and position <= 10
        rr = 0.0 if position is None else 1.0 / position
        retrieved = item["expected"] in kept_ids
        if retrieved:
            retrieval_passed += 1
        if in_top_3:
            top3_hits += 1
        if in_top_10:
            top10_hits += 1
        rr_sum += rr
        kept_total += len(kept_ids)
        reached_total += len(reached_ids)
        cut_total += len(cut_ids)
        rows.append(
            QuestionResult(
                id=item["id"],
                question=item["question"],
                expected=item["expected"],
                position=position,
                in_top_3=in_top_3,
                in_top_10=in_top_10,
                rr=rr,
                retrieved=retrieved,
                kept=kept_ids,
                reached=reached_ids,
                cut=cut_ids,
                used_tokens=trace.assembly.used_tokens,
            )
        )

    n = len(questions)
    return EvalResult(
        questions=rows,
        top_k=top_k,
        budget=CONTEXT_BUDGET,
        retrieval_passed=retrieval_passed,
        recall_at_3=(top3_hits / n) if n else 0.0,
        recall_at_10=(top10_hits / n) if n else 0.0,
        mrr=(rr_sum / n) if n else 0.0,
        kept_total=kept_total,
        reached_total=reached_total,
        cut_total=cut_total,
    )
