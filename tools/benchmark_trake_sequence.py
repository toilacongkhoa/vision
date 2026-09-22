"""Regression checks for TRAKE same-video and temporal sequence scoring."""

from __future__ import annotations

import argparse
import json
from typing import Any, Callable, Dict, List

from benchmark import benchmark_case


CASE = {
    "id": "synthetic-trake",
    "type": "TRAKE",
    "query": "E1: first event\nE2: second event",
    "answer": [
        {"video_id": "V1", "frame_idx": 100},
        {"video_id": "V1", "frame_idx": 200},
    ],
}
FPS_MAP = {"V1": 1.0, "V2": 1.0}


def make_search(responses: List[List[Dict[str, Any]]]) -> Callable[[str], List[Dict[str, Any]]]:
    remaining = iter(responses)
    return lambda _query: next(remaining)


def run_scenario(
    name: str,
    responses: List[List[Dict[str, Any]]],
    expected_correct: bool,
) -> Dict[str, Any]:
    record = benchmark_case(CASE, make_search(responses), FPS_MAP, 150.0)
    actual_correct = bool(record["correct"])
    return {
        "name": name,
        "passed": actual_correct is expected_correct,
        "expected_correct": expected_correct,
        "actual_correct": actual_correct,
        "event_ranks": record["event_ranks"],
        "selected_sequence": record["selected_sequence"],
        "same_video": record["same_video"],
        "ordered_sequence": record["ordered_sequence"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cases = [
        run_scenario(
            "ordered",
            [[{"video_id": "V1", "frame_idx": 100}], [{"video_id": "V1", "frame_idx": 200}]],
            True,
        ),
        run_scenario(
            "duplicate_frame",
            [[{"video_id": "V1", "frame_idx": 150}], [{"video_id": "V1", "frame_idx": 150}]],
            False,
        ),
        run_scenario(
            "reverse_order",
            [[{"video_id": "V1", "frame_idx": 200}], [{"video_id": "V1", "frame_idx": 100}]],
            False,
        ),
    ]
    report = {
        "scenarios": len(cases),
        "passed": sum(int(case["passed"]) for case in cases),
        "failed": sum(int(not case["passed"]) for case in cases),
        "cases": cases,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(
            f"TRAKE SEQUENCE: {'PASS' if report['failed'] == 0 else 'FAIL'}, "
            f"scenarios={report['scenarios']}, passed={report['passed']}, failed={report['failed']}"
        )
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
