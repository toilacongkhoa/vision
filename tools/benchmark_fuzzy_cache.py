"""Benchmark OCR/ASR fuzzy fallback correctness and cache latency.

The production database may not contain the optional FTS5 tables.  In that
case ``exact_ocr_search`` and ``exact_asr_search`` use the LIKE-based fallback
implemented by ``SQLiteSearchEngine``.  This benchmark covers repeated
queries, a large-to-small top-K sequence, and a video-filtered query without
requiring a running API server.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SearchFn = Callable[..., List[Dict[str, Any]]]


def timed_search(
    search: SearchFn,
    query: str,
    top_k: int,
    video_id: Optional[str] = None,
) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        results = search(query, top_k=top_k, video_id_filter=video_id)
    except Exception as exc:
        return {
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "error": repr(exc),
        }
    return {
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "result_count": len(results),
        "vector_ids": [item.get("vector_id") for item in results],
        "video_ids": [item.get("video_id") for item in results],
    }


def repeated_case(search: SearchFn, query: str, top_k: int) -> Dict[str, Any]:
    cold = timed_search(search, query, top_k)
    warm = timed_search(search, query, top_k)
    passed = (
        "error" not in cold
        and "error" not in warm
        and cold.get("result_count") == top_k
        and warm.get("vector_ids") == cold.get("vector_ids")
    )
    return {
        "passed": passed,
        "query": query,
        "top_k": top_k,
        "cold": cold,
        "warm": warm,
    }


def prefix_case(search: SearchFn, query: str, top_k: int) -> Dict[str, Any]:
    prime_top_k = max(top_k * 10, top_k + 1)
    prime = timed_search(search, query, prime_top_k)
    small = timed_search(search, query, top_k)
    passed = (
        "error" not in prime
        and "error" not in small
        and prime.get("result_count") == prime_top_k
        and small.get("vector_ids") == prime.get("vector_ids", [])[:top_k]
    )
    return {
        "passed": passed,
        "query": query,
        "prime_top_k": prime_top_k,
        "small_top_k": top_k,
        "prime": prime,
        "small": small,
    }


def filtered_case(
    search: SearchFn,
    query: str,
    top_k: int,
    video_id: str,
) -> Dict[str, Any]:
    result = timed_search(search, query, top_k, video_id)
    passed = (
        "error" not in result
        and result.get("result_count") == top_k
        and all(item == video_id for item in result.get("video_ids", []))
    )
    return {
        "passed": passed,
        "query": query,
        "top_k": top_k,
        "video_id": video_id,
        "result": result,
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
        "ocr_repeat": repeated_case(
            engine.exact_ocr_search,
            "học sinh giáo viên trường học đồng phục",
            args.top_k,
        ),
        "asr_repeat": repeated_case(
            engine.exact_asr_search,
            "học sinh giáo viên trường học đồng phục",
            args.top_k,
        ),
        "ocr_prefix": prefix_case(
            engine.exact_ocr_search,
            "học sinh trường học đồng phục sân",
            args.top_k,
        ),
        "asr_prefix": prefix_case(
            engine.exact_asr_search,
            "học sinh trường học đồng phục sân",
            args.top_k,
        ),
        "asr_filter": filtered_case(
            engine.exact_asr_search,
            "học sinh",
            min(args.top_k, 3),
            "L22_V019",
        ),
    }
    report = {
        "scenarios": len(cases),
        "passed": sum(int(case["passed"]) for case in cases.values()),
        "failed": sum(int(not case["passed"]) for case in cases.values()),
        "errors": sum(
            int(
                any(
                    "error" in value
                    for value in case.values()
                    if isinstance(value, dict)
                )
            )
            for case in cases.values()
        ),
        "load_ms": load_ms,
        "cases": cases,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        status = "PASS" if report["failed"] == 0 else "FAIL"
        print(
            f"FUZZY CACHE: {status}, scenarios={report['scenarios']}, "
            f"passed={report['passed']}, failed={report['failed']}, "
            f"errors={report['errors']}, load={load_ms:.2f} ms"
        )
        for name, case in cases.items():
            print(f"{name}: {'PASS' if case['passed'] else 'FAIL'}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
