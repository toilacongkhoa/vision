"""Compare semantic retrieval with sentence-aware clause splitting on p2/p3 labels."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark import (  # noqa: E402
    DATASET_PATH,
    FPS_MAP_PATH,
    benchmark_case,
    configure_translation_network,
    format_rank_metrics,
    load_cases,
    load_fps_map,
    percentile,
    rank_targets,
)


def summarize(records: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    ranks = [rank for record in records for rank in rank_targets(record)]
    elapsed = [float(record["elapsed_ms"]) for record in records]
    return {
        "cases": len(records),
        "correct_cases": sum(bool(record.get("correct")) for record in records),
        "targets": len(ranks),
        "rank_metrics": format_rank_metrics(
            [{"type": "KIS", "location_rank": rank} for rank in ranks], top_k
        ),
        "recall_at_1": sum(rank is not None and rank <= 1 for rank in ranks),
        "recall_at_5": sum(rank is not None and rank <= 5 for rank in ranks),
        "recall_at_10": sum(rank is not None and rank <= 10 for rank in ranks),
        "recall_at_top_k": sum(rank is not None and rank <= top_k for rank in ranks),
        "mrr": sum(1.0 / rank for rank in ranks if rank is not None) / len(ranks) if ranks else 0.0,
        "latency_p50_ms": percentile(elapsed, 50),
        "latency_p95_ms": percentile(elapsed, 95),
    }


def evaluate(cases, search, fps_map, tolerance_seconds):
    records = []
    for case in cases:
        try:
            records.append(benchmark_case(case, search, fps_map, tolerance_seconds))
        except Exception as exc:
            records.append(
                {
                    "id": case.get("id"),
                    "type": case.get("type"),
                    "correct": False,
                    "location_rank": None,
                    "event_ranks": [],
                    "elapsed_ms": 0.0,
                    "error": type(exc).__name__,
                }
            )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--fps-map", type=Path, default=FPS_MAP_PATH)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--tolerance-seconds", type=float, default=5.0,
                        help="diagnostic temporal window, not a competition rule")
    args = parser.parse_args()

    configure_translation_network(False)
    cases = load_cases(args.dataset)
    groups = {
        "p2_tuning": [case for case in cases if str(case.get("id", "")).startswith("query-p2-")],
        "p3_holdout": [case for case in cases if str(case.get("id", "")).startswith("query-p3-")],
    }
    if sum(map(len, groups.values())) != len(cases) or any(not group for group in groups.values()):
        parser.error("dataset must contain non-empty query-p2-* and query-p3-* groups only")

    fps_map = load_fps_map(args.fps_map)
    from src import sqlite_engine
    from src.sqlite_engine import SQLiteSearchEngine

    engine = SQLiteSearchEngine()
    top_k = args.top_k

    def search(query: str):
        return engine.search(query_text=query, top_k=top_k)

    original_pattern = sqlite_engine._CLAUSE_SPLIT_RE
    candidate_pattern = re.compile(r",|;|\n| and |(?<=[.!?])\s+")
    report = {
        "dataset": str(args.dataset.resolve()),
        "dataset_sha256": _sha256(args.dataset),
        "cases": len(cases),
        "top_k": top_k,
        "tolerance_seconds_diagnostic_only": args.tolerance_seconds,
        "translation": "offline/cache only; online translation disabled",
        "splits": {},
    }

    for split_name, split_cases in groups.items():
        sqlite_engine._CLAUSE_SPLIT_RE = original_pattern
        baseline = evaluate(split_cases, search, fps_map, args.tolerance_seconds)
        sqlite_engine._CLAUSE_SPLIT_RE = candidate_pattern
        candidate = evaluate(split_cases, search, fps_map, args.tolerance_seconds)
        report["splits"][split_name] = {
            "case_count": len(split_cases),
            "baseline": summarize(baseline, top_k),
            "sentence_split": summarize(candidate, top_k),
            "candidate_errors": sum("error" in record for record in candidate),
        }
        print(f"Completed {split_name}: {len(split_cases)} cases", flush=True)

    sqlite_engine._CLAUSE_SPLIT_RE = original_pattern
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
