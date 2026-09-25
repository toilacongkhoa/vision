"""Validate that runtime metadata paths do not depend on the launch CWD."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COUNT_MARKER = "METADATA_COUNT="


def expected_metadata_count() -> int:
    with (PROJECT_ROOT / "video_drive_metadata.json").open(
        "r", encoding="utf-8"
    ) as handle:
        payload = json.load(handle)
    return len(payload.get("videos", {}))


def run_import(cwd: Path, expected_count: int) -> Dict[str, Any]:
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(PROJECT_ROOT)!r}); "
        "import src.main as main; "
        f"print({COUNT_MARKER!r} + str(len(main.video_metadata_cache)))"
    )
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
    except Exception as exc:
        return {
            "passed": False,
            "cwd": str(cwd),
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "error": repr(exc),
        }

    count = None
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(COUNT_MARKER):
            try:
                count = int(line[len(COUNT_MARKER) :])
            except ValueError:
                pass
            break
    return {
        "passed": completed.returncode == 0 and count == expected_count,
        "cwd": str(cwd),
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "returncode": completed.returncode,
        "metadata_count": count,
        "expected_count": expected_count,
        "stderr_tail": completed.stderr.splitlines()[-3:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON")
    args = parser.parse_args()

    expected_count = expected_metadata_count()
    cases = {
        "project_cwd": run_import(PROJECT_ROOT, expected_count),
        "external_cwd": run_import(Path(tempfile.gettempdir()), expected_count),
    }
    report = {
        "scenarios": len(cases),
        "passed": sum(int(case["passed"]) for case in cases.values()),
        "failed": sum(int(not case["passed"]) for case in cases.values()),
        "errors": sum(int("error" in case) for case in cases.values()),
        "expected_count": expected_count,
        "cases": cases,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        status = "PASS" if report["failed"] == 0 else "FAIL"
        print(
            f"RUNTIME PATHS: {status}, scenarios={report['scenarios']}, "
            f"passed={report['passed']}, failed={report['failed']}, "
            f"errors={report['errors']}"
        )
        for name, case in cases.items():
            print(
                f"{name}: {'PASS' if case['passed'] else 'FAIL'}, "
                f"metadata={case.get('metadata_count')}/{expected_count}, "
                f"elapsed={case['elapsed_ms']:.2f} ms"
            )
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
