"""Benchmark semantic candidate-cache correctness and warm latency."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def timed_search(engine: Any, query: str, top_k: int) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        results: List[Dict[str, Any]] = engine.search(query_text=query, top_k=top_k)
    except Exception as exc:
        return {
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "error": repr(exc),
        }
    return {
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "result_count": len(results),
        "vector_ids": [item.get("vector_id") for item in results],
    }


def repeated_case(engine: Any, query: str, top_k: int) -> Dict[str, Any]:
    cold = timed_search(engine, query, top_k)
    warm = timed_search(engine, query, top_k)
    passed = (
        "error" not in cold
        and "error" not in warm
        and cold["result_count"] == top_k
        and warm["vector_ids"] == cold["vector_ids"]
        and warm["elapsed_ms"] < cold["elapsed_ms"]
    )
    return {"passed": passed, "query": query, "top_k": top_k, "cold": cold, "warm": warm}


def prefix_case(engine: Any, query: str, top_k: int) -> Dict[str, Any]:
    large_top_k = min(max(top_k * 10, top_k + 1), len(engine.vectors))
    prime = timed_search(engine, query, large_top_k)
    cached = timed_search(engine, query, top_k)
    expected_ids = prime.get("vector_ids", [])[:top_k]
    passed = (
        "error" not in prime
        and "error" not in cached
        and cached.get("vector_ids") == expected_ids
        and cached["elapsed_ms"] < prime["elapsed_ms"]
    )
    return {
        "passed": passed,
        "query": query,
        "prime_top_k": large_top_k,
        "cached_top_k": top_k,
        "prime": prime,
        "cached": cached,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON")
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    sys.path.insert(0, str(PROJECT_ROOT))
    from src.sqlite_engine import SQLiteSearchEngine

    load_started = time.perf_counter()
    engine = SQLiteSearchEngine()
    load_ms = (time.perf_counter() - load_started) * 1000
    cases = {
        "single_repeat": repeated_case(engine, "a person riding a bicycle", args.top_k),
        "single_prefix": prefix_case(engine, "a red vehicle on a roadway", args.top_k),
        "multi_clause_repeat": repeated_case(engine, "a person, a bicycle", args.top_k),
    }
    report = {
        "scenarios": len(cases),
        "passed": sum(int(case["passed"]) for case in cases.values()),
        "failed": sum(int(not case["passed"]) for case in cases.values()),
        "errors": sum(
            int(any("error" in value for value in case.values() if isinstance(value, dict)))
            for case in cases.values()
        ),
        "load_ms": load_ms,
        "cases": cases,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if report["failed"] == 0 else "FAIL"
        print(
            f"SEMANTIC CACHE: {status}, scenarios={report['scenarios']}, "
            f"passed={report['passed']}, failed={report['failed']}, "
            f"errors={report['errors']}, load={load_ms:.2f} ms"
        )
        for name, case in cases.items():
            print(f"{name}: {'PASS' if case['passed'] else 'FAIL'}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
