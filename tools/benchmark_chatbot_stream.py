"""Regression benchmark for chatbot SSE parsing and diagnostics."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Iterable, List

import benchmark_chatbot as chatbot


class _FakeResponse:
    def __init__(self, lines: Iterable[str]) -> None:
        self.lines = [line.encode("utf-8") for line in lines]

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def __iter__(self):
        return iter(self.lines)


def _run_stream(lines: List[str]) -> Dict[str, Any]:
    original = chatbot.urlopen
    chatbot.urlopen = lambda request, timeout: _FakeResponse(lines)
    try:
        return chatbot.call_chat("http://test/chat", "query", "session", 1.0)
    finally:
        chatbot.urlopen = original


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    plain = _run_stream(
        [
            "data: [TOOL] search_semantic_video\n",
            "data: VideoID: L21_V001, FrameIdx: 1500\n",
            "data: [DONE]\n",
        ]
    )
    json_delta = _run_stream(
        [
            'data: {"delta":"L22_V002,222"}\n',
            "data: [DONE]\n",
        ]
    )
    error = _run_stream(
        [
            "data: [ERROR] synthetic failure\n",
            "data: [DONE]\n",
        ]
    )

    cases = [
        {
            "name": "plain_text_and_tool",
            "passed": (
                chatbot.extract_video_frame_pairs(plain["text"]) == [("L21_V001", 1500)]
                and len(plain["tool_events"]) == 1
                and plain["sse_events"] == 3
                and plain["saw_done"]
            ),
            "response": plain,
        },
        {
            "name": "json_delta",
            "passed": (
                chatbot.extract_video_frame_pairs(json_delta["text"]) == [("L22_V002", 222)]
                and json_delta["sse_events"] == 2
                and json_delta["saw_done"]
            ),
            "response": json_delta,
        },
        {
            "name": "error_and_done",
            "passed": (
                error["errors"] == ["[ERROR] synthetic failure"]
                and error["sse_events"] == 2
                and error["saw_done"]
            ),
            "response": error,
        },
    ]
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
            f"CHATBOT STREAM: {'PASS' if passed == len(cases) else 'FAIL'}, "
            f"scenarios={len(cases)}, passed={passed}, failed={len(cases) - passed}"
        )
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
