"""Contract benchmark for the offline DRES early-submit/wait calculator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dres_submission import (  # noqa: E402
    SubmissionError,
    compare_submission_timing,
)


def _scenario(**kwargs):
    return compare_submission_timing(
        early_seconds=kwargs.pop("early_seconds", 60),
        wait_seconds=kwargs.pop("wait_seconds", 240),
        task_seconds=kwargs.pop("task_seconds", 300),
        wrong_submissions_before=kwargs.pop("wrong_submissions_before", 0),
        p_correct_early=kwargs.pop("p_correct_early", 0.55),
        p_correct_wait=kwargs.pop("p_correct_wait", 0.82),
        p_recover_after_early_wrong=kwargs.pop("p_recover_after_early_wrong", 0.6),
        **kwargs,
    )


def run_benchmark() -> Tuple[int, int, List[str]]:
    checks: List[Tuple[str, Callable[[], None]]] = [
        ("early_strategy_wins_when_assumptions_support_it", lambda: _assert(
            (_scenario()["preferred_under_assumptions"], _scenario()["early_expected_score"]),
            ("early", 63.0),
        )),
        ("wait_strategy_wins_when_early_confidence_is_low", lambda: _assert(
            _scenario(p_correct_early=0.2, p_correct_wait=0.9, p_recover_after_early_wrong=0.1)["preferred_under_assumptions"],
            "wait",
        )),
        ("break_even_probability_is_reported", lambda: _assert(
            _scenario()["early_correct_probability_break_even"], 0.32,
        )),
        ("prior_wrong_attempts_reduce_both_options", lambda: _assert(
            _scenario(wrong_submissions_before=1)["early_expected_score"] < _scenario()["early_expected_score"],
            True,
        )),
        ("reject_probability_above_one", lambda: _raises(
            lambda: _scenario(p_correct_wait=1.1),
        )),
        ("reject_wait_after_deadline", lambda: _raises(
            lambda: _scenario(wait_seconds=301),
        )),
    ]
    failures = []
    for name, check in checks:
        try:
            check()
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    return len(checks) - len(failures), len(checks), failures


def _assert(actual, expected):
    if actual != expected:
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def _raises(function):
    try:
        function()
    except SubmissionError:
        return
    raise AssertionError("expected SubmissionError")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    passed, total, failures = run_benchmark()
    if args.json:
        print(json.dumps({"passed": passed, "total": total, "failed": failures}))
    else:
        print(f"DRES timing strategy benchmark: {passed}/{total} pass")
        for failure in failures:
            print(f"FAIL {failure}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
