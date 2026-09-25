"""Benchmark the production retrieval pipeline against answerAndQuestion.jsonl.

The default mode instantiates the same SQLiteSearchEngine used by the FastAPI
application, so the benchmark does not depend on a separately running server.
Translation is kept local/cache-only unless --allow-online-translation is passed.
Use --api-url to benchmark an already running /api/v1/search endpoint instead;
that server's egress cannot be controlled by this client.
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
RECALL_CUTOFFS = (1, 5, 10, 50)


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


def first_matching_rank(
    expected: Tuple[str, int],
    results: Iterable[Dict[str, Any]],
    fps_map: Dict[str, float],
    tolerance_seconds: float,
) -> Optional[int]:
    """Return the one-based rank of the first location match, or ``None``."""
    for rank, result in enumerate(results, start=1):
        try:
            returned = pair(result)
        except (TypeError, ValueError):
            continue
        if within_time_tolerance(expected, returned, fps_map, tolerance_seconds):
            return rank
    return None


def matching_location_results(
    expected: Tuple[str, int],
    results: Iterable[Dict[str, Any]],
    fps_map: Dict[str, float],
    tolerance_seconds: float,
) -> List[Dict[str, Any]]:
    """Return only results that match the expected video and time window."""
    matches: List[Dict[str, Any]] = []
    for result in results:
        try:
            returned = pair(result)
        except (TypeError, ValueError):
            continue
        if within_time_tolerance(expected, returned, fps_map, tolerance_seconds):
            matches.append(result)
    return matches


def find_ordered_trake_sequence(
    expected: List[Tuple[str, int]],
    event_results: List[List[Dict[str, Any]]],
    fps_map: Dict[str, float],
    tolerance_seconds: float,
) -> Optional[List[Dict[str, Any]]]:
    """Select one location match per event in a shared video and time order."""
    if not expected or len(event_results) != len(expected):
        return None
    expected_videos = {video_id for video_id, _ in expected}
    if len(expected_videos) != 1:
        return None

    paths: List[Tuple[List[int], List[Dict[str, Any]]]] = []
    for rank, result in enumerate(event_results[0], start=1):
        try:
            returned = pair(result)
        except (TypeError, ValueError):
            continue
        if within_time_tolerance(expected[0], returned, fps_map, tolerance_seconds):
            paths.append(([rank], [result]))

    for event_index in range(1, len(expected)):
        next_paths: List[Tuple[List[int], List[Dict[str, Any]]]] = []
        for rank, result in enumerate(event_results[event_index], start=1):
            try:
                returned_video, returned_frame = pair(result)
            except (TypeError, ValueError):
                continue
            if not within_time_tolerance(
                expected[event_index],
                (returned_video, returned_frame),
                fps_map,
                tolerance_seconds,
            ):
                continue
            compatible = [
                (ranks, selected)
                for ranks, selected in paths
                if pair(selected[-1])[0] == returned_video
                and pair(selected[-1])[1] < returned_frame
            ]
            if compatible:
                ranks, selected = min(
                    compatible,
                    key=lambda item: (max(item[0]), sum(item[0]), item[0]),
                )
                next_paths.append((ranks + [rank], selected + [result]))
        paths = next_paths
        if not paths:
            return None

    _, selected = min(paths, key=lambda item: (max(item[0]), sum(item[0]), item[0]))
    return selected


def percentile(values: Iterable[float], percentile_value: float) -> Optional[float]:
    """Return a linearly interpolated percentile without adding dependencies."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile_value / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


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


def configure_translation_network(allow_online_translation: bool) -> None:
    """Disable translator network fallbacks unless a caller explicitly allows them."""
    if allow_online_translation:
        return
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.fast_translator import fast_translator

    fast_translator._online_fallback_disabled = True
    fast_translator.local_translator = None
    fast_translator.tokenizer = None


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
        event_ranks: List[Optional[int]] = []
        event_results: List[List[Dict[str, Any]]] = []
        for event_index, event in enumerate(events):
            results = search(event)
            event_results.append(results)
            rank = (
                first_matching_rank(expected[event_index], results, fps_map, tolerance_seconds)
                if event_index < len(expected)
                else None
            )
            event_ranks.append(rank)
            event_hits.append(rank is not None)
        sequence = find_ordered_trake_sequence(
            expected,
            event_results[: len(expected)],
            fps_map,
            tolerance_seconds,
        )
        selected_pairs = [pair(result) for result in sequence] if sequence else []
        same_video = bool(selected_pairs) and len({video_id for video_id, _ in selected_pairs}) == 1
        ordered_sequence = same_video and all(
            selected_pairs[index - 1][1] < selected_pairs[index][1]
            for index in range(1, len(selected_pairs))
        )
        correct = len(selected_pairs) == len(expected) and ordered_sequence
        target_ranks = event_ranks[: len(expected)]
        target_ranks.extend([None] * (len(expected) - len(target_ranks)))
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "id": case["id"],
            "type": case_type,
            "correct": correct,
            "event_hits": event_hits,
            "event_ranks": target_ranks,
            "expected_events": expected,
            "selected_sequence": selected_pairs,
            "same_video": same_video,
            "ordered_sequence": ordered_sequence,
            "elapsed_ms": elapsed_ms,
            "time_to_first_correct_ms": elapsed_ms if correct else None,
        }

    expected = pair(answer)
    results = search(case["query"])
    location_rank = first_matching_rank(expected, results, fps_map, tolerance_seconds)
    location_correct = location_rank is not None
    location_results = matching_location_results(expected, results, fps_map, tolerance_seconds)
    answer_evidence_correct = (
        text_answer_matches(answer.get("text_answer"), location_results)
        if case_type == "QA"
        else None
    )
    correct = location_correct and (
        answer_evidence_correct if answer_evidence_correct is not None else True
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "id": case["id"],
        "type": case_type,
        "correct": correct,
        "location_correct": location_correct,
        "location_rank": location_rank,
        "text_correct": answer_evidence_correct,
        "answer_evidence_correct": answer_evidence_correct,
        "expected": expected,
        "elapsed_ms": elapsed_ms,
        "time_to_first_correct_ms": elapsed_ms if correct else None,
    }


def rank_targets(record: Dict[str, Any]) -> List[Optional[int]]:
    """Return independently ranked competition targets for Recall/MRR."""
    if record.get("type") == "TRAKE":
        return list(record.get("event_ranks", []))
    return [record.get("location_rank")]


def format_rank_metrics(records: Iterable[Dict[str, Any]], top_k: int) -> str:
    targets = [rank for record in records for rank in rank_targets(record)]
    total = len(targets)
    cutoffs = sorted({cutoff for cutoff in RECALL_CUTOFFS if cutoff <= top_k} | {top_k})
    recall_parts = []
    for cutoff in cutoffs:
        hits = sum(rank is not None and rank <= cutoff for rank in targets)
        percentage = 100 * hits / total if total else 0.0
        recall_parts.append(f"R@{cutoff} {hits}/{total} ({percentage:.2f}%)")
    mrr = sum(1.0 / rank for rank in targets if rank is not None) / total if total else 0.0
    return f"{', '.join(recall_parts)}, MRR {mrr:.4f}"


def format_latency_metrics(records: Iterable[Dict[str, Any]]) -> str:
    records_list = list(records)
    elapsed = [record["elapsed_ms"] for record in records_list if record.get("elapsed_ms") is not None]
    ttfc = [
        record["time_to_first_correct_ms"]
        for record in records_list
        if record.get("time_to_first_correct_ms") is not None
    ]
    p50 = percentile(elapsed, 50) or 0.0
    p95 = percentile(elapsed, 95) or 0.0
    if not ttfc:
        return f"latency p50/p95 {p50:.2f}/{p95:.2f} ms, TTFC unavailable (no correct case)"
    ttfc_p50 = percentile(ttfc, 50) or 0.0
    ttfc_p95 = percentile(ttfc, 95) or 0.0
    return (
        f"latency p50/p95 {p50:.2f}/{p95:.2f} ms, "
        f"TTFC p50/p95 {ttfc_p50:.2f}/{ttfc_p95:.2f} ms ({len(ttfc)} correct cases)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--fps-map", type=Path, default=FPS_MAP_PATH)
    parser.add_argument("--tolerance-seconds", type=float, default=TOLERANCE_SECONDS)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--api-url", help="Base URL of a running FastAPI server; otherwise use the direct production pipeline")
    parser.add_argument(
        "--allow-online-translation",
        action="store_true",
        help="allow FastTranslator to send uncached Vietnamese queries to Google Translate/MyMemory",
    )
    args = parser.parse_args()

    if args.api_url and not args.allow_online_translation:
        parser.error("API mode cannot enforce local translator settings; pass --allow-online-translation only when that server's egress is approved")
    configure_translation_network(args.allow_online_translation)

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
        if case["type"] == "TRAKE":
            rank_label = (
                f"event_ranks={record.get('event_ranks')} "
                f"sequence={record.get('selected_sequence')}"
            )
        else:
            rank_label = f"rank={record.get('location_rank')}"
        print(f"[{index}/{len(cases)}] {case['type']:<5} {status:<4} {elapsed} {rank_label} {case['id']}")

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
            answer_evidence_correct = sum(
                bool(record.get("answer_evidence_correct")) for record in group
            )
            details = (
                f", location {location_correct}/{len(group)}, "
                f"answer_evidence {answer_evidence_correct}/{len(group)}"
            )
        if case_type == "TRAKE":
            event_targets = [rank for record in group for rank in rank_targets(record)]
            event_hits = sum(rank is not None for rank in event_targets)
            details = f", ordered sequence {correct}/{len(group)}, event hits {event_hits}/{len(event_targets)}"
        print(f"{case_type}: {correct}/{len(group)} correct ({(100 * correct / len(group)) if group else 0:.2f}%){details}, average {average:.2f} ms")
        print(f"  Ranking: {format_rank_metrics(group, args.top_k)}")
        print(f"  Timing: {format_latency_metrics(group)}")
    average = sum(timed) / len(timed) if timed else 0.0
    print(f"TOTAL: {total_correct}/{len(records)} correct ({(100 * total_correct / len(records)) if records else 0:.2f}%), average {average:.2f} ms")
    print(f"  Ranking: {format_rank_metrics(records, args.top_k)}")
    print(f"  Timing: {format_latency_metrics(records)}")
    errors = [record for record in records if "error" in record]
    if errors:
        print(f"ERRORS: {len(errors)}")
        for record in errors:
            print(f"  {record['type']} {record['id']}: {record['error']}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
