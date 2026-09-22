"""Regression checks for chatbot benchmark session isolation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from benchmark_chatbot import build_benchmark_session_id  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    first = build_benchmark_session_id("run-a", "case-1")
    records: List[Dict[str, Any]] = [
        {
            "scenario": "stable_within_run",
            "passed": first == build_benchmark_session_id("run-a", "case-1"),
        },
        {
            "scenario": "isolated_between_runs",
            "passed": first != build_benchmark_session_id("run-b", "case-1"),
        },
        {
            "scenario": "isolated_between_cases",
            "passed": first != build_benchmark_session_id("run-a", "case-2"),
        },
    ]
    failed = sum(not record["passed"] for record in records)
    summary = {
        "scenarios": len(records),
        "passed": len(records) - failed,
        "failed": failed,
        "records": records,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=True, indent=2))
    else:
        for record in records:
            status = "PASS" if record["passed"] else "FAIL"
            print(f"[{status}] {record['scenario']}")
        print(f"SUMMARY: {summary['passed']}/{summary['scenarios']} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
