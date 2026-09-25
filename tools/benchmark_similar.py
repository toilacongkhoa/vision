"""Benchmark and validate the production similar-by-vector search path.

This intentionally exercises ``SQLiteSearchEngine.search(query_vector_id=...)``
without requiring a running API server. A valid source vector must return the
requested number of results with itself ranked first, while vector IDs outside
the matrix bounds must return no results.
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


def run_invalid_case(engine: Any, vector_id: int, top_k: int) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        results: List[Dict[str, Any]] = engine.search(
            query_vector_id=vector_id,
            top_k=top_k,
        )
    except Exception as exc:
        return {
            "vector_id": vector_id,
            "passed": False,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "error": repr(exc),
        }

    return {
        "vector_id": vector_id,
        "passed": results == [],
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "result_count": len(results),
    }


def run_prefix_cache_case(engine: Any, vector_id: int, top_k: int) -> Dict[str, Any]:
    prime_top_k = min(max(top_k * 10, top_k + 1), len(engine.vectors))
    prime = run_case(engine, vector_id, prime_top_k)
    cached = run_case(engine, vector_id, top_k)
    expected_ids = prime.get("returned_vector_ids", [])[:top_k]
    returned_ids = cached.get("returned_vector_ids", [])
    passed = (
        bool(prime.get("passed"))
        and bool(cached.get("passed"))
        and returned_ids == expected_ids
        and cached["elapsed_ms"] < prime["elapsed_ms"]
    )
    return {
        "vector_id": vector_id,
        "passed": passed,
        "prime_top_k": prime_top_k,
        "prime_elapsed_ms": prime["elapsed_ms"],
        "cached_top_k": top_k,
        "cached_elapsed_ms": cached["elapsed_ms"],
        "returned_vector_ids": returned_ids,
        **({"error": prime.get("error") or cached.get("error")} if "error" in prime or "error" in cached else {}),
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
    invalid_cases = [
        run_invalid_case(engine, -1, args.top_k),
        run_invalid_case(engine, len(engine.vectors), args.top_k),
    ]
    prefix_vector_id = (args.vector_id + 1) % len(engine.vectors)
    prefix_cache_case = run_prefix_cache_case(
        engine,
        prefix_vector_id,
        args.top_k,
    )
    cases = [case, *invalid_cases, prefix_cache_case]
    report = {
        "scenarios": len(cases),
        "passed": sum(int(bool(item["passed"])) for item in cases),
        "failed": sum(int(not item["passed"]) for item in cases),
        "errors": sum(int("error" in item) for item in cases),
        "load_ms": load_ms,
        "case": case,
        "invalid_cases": invalid_cases,
        "prefix_cache_case": prefix_cache_case,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if report["failed"] == 0 else "FAIL"
        print(
            f"SIMILAR: {status}, scenarios={report['scenarios']}, passed={report['passed']}, "
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
        for invalid_case in invalid_cases:
            invalid_status = "PASS" if invalid_case["passed"] else "FAIL"
            print(
                f"INVALID {invalid_case['vector_id']}: {invalid_status}, "
                f"results={invalid_case.get('result_count')}, "
                f"case={invalid_case['elapsed_ms']:.2f} ms"
            )
        prefix_status = "PASS" if prefix_cache_case["passed"] else "FAIL"
        print(
            f"PREFIX CACHE: {prefix_status}, vector_id={prefix_cache_case['vector_id']}, "
            f"prime={prefix_cache_case['prime_elapsed_ms']:.2f} ms, "
            f"cached={prefix_cache_case['cached_elapsed_ms']:.2f} ms"
        )
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
