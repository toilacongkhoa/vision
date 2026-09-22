"""Benchmark semantic, OCR, ASR and reference hybrid retrieval on competition cases.

OCR/ASR receive an online-safe lexical reduction: a static Vietnamese stopword
list and at most the first N remaining unique terms. No answer labels or corpus
statistics are used to form a query.
"""

from __future__ import annotations

import argparse
import gc
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (PROJECT_ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from benchmark import (  # noqa: E402
    DATASET_PATH,
    FPS_MAP_PATH,
    TOLERANCE_SECONDS,
    benchmark_case,
    load_cases,
    load_fps_map,
    percentile,
    rank_targets,
)


STRATEGIES = ("semantic", "ocr", "asr", "hybrid")
RECALL_CUTOFFS = (1, 5, 10, 50)
VI_STOPWORDS = frozenset(
    {
        "các", "cảnh", "cho", "chính", "chiếc", "chúng", "cùng", "cuối",
        "của", "dưới", "đang", "đầu", "đến", "đoạn", "được", "giữa",
        "hình", "hiện", "khi", "lại", "lên", "lúc", "màn", "một", "này",
        "ngay", "người", "những", "phía", "qua", "sau", "theo", "thấy",
        "thì", "trên", "trong", "trước", "từ", "vào", "video", "với",
        "xuất",
    }
)


def reduce_lexical_query(query: str, max_terms: int) -> str:
    """Return a bounded query without using dataset-wide or answer statistics."""
    raw_terms = [
        token.casefold()
        for token in re.findall(r"\b\w+\b", query, flags=re.UNICODE)
        if len(token) >= 4
    ]
    filtered = [token for token in raw_terms if token not in VI_STOPWORDS]
    candidates = filtered or raw_terms
    selected: List[str] = []
    seen = set()
    for token in candidates:
        if token in seen:
            continue
        selected.append(token)
        seen.add(token)
        if len(selected) >= max_terms:
            break
    return " ".join(selected)


def result_key(item: Dict[str, Any]) -> Tuple[Any, ...]:
    vector_id = item.get("vector_id")
    if vector_id is not None:
        return ("vector", int(vector_id))
    return ("location", str(item.get("video_id")), int(item.get("frame_idx")))


def fuse_rrf(branches: Iterable[List[Dict[str, Any]]], top_k: int) -> List[Dict[str, Any]]:
    scores: Dict[Tuple[Any, ...], float] = {}
    items: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for branch in branches:
        for rank, item in enumerate(branch, start=1):
            try:
                key = result_key(item)
            except (TypeError, ValueError):
                continue
            scores[key] = scores.get(key, 0.0) + 1.0 / (60.0 + rank)
            items[key] = item
    ordered = sorted(scores, key=lambda key: scores[key], reverse=True)[:top_k]
    return [{**items[key], "score": scores[key]} for key in ordered]


def make_search(engine: Any, strategy: str, top_k: int, max_terms: int) -> Callable[[str], List[Dict[str, Any]]]:
    def semantic(query: str) -> List[Dict[str, Any]]:
        return engine.search(query_text=query, top_k=top_k)

    def ocr(query: str) -> List[Dict[str, Any]]:
        return engine.exact_ocr_search(reduce_lexical_query(query, max_terms), top_k=top_k)

    def asr(query: str) -> List[Dict[str, Any]]:
        return engine.exact_asr_search(reduce_lexical_query(query, max_terms), top_k=top_k)

    if strategy == "semantic":
        return semantic
    if strategy == "ocr":
        return ocr
    if strategy == "asr":
        return asr
    if strategy == "hybrid":
        return lambda query: fuse_rrf((semantic(query), ocr(query), asr(query)), top_k)
    raise ValueError(f"Unknown strategy: {strategy}")


def summarize(records: List[Dict[str, Any]], top_k: int) -> Dict[str, Any]:
    ranks = [rank for record in records for rank in rank_targets(record)]
    elapsed = [float(record["elapsed_ms"]) for record in records if record.get("elapsed_ms") is not None]
    ttfc = [
        float(record["time_to_first_correct_ms"])
        for record in records
        if record.get("time_to_first_correct_ms") is not None
    ]
    cutoffs = sorted({cutoff for cutoff in RECALL_CUTOFFS if cutoff <= top_k} | {top_k})
    return {
        "cases": len(records),
        "correct": sum(int(bool(record.get("correct"))) for record in records),
        "errors": sum(int("error" in record) for record in records),
        "targets": len(ranks),
        "recall": {
            str(cutoff): sum(int(rank is not None and rank <= cutoff) for rank in ranks)
            for cutoff in cutoffs
        },
        "mrr": sum(1.0 / rank for rank in ranks if rank is not None) / len(ranks) if ranks else 0.0,
        "latency_p50_ms": percentile(elapsed, 50),
        "latency_p95_ms": percentile(elapsed, 95),
        "ttfc_p50_ms": percentile(ttfc, 50),
        "ttfc_p95_ms": percentile(ttfc, 95),
    }


def run_strategy(
    strategy: str,
    cases: List[Dict[str, Any]],
    fps_map: Dict[str, float],
    top_k: int,
    max_terms: int,
    tolerance_seconds: float,
) -> Dict[str, Any]:
    from src.sqlite_engine import SQLiteSearchEngine

    load_started = time.perf_counter()
    engine = SQLiteSearchEngine()
    load_ms = (time.perf_counter() - load_started) * 1000
    search = make_search(engine, strategy, top_k, max_terms)
    records: List[Dict[str, Any]] = []
    wall_started = time.perf_counter()
    for case in cases:
        try:
            records.append(benchmark_case(case, search, fps_map, tolerance_seconds))
        except Exception as exc:
            records.append(
                {
                    "id": case.get("id"),
                    "type": case.get("type"),
                    "correct": False,
                    "error": repr(exc),
                    "elapsed_ms": None,
                }
            )
    result = {
        "strategy": strategy,
        "load_ms": load_ms,
        "wall_ms": (time.perf_counter() - wall_started) * 1000,
        "summary": summarize(records, top_k),
        "target_ranks": {
            str(record.get("id")): rank_targets(record)
            for record in records
        },
    }
    del engine
    gc.collect()
    return result


def semantic_preservation(reports: Dict[str, Dict[str, Any]], top_k: int) -> Dict[str, Any]:
    semantic = reports.get("semantic", {}).get("target_ranks", {})
    hybrid = reports.get("hybrid", {}).get("target_ranks", {})
    expected: List[str] = []
    missing: List[str] = []
    for case_id, ranks in semantic.items():
        hybrid_ranks = hybrid.get(case_id, [])
        for index, rank in enumerate(ranks):
            if rank is None or rank > top_k:
                continue
            label = f"{case_id}#{index + 1}"
            expected.append(label)
            if index >= len(hybrid_ranks) or hybrid_ranks[index] is None or hybrid_ranks[index] > top_k:
                missing.append(label)
    return {
        "semantic_hits": len(expected),
        "preserved": len(expected) - len(missing),
        "missing": missing,
        "passed": not missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--fps-map", type=Path, default=FPS_MAP_PATH)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--max-lexical-terms", type=int, default=6)
    parser.add_argument("--tolerance-seconds", type=float, default=TOLERANCE_SECONDS)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    if args.limit is not None:
        cases = cases[: max(0, args.limit)]
    fps_map = load_fps_map(args.fps_map)
    reports: Dict[str, Dict[str, Any]] = {}
    for strategy in args.strategies:
        print(f"[multimodal] running {strategy} on {len(cases)} cases", flush=True)
        reports[strategy] = run_strategy(
            strategy,
            cases,
            fps_map,
            args.top_k,
            args.max_lexical_terms,
            args.tolerance_seconds,
        )

    preservation: Optional[Dict[str, Any]] = None
    if "semantic" in reports and "hybrid" in reports:
        preservation = semantic_preservation(reports, args.top_k)
    report = {
        "coverage": len(reports),
        "top_k": args.top_k,
        "max_lexical_terms": args.max_lexical_terms,
        "tolerance_seconds": args.tolerance_seconds,
        "reports": reports,
        "semantic_preservation": preservation,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        for strategy, strategy_report in reports.items():
            summary = strategy_report["summary"]
            print(
                f"{strategy}: correct={summary['correct']}/{summary['cases']}, "
                f"recall={summary['recall']}, MRR={summary['mrr']:.4f}, "
                f"latency p50/p95={summary['latency_p50_ms']:.2f}/{summary['latency_p95_ms']:.2f} ms, "
                f"TTFC p50/p95={summary['ttfc_p50_ms']}/{summary['ttfc_p95_ms']} ms, "
                f"errors={summary['errors']}, wall={strategy_report['wall_ms']:.2f} ms"
            )
        if preservation is not None:
            print(
                "semantic preservation: "
                f"{preservation['preserved']}/{preservation['semantic_hits']}, "
                f"missing={preservation['missing']}"
            )
    errors = sum(item["summary"]["errors"] for item in reports.values())
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
