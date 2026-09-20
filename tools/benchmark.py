"""Benchmark the production retrieval pipeline against answerAndQuestion.jsonl.

The default mode instantiates the same SQLiteSearchEngine used by the FastAPI
application, so the benchmark does not depend on a separately running server.
Use --api-url to benchmark an already running /api/v1/search endpoint instead.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "answerAndQuestion.jsonl"


def load_cases(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def pair(item: Dict[str, Any]) -> Tuple[str, int]:
    return str(item.get("video_id")), int(item.get("frame_idx"))


def result_pairs(results: Iterable[Dict[str, Any]]) -> set[Tuple[str, int]]:
    pairs: set[Tuple[str, int]] = set()
    for result in results:
        try:
            pairs.add(pair(result))
        except (TypeError, ValueError):
            continue
    return pairs


def split_trake_events(query: str) -> List[str]:
    """Extract E1..En event descriptions used by the production agent flow."""
    events = re.findall(r"E\d+\s*:\s*(.*?)(?=\nE\d+\s*:|$)", query, flags=re.S)
    return [re.sub(r"\s+", " ", event).strip() for event in events if event.strip()]


def make_direct_search(top_k: int) -> Callable[[str], List[Dict[str, Any]]]:
    # Import lazily so --help and --api-url do not load torch/OpenCLIP.
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.sqlite_engine import SQLiteSearchEngine

    engine = SQLiteSearchEngine()

    def search(query: str) -> List[Dict[str, Any]]:
        return engine.search(query_text=query, top_k=top_k)

    return search


def make_api_search(api_url: str, top_k: int) -> Callable[[str], List[Dict[str, Any]]]:
    endpoint = api_url.rstrip("/") + "/api/v1/search"

    def search(query: str) -> List[Dict[str, Any]]:
        payload = json.dumps({"query": query, "top_k": top_k, "mode": "semantic"}).encode("utf-8")
        request = Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("results", [])

    return search


def benchmark_case(case: Dict[str, Any], search: Callable[[str], List[Dict[str, Any]]]) -> Dict[str, Any]:
    case_type = case["type"]
    answer = case["answer"]
    started = time.perf_counter()

    if case_type == "TRAKE":
        expected = [pair(item) for item in answer]
        events = split_trake_events(case["query"])
        event_hits: List[bool] = []
        returned: List[List[Tuple[str, int]]] = []
        for event in events:
            results = search(event)
            pairs = result_pairs(results)
            returned.append(sorted(pairs))
            event_hits.append(expected[len(event_hits)] in pairs if len(event_hits) < len(expected) else False)
        correct = len(event_hits) == len(expected) and all(event_hits)
        return {
            "id": case["id"],
            "type": case_type,
            "correct": correct,
            "event_hits": event_hits,
            "expected_events": expected,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
        }

    expected = pair(answer)
    results = search(case["query"])
    hits = expected in result_pairs(results)
    return {
        "id": case["id"],
        "type": case_type,
        "correct": hits,
        "expected": expected,
        "elapsed_ms": (time.perf_counter() - started) * 1000,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--api-url", help="Base URL of a running FastAPI server; otherwise use the direct production pipeline")
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    search = make_api_search(args.api_url, args.top_k) if args.api_url else make_direct_search(args.top_k)

    records: List[Dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        try:
            record = benchmark_case(case, search)
        except Exception as exc:  # Keep the report complete and identify failing cases.
            record = {"id": case.get("id"), "type": case.get("type"), "correct": False, "error": repr(exc), "elapsed_ms": None}
        records.append(record)
        status = "OK" if record["correct"] else "MISS"
        elapsed = "error" if record["elapsed_ms"] is None else f"{record['elapsed_ms']:.1f} ms"
        print(f"[{index}/{len(cases)}] {case['type']:<5} {status:<4} {elapsed} {case['id']}")

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["type"]].append(record)

    print("\n=== BENCHMARK SUMMARY ===")
    total_correct = sum(bool(record["correct"]) for record in records)
    timed = [record["elapsed_ms"] for record in records if record["elapsed_ms"] is not None]
    for case_type in ("KIS", "QA", "TRAKE"):
        group = grouped.get(case_type, [])
        correct = sum(bool(record["correct"]) for record in group)
        group_times = [record["elapsed_ms"] for record in group if record["elapsed_ms"] is not None]
        average = sum(group_times) / len(group_times) if group_times else 0.0
        print(f"{case_type}: {correct}/{len(group)} correct ({(100 * correct / len(group)) if group else 0:.2f}%), average {average:.2f} ms")
    average = sum(timed) / len(timed) if timed else 0.0
    print(f"TOTAL: {total_correct}/{len(records)} correct ({(100 * total_correct / len(records)) if records else 0:.2f}%), average {average:.2f} ms")
    errors = [record for record in records if "error" in record]
    if errors:
        print(f"ERRORS: {len(errors)}")
        for record in errors:
            print(f"  {record['type']} {record['id']}: {record['error']}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
