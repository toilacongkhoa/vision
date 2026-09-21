"""Benchmark and validate the production similar-by-vector search path.

This intentionally exercises ``SQLiteSearchEngine.search(query_vector_id=...)``
without requiring a running API server. A valid source vector must return the
requested number of results with itself ranked first.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_case(engine: Any, vector_id: int, top_k: int) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        results: List[Dict[str, Any]] = engine.search(
            query_vector_id=vector_id,
            top_k=top_k,
        )
    except Exception as exc:
        return {
            "passed": False,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "error": repr(exc),
        }

    returned_ids = [result.get("vector_id") for result in results]
    passed = len(results) == top_k and bool(returned_ids) and returned_ids[0] == vector_id
    return {
        "passed": passed,
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "result_count": len(results),
        "top_vector_id": returned_ids[0] if returned_ids else None,
        "returned_vector_ids": returned_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vector-id", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON")
    args = parser.parse_args()

    if args.vector_id < 0:
        parser.error("--vector-id must be non-negative")
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    sys.path.insert(0, str(PROJECT_ROOT))
    from src.sqlite_engine import SQLiteSearchEngine

    load_started = time.perf_counter()
    engine = SQLiteSearchEngine()
    load_ms = (time.perf_counter() - load_started) * 1000
    case = run_case(engine, args.vector_id, args.top_k)
    report = {
        "scenarios": 1,
        "passed": int(bool(case["passed"])),
        "failed": int(not case["passed"]),
        "errors": int("error" in case),
        "load_ms": load_ms,
        "case": case,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if case["passed"] else "FAIL"
        print(
            f"SIMILAR: {status}, scenarios=1, passed={report['passed']}, "
            f"failed={report['failed']}, errors={report['errors']}, "
            f"load={load_ms:.2f} ms, case={case['elapsed_ms']:.2f} ms"
        )
        if "error" in case:
            print(f"ERROR: {case['error']}")
        else:
            print(
                f"RESULTS: count={case['result_count']}, "
                f"top_vector_id={case['top_vector_id']}"
            )
    return 0 if case["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
