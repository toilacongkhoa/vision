"""Validate that SQLiteSearchEngine honors the configured DB_PATH."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = (PROJECT_ROOT / "video_index_v2.db").resolve()
RESULT_MARKER = "DB_CONFIG_RESULT="


def expected_row_count() -> int:
    with sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM keyframes").fetchone()[0])


def run_case(expected_count: int) -> Dict[str, Any]:
    fake_data_root = Path(tempfile.gettempdir()) / "vision-config-benchmark" / "data"
    child_code = f"""
import json
import sys
sys.path.insert(0, {str(PROJECT_ROOT)!r})
from src.config import DB_PATH
from src.sqlite_engine import SQLiteSearchEngine

engine = SQLiteSearchEngine()
payload = {{
    "configured_path": str(DB_PATH),
    "engine_path": str(engine.db_path),
    "row_count": None,
}}
try:
    payload["row_count"] = engine._get_db().execute(
        "SELECT COUNT(*) FROM keyframes"
    ).fetchone()[0]
except Exception as exc:
    payload["error"] = repr(exc)
print({RESULT_MARKER!r} + json.dumps(payload))
"""
    environment = os.environ.copy()
    environment.update(
        {
            "DB_PATH": str(DATABASE_PATH),
            "DATA_ROOT": str(fake_data_root),
            "CONSOLIDATED_VECTORS_PATH": str(PROJECT_ROOT / "all_vectors.npy"),
        }
    )
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, "-c", child_code],
            cwd=str(PROJECT_ROOT),
            env=environment,
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
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "error": repr(exc),
        }

    payload: Dict[str, Any] = {}
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(RESULT_MARKER):
            try:
                payload = json.loads(line[len(RESULT_MARKER) :])
            except json.JSONDecodeError:
                pass
            break
    passed = (
        completed.returncode == 0
        and payload.get("configured_path") == str(DATABASE_PATH)
        and payload.get("engine_path") == str(DATABASE_PATH)
        and payload.get("row_count") == expected_count
    )
    return {
        "passed": passed,
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "returncode": completed.returncode,
        "expected_path": str(DATABASE_PATH),
        "expected_count": expected_count,
        **payload,
        "stderr_tail": completed.stderr.splitlines()[-3:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON")
    args = parser.parse_args()

    case = run_case(expected_row_count())
    report = {
        "scenarios": 1,
        "passed": int(case["passed"]),
        "failed": int(not case["passed"]),
        "errors": int("error" in case),
        "case": case,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        status = "PASS" if case["passed"] else "FAIL"
        print(
            f"DATABASE CONFIG: {status}, path={case.get('engine_path')}, "
            f"rows={case.get('row_count')}/{case.get('expected_count')}, "
            f"elapsed={case['elapsed_ms']:.2f} ms"
        )
    return 0 if case["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
