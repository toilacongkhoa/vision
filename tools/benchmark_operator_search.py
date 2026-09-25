"""Regression benchmark for the manual text-search operator path.

The benchmark verifies that the frontend exposes every production search mode,
passes the selected mode to the search API, and that the API accepts/routes a
smart request without invoking the expensive real retrieval pipeline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PATH = PROJECT_ROOT / "frontend" / "index.html"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class _SearchModeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_search_mode = False
        self.current_value: Optional[str] = None
        self.current_label: List[str] = []
        self.options: Dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        attributes = dict(attrs)
        if tag == "select" and attributes.get("id") == "searchMode":
            self.in_search_mode = True
        elif tag == "option" and self.in_search_mode:
            self.current_value = attributes.get("value")
            self.current_label = []

    def handle_data(self, data: str) -> None:
        if self.current_value is not None:
            self.current_label.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self.current_value is not None:
            self.options[self.current_value] = " ".join("".join(self.current_label).split())
            self.current_value = None
            self.current_label = []
        elif tag == "select" and self.in_search_mode:
            self.in_search_mode = False


def _frontend_cases(source: str) -> List[Dict[str, Any]]:
    parser = _SearchModeParser()
    parser.feed(source)
    expected_modes = ["semantic", "smart", "ocr", "asr"]
    missing_modes = [mode for mode in expected_modes if mode not in parser.options]
    smart_label = parser.options.get("smart", "")
    mode_wiring = bool(
        re.search(
            r"mode\s*:\s*document\.getElementById\(\s*['\"]searchMode['\"]\s*\)\.value",
            source,
        )
    )
    search_endpoint = "/api/v1/search" in source
    return [
        {
            "name": "frontend_smart_mode",
            "passed": not missing_modes and bool(smart_label),
            "options": parser.options,
            "missing_modes": missing_modes,
        },
        {
            "name": "frontend_mode_request_wiring",
            "passed": mode_wiring and search_endpoint,
            "dynamic_mode": mode_wiring,
            "search_endpoint": search_endpoint,
        },
    ]


def _api_cases() -> List[Dict[str, Any]]:
    from src import main

    cases: List[Dict[str, Any]] = []
    try:
        request = main.SearchRequest(
            query="học sinh trong lớp",
            top_k=3,
            video_id="TEST_V001",
            mode="smart",
        )
        cases.append(
            {
                "name": "api_smart_schema",
                "passed": request.mode == "smart",
                "mode": request.mode,
            }
        )
    except Exception as exc:
        cases.append(
            {
                "name": "api_smart_schema",
                "passed": False,
                "error": repr(exc),
            }
        )
        return cases

    calls: List[Dict[str, Any]] = []
    original = main.search_engine.smart_search

    def fake_smart_search(**kwargs: Any) -> List[Dict[str, Any]]:
        calls.append(kwargs)
        return [
            {
                "video_id": "TEST_V001",
                "frame_idx": 123,
                "vector_id": 7,
                "score": 0.5,
            }
        ]

    try:
        main.search_engine.smart_search = fake_smart_search
        response = main.search_keyframes(request)
        first = response.get("results", [{}])[0]
        routed = calls == [
            {
                "query_text": "học sinh trong lớp",
                "top_k": 3,
                "video_id_filter": "TEST_V001",
            }
        ]
        output_correct = (
            response.get("mode") == "smart"
            and response.get("total_results") == 1
            and first.get("video_id") == "TEST_V001"
            and first.get("frame_idx") == 123
        )
        cases.append(
            {
                "name": "api_smart_routing_and_output",
                "passed": routed and output_correct,
                "routed": routed,
                "output_correct": output_correct,
                "video_id": first.get("video_id"),
                "frame_idx": first.get("frame_idx"),
            }
        )
    except Exception as exc:
        cases.append(
            {
                "name": "api_smart_routing_and_output",
                "passed": False,
                "error": repr(exc),
            }
        )
    finally:
        main.search_engine.smart_search = original
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", type=Path, default=FRONTEND_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    cases: List[Dict[str, Any]] = []
    try:
        source = args.frontend.read_text(encoding="utf-8")
        cases.extend(_frontend_cases(source))
    except Exception as exc:
        cases.append(
            {
                "name": "frontend_load",
                "passed": False,
                "error": repr(exc),
            }
        )
    try:
        cases.extend(_api_cases())
    except Exception as exc:
        cases.append(
            {
                "name": "api_load",
                "passed": False,
                "error": repr(exc),
            }
        )

    passed = sum(int(bool(case.get("passed"))) for case in cases)
    report = {
        "scenarios": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "errors": sum(int("error" in case) for case in cases),
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "cases": cases,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(
            f"OPERATOR SEARCH: {'PASS' if passed == len(cases) else 'FAIL'}, "
            f"scenarios={len(cases)}, passed={passed}, failed={len(cases) - passed}"
        )
        for case in cases:
            print(f"- {case['name']}: {'PASS' if case.get('passed') else 'FAIL'}")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
