"""Offline contract benchmark for AI Challenge 2026 DRES submissions.

This checks serializers and scoring against the supplied organizer guide. It
does not authenticate to or submit to a DRES server.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dres_submission import (  # noqa: E402
    SubmissionDeduper,
    SubmissionError,
    build_kis_payload,
    build_qa_payload,
    build_trake_payload,
    pts_time_seconds_to_ms,
    score_full_answer,
    score_partial_trake,
    validate_payload,
)


def _raises(function: Callable[[], object], error: type[Exception] = SubmissionError) -> None:
    try:
        function()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_contract_benchmark() -> Tuple[int, int, List[str]]:
    scenarios: List[Tuple[str, Callable[[], None]]] = []

    def check_payload(name: str, payload: object, query_type: str, expected: object) -> None:
        if payload != expected:
            raise AssertionError(f"{name}: payload mismatch: {payload!r}")
        validate_payload(payload, query_type)

    scenarios.append(("textual_kis_ms_payload", lambda: check_payload(
        "textual_kis_ms_payload",
        build_kis_payload("L1_V2", 12.3456),
        "Textual KIS",
        {"answerSets": [{"answers": [{"mediaItemName": "L1_V2", "start": "12346", "end": "12346"}]}]},
    )))
    scenarios.append(("video_kis_point_payload", lambda: check_payload(
        "video_kis_point_payload",
        build_kis_payload("L1_V2", 0),
        "VIDEO_KIS",
        {"answerSets": [{"answers": [{"mediaItemName": "L1_V2", "start": "0", "end": "0"}]}]},
    )))
    scenarios.append(("qa_text_payload", lambda: check_payload(
        "qa_text_payload",
        build_qa_payload("L1_V2", 8.888, "màu xanh"),
        "Q&A",
        {"answerSets": [{"answers": [{"text": "QA-màu xanh-L1_V2-8888"}]}]},
    )))
    scenarios.append(("trake_ordered_frame_ids", lambda: check_payload(
        "trake_ordered_frame_ids",
        build_trake_payload("L1_V2", [100, 150, 205]),
        "TRAKE",
        {"answerSets": [{"answers": [{"text": "TR-L1_V2-100,150,205"}]}]},
    )))
    scenarios.append(("pts_time_half_up_rounding", lambda: _assert_equal(pts_time_seconds_to_ms("1.2345"), 1235)))
    scenarios.append(("reject_video_extension", lambda: _raises(lambda: build_kis_payload("L1_V2.mp4", 1))))
    scenarios.append(("reject_negative_timestamp", lambda: _raises(lambda: build_kis_payload("L1_V2", -0.1))))
    scenarios.append(("reject_nonfinite_timestamp", lambda: _raises(lambda: pts_time_seconds_to_ms(float("nan")))))
    scenarios.append(("reject_empty_qa_answer", lambda: _raises(lambda: build_qa_payload("L1_V2", 1, " "))))
    scenarios.append(("reject_unordered_trake", lambda: _raises(lambda: build_trake_payload("L1_V2", [100, 100]))))
    scenarios.append(("reject_invalid_payload_envelope", lambda: _raises(lambda: validate_payload({}, "KIS"))))
    scenarios.append(("reject_unordered_trake_payload", lambda: _raises(lambda: validate_payload(
        {"answerSets": [{"answers": [{"text": "TR-L1_V2-100,90"}]}]}, "TRAKE"
    ))))

    def dedupe_behavior() -> None:
        deduper = SubmissionDeduper()
        original = build_kis_payload("L1_V2", 12.0)
        corrected = build_kis_payload("L1_V2", 13.0)
        deduper.record("q1", original)
        deduper.record("q1", original)
        deduper.record("q1", corrected)
        deduper.record("q2", original)

    scenarios.append(("record_identical_retries_and_allow_corrections", dedupe_behavior))
    scenarios.append(("full_score_formula", lambda: _assert_equal(
        [score_full_answer(0, 300, 0), score_full_answer(150, 300, 1), score_full_answer(300, 300, 0)],
        [100.0, 65.0, 50.0],
    )))
    scenarios.append(("partial_trake_score_formula", lambda: _assert_equal(
        score_partial_trake(150, 300, 1, 2, 4), 32.5
    )))
    scenarios.append(("reject_full_sequence_as_partial", lambda: _raises(
        lambda: score_partial_trake(150, 300, 0, 4, 4)
    )))

    failures: List[str] = []
    for name, scenario in scenarios:
        try:
            scenario()
        except Exception as exc:  # report every failed contract in one run
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    passed = len(scenarios) - len(failures)
    return passed, len(scenarios), failures


def _assert_equal(actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print a JSON summary")
    args = parser.parse_args()

    passed, total, failures = run_contract_benchmark()
    if args.json:
        import json

        print(json.dumps({"passed": passed, "total": total, "failed": failures}, ensure_ascii=True))
    else:
        print(f"DRES submission contract: {passed}/{total} pass, {len(failures)} fail")
        for failure in failures:
            print(f"FAIL {failure}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
