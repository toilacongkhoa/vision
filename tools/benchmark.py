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
FPS_MAP_PATH = PROJECT_ROOT / "video_fps_map.json"
TOLERANCE_SECONDS = 150.0


def load_cases(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_fps_map(path: Path) -> Dict[str, float]:
    with path.open("r", encoding="utf-8") as handle:
        raw_map = json.load(handle)
    return {str(video_id): float(fps) for video_id, fps in raw_map.items()}


def pair(item: Dict[str, Any]) -> Tuple[str, int]:
    return str(item.get("video_id")), int(item.get("frame_idx"))


def within_time_tolerance(
    expected: Tuple[str, int],
    returned: Tuple[str, int],
    fps_map: Dict[str, float],
    tolerance_seconds: float,
) -> bool:
    expected_video, expected_frame = expected
    returned_video, returned_frame = returned
    if expected_video != returned_video:
        return False
    fps = fps_map.get(expected_video)
    if fps is None or fps <= 0:
        raise ValueError(f"Missing or invalid FPS for video_id={expected_video!r}")
    expected_seconds = expected_frame / fps
    returned_seconds = returned_frame / fps
    return abs(returned_seconds - expected_seconds) <= tolerance_seconds


def result_pairs(results: Iterable[Dict[str, Any]]) -> List[Tuple[str, int]]:
    pairs: List[Tuple[str, int]] = []
    for result in results:
        try:
            pairs.append(pair(result))
        except (TypeError, ValueError):
            continue
    return pairs


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def text_answer_matches(expected_text: Any, results: Iterable[Dict[str, Any]]) -> bool:
    expected = normalize_text(expected_text)
    if not expected:
        return True
    fields = ("text_answer", "answer", "text", "ocr_text", "asr_text", "objects")
    for result in results:
        for field in fields:
            content = normalize_text(result.get(field))
            if expected and expected in content:
                return True
    return False


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


def benchmark_case(
    case: Dict[str, Any],
    search: Callable[[str], List[Dict[str, Any]]],
    fps_map: Dict[str, float],
    tolerance_seconds: float,
) -> Dict[str, Any]:
    case_type = case["type"]
    answer = case["answer"]
    started = time.perf_counter()

    if case_type == "TRAKE":
        expected = [pair(item) for item in answer]
        events = split_trake_events(case["query"])
        event_hits: List[bool] = []
        for event_index, event in enumerate(events):
            results = search(event)
            event_hits.append(
                event_index < len(expected)
                and any(
                    within_time_tolerance(expected[event_index], returned, fps_map, tolerance_seconds)
                    for returned in result_pairs(results)
                )
            )
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
    location_correct = any(
        within_time_tolerance(expected, returned, fps_map, tolerance_seconds)
        for returned in result_pairs(results)
    )
    text_correct = text_answer_matches(answer.get("text_answer"), results) if case_type == "QA" else None
    return {
        "id": case["id"],
        "type": case_type,
        "correct": location_correct and (text_correct if text_correct is not None else True),
        "location_correct": location_correct,
        "text_correct": text_correct,
        "expected": expected,
        "elapsed_ms": (time.perf_counter() - started) * 1000,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--fps-map", type=Path, default=FPS_MAP_PATH)
    parser.add_argument("--tolerance-seconds", type=float, default=TOLERANCE_SECONDS)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--api-url", help="Base URL of a running FastAPI server; otherwise use the direct production pipeline")
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    fps_map = load_fps_map(args.fps_map)
    search = make_api_search(args.api_url, args.top_k) if args.api_url else make_direct_search(args.top_k)

    records: List[Dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        try:
            record = benchmark_case(case, search, fps_map, args.tolerance_seconds)
        except Exception as exc:  # Keep the report complete and identify failing cases.
            record = {"id": case.get("id"), "type": case.get("type"), "correct": False, "error": repr(exc), "elapsed_ms": None}
        records.append(record)
        status = "OK" if record["correct"] else "MISS"
        elapsed = "error" if record["elapsed_ms"] is None else f"{record['elapsed_ms']:.1f} ms"
        print(f"[{index}/{len(cases)}] {case['type']:<5} {status:<4} {elapsed} {case['id']}")

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["type"]].append(record)

    print(f"\n=== BENCHMARK SUMMARY (frame tolerance: +/- {args.tolerance_seconds:.1f}s / +/- {args.tolerance_seconds / 60:.1f} min) ===")
    total_correct = sum(bool(record["correct"]) for record in records)
    timed = [record["elapsed_ms"] for record in records if record["elapsed_ms"] is not None]
    for case_type in ("KIS", "QA", "TRAKE"):
        group = grouped.get(case_type, [])
        correct = sum(bool(record["correct"]) for record in group)
        group_times = [record["elapsed_ms"] for record in group if record["elapsed_ms"] is not None]
        average = sum(group_times) / len(group_times) if group_times else 0.0
        details = ""
        if case_type == "QA":
            location_correct = sum(bool(record.get("location_correct")) for record in group)
            text_correct = sum(bool(record.get("text_correct")) for record in group)
            details = f", location {location_correct}/{len(group)}, text_answer {text_correct}/{len(group)}"
        print(f"{case_type}: {correct}/{len(group)} correct ({(100 * correct / len(group)) if group else 0:.2f}%){details}, average {average:.2f} ms")
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
