"""Regression checks that Q&A answer evidence belongs to the matched location."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from benchmark import benchmark_case


CASE = {
    "id": "synthetic-qa",
    "type": "QA",
    "query": "question",
    "answer": {"video_id": "V1", "frame_idx": 100, "text_answer": "answer"},
}
FPS_MAP = {"V1": 1.0, "V2": 1.0}


def run_scenario(
    name: str,
    results: List[Dict[str, Any]],
    expected_correct: bool,
) -> Dict[str, Any]:
    record = benchmark_case(CASE, lambda _query: results, FPS_MAP, 0.0)
    actual_correct = bool(record["correct"])
    return {
        "name": name,
        "passed": actual_correct is expected_correct,
        "expected_correct": expected_correct,
        "actual_correct": actual_correct,
        "location_correct": record["location_correct"],
        "location_rank": record["location_rank"],
        "answer_evidence_correct": record["answer_evidence_correct"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cases = [
        run_scenario(
            "aligned_evidence",
            [{"video_id": "V1", "frame_idx": 100, "ocr_text": "the answer"}],
            True,
        ),
        run_scenario(
            "disconnected_evidence",
            [
                {"video_id": "V1", "frame_idx": 100, "ocr_text": "no evidence"},
                {"video_id": "V2", "frame_idx": 999, "ocr_text": "answer"},
            ],
            False,
        ),
        run_scenario(
            "evidence_without_location",
            [{"video_id": "V2", "frame_idx": 999, "ocr_text": "answer"}],
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
            f"QA EVIDENCE: {'PASS' if report['failed'] == 0 else 'FAIL'}, "
            f"scenarios={report['scenarios']}, passed={report['passed']}, failed={report['failed']}"
        )
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
