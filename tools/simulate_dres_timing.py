"""Compare early-submit and wait strategies under explicit probability assumptions.

Example: python tools/simulate_dres_timing.py --early-seconds 60 --wait-seconds 240 --task-seconds 300 --p-correct-early 0.55 --p-correct-wait 0.82 --p-recover-after-early-wrong 0.6

This is an offline sensitivity calculator, not a calibrated competition policy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dres_submission import SubmissionError, compare_submission_timing  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--early-seconds", type=float, required=True)
    parser.add_argument("--wait-seconds", type=float, required=True)
    parser.add_argument("--task-seconds", type=float, required=True)
    parser.add_argument("--wrong-submissions-before", type=int, default=0)
    parser.add_argument("--p-correct-early", type=float, required=True)
    parser.add_argument("--p-correct-wait", type=float, required=True)
    parser.add_argument("--p-recover-after-early-wrong", type=float, required=True)
    args = parser.parse_args()
    try:
        result = compare_submission_timing(
            early_seconds=args.early_seconds,
            wait_seconds=args.wait_seconds,
            task_seconds=args.task_seconds,
            wrong_submissions_before=args.wrong_submissions_before,
            p_correct_early=args.p_correct_early,
            p_correct_wait=args.p_correct_wait,
            p_recover_after_early_wrong=args.p_recover_after_early_wrong,
        )
    except SubmissionError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
