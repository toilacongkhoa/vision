"""Regression benchmark for KIS/QA first-candidate scoring in chatbot output."""

from __future__ import annotations

import argparse
import json

from benchmark_chatbot import evaluate_case


FPS_MAP = {"L26_V183": 25.0, "L26_V005": 25.0}
KIS = {"id": "kis", "type": "KIS", "answer": {"video_id": "L26_V183", "frame_idx": 5895}}
QA = {
    "id": "qa",
    "type": "QA",
    "answer": {"video_id": "L26_V183", "frame_idx": 5895, "text_answer": "màu xanh"},
}


def score(case: dict, text: str) -> dict:
    response = {"text": text, "elapsed_ms": 100.0, "errors": [], "usage": None}
    return evaluate_case(case, response, FPS_MAP, 150.0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    wrong_first = score(KIS, "1. L26_V005,5870\n2. L26_V183,5895")
    right_first = score(KIS, "1. L26_V183,5895\n2. L26_V005,5870")
    wrong_qa_first = score(QA, "1. L26_V005,5870\n2. L26_V183,5895\nAnswer: màu xanh")
    right_qa_first = score(QA, "1. L26_V183,5895\n2. L26_V005,5870\nAnswer: màu xanh")
    wrong_qa_answer = score(QA, "1. L26_V183,5895\nAnswer: màu đỏ")
    empty = score(KIS, "No verified candidate")
    checks = [
        ("wrong_first_backup_hit", not wrong_first["correct"] and wrong_first["any_location_correct"]),
        ("right_first", right_first["correct"] and right_first["first_candidate"] == ("L26_V183", 5895)),
        ("wrong_qa_first_backup_hit", not wrong_qa_first["correct"] and wrong_qa_first["any_location_correct"]),
        ("right_qa_first_and_answer", right_qa_first["correct"]),
        ("right_qa_location_wrong_answer", not wrong_qa_answer["correct"] and wrong_qa_answer["location_correct"]),
        ("empty_candidate", not empty["correct"] and empty["first_candidate"] is None),
    ]
    records = [{"scenario": name, "passed": passed} for name, passed in checks]
    passed = sum(item["passed"] for item in records)
    summary = {"scenarios": len(records), "passed": passed, "failed": len(records) - passed, "records": records}
    if args.json:
        print(json.dumps(summary, ensure_ascii=True, indent=2))
    else:
        for item in records:
            print(f"[{'PASS' if item['passed'] else 'FAIL'}] {item['scenario']}")
        print(f"SUMMARY: {passed}/{len(records)} passed")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
