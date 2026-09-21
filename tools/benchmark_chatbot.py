"""Benchmark the production Agy chatbot API as a separate Track B evaluation.

The default dataset is answerAndQuestion.jsonl.  It supplies expected
VideoID/FrameIdx pairs and QA text answers, while an optional JSONL dataset can
add reference answers for conversational evaluations.  The script consumes
the SSE stream from POST /api/v1/chat and never changes the retrieval benchmark.

Example::

    python tools/benchmark_chatbot.py --api-url http://127.0.0.1:8000

The current FastAPI chat endpoint does not expose token usage.  In that case
the report explicitly marks token and cost metrics as unavailable.  If a
future endpoint includes usage in an SSE JSON payload, pass model pricing with
--input-cost-per-1m and --output-cost-per-1m to estimate cost.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Reuse Track A's dataset loading and frame-tolerance implementation.
from benchmark import load_cases, load_fps_map, normalize_text, pair, within_time_tolerance


DEFAULT_API_URL = "http://127.0.0.1:8000"
DATASET_PATH = PROJECT_ROOT / "answerAndQuestion.jsonl"
FPS_MAP_PATH = PROJECT_ROOT / "video_fps_map.json"
TOLERANCE_SECONDS = 150.0

_LABELLED_PAIR_RE = re.compile(
    r"(?:video\s*id|videoid)\s*[:：=]\s*([A-Za-z0-9_-]+)"
    r"[^\n]{0,100}?"
    r"(?:frame\s*(?:idx|index)?|frame_idx)\s*[:：=]\s*(\d+)",
    flags=re.IGNORECASE,
)
_SHORT_PAIR_RE = re.compile(
    r"\b([A-Za-z]\d+_V\d+)\s*[,;|]\s*(?:frame\s*(?:idx|index)?\s*[:：=]\s*)?(\d+)\b",
    flags=re.IGNORECASE,
)


def extract_video_frame_pairs(text: str) -> List[Tuple[str, int]]:
    """Extract ordered VideoID/FrameIdx pairs from an Agy answer."""
    matches: List[Tuple[int, Tuple[str, int]]] = []
    for regex in (_LABELLED_PAIR_RE, _SHORT_PAIR_RE):
        for match in regex.finditer(text):
            try:
                matches.append((match.start(), (str(match.group(1)), int(match.group(2)))))
            except (TypeError, ValueError):
                continue

    ordered: List[Tuple[str, int]] = []
    seen = set()
    for _, candidate in sorted(matches, key=lambda item: item[0]):
        if candidate not in seen:
            ordered.append(candidate)
            seen.add(candidate)
    return ordered


def _usage_from_payload(payload: Dict[str, Any]) -> Optional[Dict[str, int]]:
    """Read common usage shapes without requiring a specific Agy schema."""
    usage = payload.get("usage") or payload.get("usage_metadata") or payload.get("token_usage")
    if not isinstance(usage, dict):
        return None

    def first_int(*names: str) -> Optional[int]:
        for name in names:
            value = usage.get(name)
            if isinstance(value, (int, float)):
                return int(value)
        return None

    input_tokens = first_int("input_tokens", "prompt_tokens", "inputTokens")
    output_tokens = first_int("output_tokens", "completion_tokens", "outputTokens")
    total_tokens = first_int("total_tokens", "totalTokens")
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None
    if total_tokens is None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    return {
        "input_tokens": input_tokens or 0,
        "output_tokens": output_tokens or 0,
        "total_tokens": total_tokens,
    }


def _merge_usage(current: Optional[Dict[str, int]], incoming: Optional[Dict[str, int]]) -> Optional[Dict[str, int]]:
    if incoming is None:
        return current
    if current is None:
        return dict(incoming)
    return {
        key: current.get(key, 0) + incoming.get(key, 0)
        for key in ("input_tokens", "output_tokens", "total_tokens")
    }


def call_chat(
    endpoint: str,
    message: str,
    session_id: str,
    timeout_seconds: float,
) -> Dict[str, Any]:
    """Call /api/v1/chat and consume its text/event-stream response."""
    payload = json.dumps({"message": message, "session_id": session_id}).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "vision-chatbot-benchmark/1.0",
        },
        method="POST",
    )
    started = time.perf_counter()
    text_parts: List[str] = []
    errors: List[str] = []
    usage: Optional[Dict[str, int]] = None

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                if data.startswith("[TOOL]"):
                    continue
                if data.startswith("[ERROR]"):
                    errors.append(data)
                    continue

                try:
                    payload_event = json.loads(data)
                except json.JSONDecodeError:
                    text_parts.append(data.replace("<br>", "\n"))
                    continue
                if isinstance(payload_event, dict):
                    usage = _merge_usage(usage, _usage_from_payload(payload_event))
                    delta = payload_event.get("text") or payload_event.get("delta") or payload_event.get("content")
                    if isinstance(delta, str):
                        text_parts.append(delta)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        errors.append(repr(exc))

    return {
        "text": "".join(text_parts),
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "errors": errors,
        "usage": usage,
    }


def _ordered_sequence_matches(
    expected: Iterable[Tuple[str, int]],
    returned: Iterable[Tuple[str, int]],
    fps_map: Dict[str, float],
    tolerance_seconds: float,
) -> bool:
    returned_list = list(returned)
    start = 0
    for expected_pair in expected:
        found = False
        for index in range(start, len(returned_list)):
            if within_time_tolerance(expected_pair, returned_list[index], fps_map, tolerance_seconds):
                start = index + 1
                found = True
                break
        if not found:
            return False
    return True


def evaluate_case(
    case: Dict[str, Any],
    response: Dict[str, Any],
    fps_map: Dict[str, float],
    tolerance_seconds: float,
) -> Dict[str, Any]:
    response_text = response["text"]
    returned_pairs = extract_video_frame_pairs(response_text)
    answer = case.get("answer", {})
    if isinstance(answer, list):
        expected_pairs = [pair(item) for item in answer]
    else:
        expected_pairs = [pair(answer)]

    if case.get("type") == "TRAKE":
        location_correct = _ordered_sequence_matches(expected_pairs, returned_pairs, fps_map, tolerance_seconds)
    else:
        location_correct = any(
            within_time_tolerance(expected_pairs[0], returned, fps_map, tolerance_seconds)
            for returned in returned_pairs
        )

    expected_text = None
    if isinstance(answer, dict):
        expected_text = answer.get("text_answer")
    expected_text = expected_text or case.get("expected_answer") or case.get("reference_answer")
    text_correct: Optional[bool] = None
    if expected_text:
        text_correct = normalize_text(expected_text) in normalize_text(response_text)

    answer_correct = location_correct and (text_correct if text_correct is not None else True)
    return {
        "id": case.get("id"),
        "type": case.get("type"),
        "correct": answer_correct,
        "location_correct": location_correct,
        "text_correct": text_correct,
        "expected_pairs": expected_pairs,
        "returned_pairs": returned_pairs,
        "response_text": response_text,
        "elapsed_ms": response["elapsed_ms"],
        "errors": response["errors"],
        "usage": response["usage"],
    }


def estimate_cost(
    usage: Optional[Dict[str, int]],
    input_cost_per_million: float,
    output_cost_per_million: float,
) -> Optional[float]:
    if usage is None:
        return None
    return (
        usage.get("input_tokens", 0) / 1_000_000 * input_cost_per_million
        + usage.get("output_tokens", 0) / 1_000_000 * output_cost_per_million
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Base URL of the running FastAPI server")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--fps-map", type=Path, default=FPS_MAP_PATH)
    parser.add_argument("--tolerance-seconds", type=float, default=TOLERANCE_SECONDS)
    parser.add_argument("--timeout", type=float, default=180.0, help="Socket read timeout per stream read")
    parser.add_argument("--limit", type=int, help="Run only the first N cases")
    parser.add_argument("--output", type=Path, help="Optional JSON file containing full chatbot responses")
    parser.add_argument("--model-label", default="configured-by-agy", help="Label shown in the cost report")
    parser.add_argument("--input-cost-per-1m", type=float, default=0.0)
    parser.add_argument("--output-cost-per-1m", type=float, default=0.0)
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    if args.limit is not None:
        cases = cases[: max(args.limit, 0)]
    fps_map = load_fps_map(args.fps_map)
    endpoint = args.api_url.rstrip("/") + "/api/v1/chat"
    records: List[Dict[str, Any]] = []

    for index, case in enumerate(cases, start=1):
        response = call_chat(endpoint, case["query"], f"benchmark-chat-{case.get('id', index)}", args.timeout)
        record = evaluate_case(case, response, fps_map, args.tolerance_seconds)
        records.append(record)
        status = "OK" if record["correct"] else "MISS"
        error_status = "error" if record["errors"] else "ok"
        print(
            f"[{index}/{len(cases)}] {case.get('type', 'UNKNOWN'):<5} "
            f"{status:<4} {record['elapsed_ms']:.1f} ms "
            f"candidates={len(record['returned_pairs'])} {error_status} {case.get('id')}"
        )

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["type"]].append(record)

    print(f"\n=== CHATBOT BENCHMARK SUMMARY (frame tolerance: +/- {args.tolerance_seconds:.1f}s / +/- {args.tolerance_seconds / 60:.1f} min) ===")
    total_correct = sum(bool(record["correct"]) for record in records)
    total_errors = sum(bool(record["errors"]) for record in records)
    timed = [record["elapsed_ms"] for record in records]
    for case_type in ("KIS", "QA", "TRAKE"):
        group = grouped.get(case_type, [])
        correct = sum(bool(record["correct"]) for record in group)
        location = sum(bool(record["location_correct"]) for record in group)
        text_checked = [record for record in group if record["text_correct"] is not None]
        text_correct = sum(bool(record["text_correct"]) for record in text_checked)
        average = sum(record["elapsed_ms"] for record in group) / len(group) if group else 0.0
        text_summary = f", text_answer {text_correct}/{len(text_checked)}" if text_checked else ""
        print(
            f"{case_type}: {correct}/{len(group)} correct ({(100 * correct / len(group)) if group else 0:.2f}%), "
            f"location/sequence {location}/{len(group)}{text_summary}, average {average:.2f} ms"
        )

    usage_records = [record["usage"] for record in records if record["usage"] is not None]
    usage_total: Optional[Dict[str, int]] = None
    for usage in usage_records:
        usage_total = _merge_usage(usage_total, usage)
    estimated_cost = estimate_cost(usage_total, args.input_cost_per_1m, args.output_cost_per_1m)
    print(f"TOTAL: {total_correct}/{len(records)} correct ({(100 * total_correct / len(records)) if records else 0:.2f}%), average {sum(timed) / len(timed) if timed else 0.0:.2f} ms")
    print(f"ERROR RATE: {total_errors}/{len(records)} ({(100 * total_errors / len(records)) if records else 0:.2f}%)")
    if usage_total is None:
        print(f"USAGE/COST ({args.model_label}): unavailable; /api/v1/chat did not return token usage")
    else:
        print(
            f"USAGE ({args.model_label}): input={usage_total['input_tokens']}, "
            f"output={usage_total['output_tokens']}, total={usage_total['total_tokens']}"
        )
        if estimated_cost is None or (args.input_cost_per_1m == 0 and args.output_cost_per_1m == 0):
            print("ESTIMATED COST: unavailable; provide --input-cost-per-1m and --output-cost-per-1m")
        else:
            print(f"ESTIMATED COST: ${estimated_cost:.6f}")

    if args.output:
        args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"DETAILS: wrote {args.output}")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
