"""Regression benchmark for converting Agy result events to chatbot SSE."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agy_session import AgySession  # noqa: E402


class _FakeStdout:
    def __init__(self, events: List[Dict[str, Any]]) -> None:
        self.lines = [(json.dumps(event) + "\n").encode("utf-8") for event in events]

    async def readline(self) -> bytes:
        return self.lines.pop(0) if self.lines else b""


class _FakeProcess:
    returncode = None

    def __init__(self, events: List[Dict[str, Any]]) -> None:
        self.stdout = _FakeStdout(events)


async def _collect(events: List[Dict[str, Any]]) -> str:
    session = AgySession("benchmark-agy-result")
    session.proc = _FakeProcess(events)
    session.ready.set()
    chunks = []
    async for chunk in session._read_until_result(1.0):
        chunks.append(chunk)
    return "".join(chunks)


async def _run() -> List[Dict[str, Any]]:
    response_output = await _collect(
        [{"event": "result", "result": {"status": "SUCCESS", "response": "L21_V001,1500"}}]
    )
    error_output = await _collect(
        [{"event": "result", "result": {"status": "ERROR", "response": "", "error": "auth failed"}}]
    )
    no_duplicate_output = await _collect(
        [
            {"event": "step_update", "step_update": {"text_delta": "L22_V002,222"}},
            {"event": "result", "result": {"status": "SUCCESS", "response": "L22_V002,222"}},
        ]
    )
    return [
        {
            "name": "result_response",
            "passed": "L21_V001,1500" in response_output and "[DONE]" in response_output,
            "output": response_output,
        },
        {
            "name": "result_error",
            "passed": "[ERROR]" in error_output and "auth failed" in error_output,
            "output": error_output,
        },
        {
            "name": "delta_result_no_duplicate",
            "passed": no_duplicate_output.count("L22_V002,222") == 1,
            "output": no_duplicate_output,
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    cases = asyncio.run(_run())
    passed = sum(int(case["passed"]) for case in cases)
    report = {
        "scenarios": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "errors": 0,
        "cases": cases,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(
            f"AGY RESULT STREAM: {'PASS' if passed == len(cases) else 'FAIL'}, "
            f"scenarios={len(cases)}, passed={passed}, failed={len(cases) - passed}"
        )
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
