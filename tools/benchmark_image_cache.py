"""Benchmark image-search correctness and repeated-request latency.

The benchmark creates deterministic JPEG inputs in memory and calls the
production ``SQLiteSearchEngine.search_by_image`` path directly.  It covers a
repeated identical image and a large-to-small top-K sequence without relying
on external image files or a running API server.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_jpeg(color: Tuple[int, int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def timed_search(engine: Any, image_bytes: bytes, top_k: int) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        results: List[Dict[str, Any]] = engine.search_by_image(
            image_bytes,
            top_k=top_k,
        )
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


def repeated_case(engine: Any, image_bytes: bytes, top_k: int) -> Dict[str, Any]:
    cold = timed_search(engine, image_bytes, top_k)
    warm = timed_search(engine, image_bytes, top_k)
    passed = (
        "error" not in cold
        and "error" not in warm
        and cold.get("result_count") == top_k
        and warm.get("vector_ids") == cold.get("vector_ids")
    )
    return {"passed": passed, "top_k": top_k, "cold": cold, "warm": warm}


def prefix_case(engine: Any, image_bytes: bytes, top_k: int) -> Dict[str, Any]:
    prime_top_k = max(top_k * 10, top_k + 1)
    prime = timed_search(engine, image_bytes, prime_top_k)
    small = timed_search(engine, image_bytes, top_k)
    passed = (
        "error" not in prime
        and "error" not in small
        and prime.get("result_count") == prime_top_k
        and small.get("vector_ids") == prime.get("vector_ids", [])[:top_k]
    )
    return {
        "passed": passed,
        "prime_top_k": prime_top_k,
        "small_top_k": top_k,
        "prime": prime,
        "small": small,
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
        "repeat": repeated_case(engine, make_jpeg((220, 30, 30)), args.top_k),
        "prefix": prefix_case(engine, make_jpeg((30, 30, 220)), args.top_k),
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
            f"IMAGE CACHE: {status}, scenarios={report['scenarios']}, "
            f"passed={report['passed']}, failed={report['failed']}, "
            f"errors={report['errors']}, load={load_ms:.2f} ms"
        )
        for name, case in cases.items():
            print(f"{name}: {'PASS' if case['passed'] else 'FAIL'}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
