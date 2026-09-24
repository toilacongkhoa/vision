"""Offline operator-to-DRES-export contract benchmark.

The benchmark invokes the local serialization route with a stub frame lookup
and checks that the UI exposes the JSON download path. It never contacts DRES.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import HTTPException  # noqa: E402
from src import main as app_module  # noqa: E402


class _FrameLookupStub:
    def search_frame_range(self, video_id: str, start_frame: int, end_frame: int, limit: int = 1):
        if video_id == "MISSING" or start_frame != end_frame:
            return []
        return [{"video_id": video_id, "frame_idx": start_frame, "pts_time": 12.3456}]


def _expect_error(call: Callable[[], object], status_code: int) -> None:
    try:
        call()
    except HTTPException as exc:
        if exc.status_code != status_code:
            raise AssertionError(f"expected HTTP {status_code}, got {exc.status_code}") from exc
        return
    raise AssertionError(f"expected HTTP {status_code}")


def run_benchmark() -> Tuple[int, int, List[str]]:
    html = (PROJECT_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    scenarios: List[Tuple[str, Callable[[], None]]] = []
    failures: List[str] = []

    original_engine = app_module.search_engine
    app_module.search_engine = _FrameLookupStub()
    try:
        scenarios.append(("kis_route_uses_exact_frame_pts", lambda: _assert_equal(
            app_module.export_dres_submission(app_module.DRESExportRequest(
                query_type="KIS", video_id="L1_V2", frame_idx=123
            )),
            {"answerSets": [{"answers": [{"mediaItemName": "L1_V2", "start": "12346", "end": "12346"}]}]},
        )))
        scenarios.append(("qa_route_includes_answer_and_location", lambda: _assert_equal(
            app_module.export_dres_submission(app_module.DRESExportRequest(
                query_type="QA", video_id="L1_V2", frame_idx=123, answer="màu xanh"
            )),
            {"answerSets": [{"answers": [{"text": "QA-màu xanh-L1_V2-12346"}]}]},
        )))
        scenarios.append(("trake_route_preserves_order", lambda: _assert_equal(
            app_module.export_dres_submission(app_module.DRESExportRequest(
                query_type="TRAKE", video_id="L1_V2", frame_ids=[100, 150, 205]
            )),
            {"answerSets": [{"answers": [{"text": "TR-L1_V2-100,150,205"}]}]},
        )))
        scenarios.append(("missing_exact_frame_rejected", lambda: _expect_error(
            lambda: app_module.export_dres_submission(app_module.DRESExportRequest(
                query_type="KIS", video_id="MISSING", frame_idx=123
            )),
            404,
        )))
        scenarios.append(("invalid_trake_sequence_rejected", lambda: _expect_error(
            lambda: app_module.export_dres_submission(app_module.DRESExportRequest(
                query_type="TRAKE", video_id="L1_V2", frame_ids=[150, 100]
            )),
            422,
        )))
        for name, scenario in scenarios:
            try:
                scenario()
            except Exception as exc:
                failures.append(f"{name}: {type(exc).__name__}: {exc}")
    finally:
        app_module.search_engine = original_engine

    ui_scenarios = [
        ("dres_download_button_present", lambda: _assert_contains(html, 'id="btnExportDres"')),
        ("ui_calls_local_export_route", lambda: _assert_contains(html, "/api/v1/submission/dres/export")),
        ("ui_requires_one_selected_answer", lambda: _assert_contains(html, "exactly one selected answer")),
        ("ui_download_handler_only_downloads_reviewed_json", lambda: _assert_download_handler_only_downloads_json(html)),
    ]
    scenarios.extend(ui_scenarios)
    for name, scenario in ui_scenarios:
        try:
            scenario()
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    return len(scenarios) - len(failures), len(scenarios), failures


def _assert_equal(actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def _assert_contains(actual: str, expected: str) -> None:
    if expected not in actual:
        raise AssertionError(f"missing expected UI contract {expected!r}")


def _assert_download_handler_only_downloads_json(html: str) -> None:
    marker = "document.getElementById('btnDownloadReviewedDres').onclick"
    start = html.find(marker)
    if start < 0:
        raise AssertionError("reviewed JSON download handler is missing")
    end = html.find("\n        };", start)
    if end < 0:
        raise AssertionError("reviewed JSON download handler is incomplete")
    handler = html[start:end]
    if "fetch(" in handler or "/api/v1/dres/submit" in handler:
        raise AssertionError("reviewed JSON download handler must not submit to DRES")
    if "URL.createObjectURL(blob)" not in handler or "link.click()" not in handler:
        raise AssertionError("reviewed JSON download handler must download the JSON file")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print a JSON summary")
    args = parser.parse_args()
    passed, total, failures = run_benchmark()
    if args.json:
        print(json.dumps({"passed": passed, "total": total, "failed": failures}, ensure_ascii=True))
    else:
        print(f"DRES operator export: {passed}/{total} pass, {len(failures)} fail")
        for failure in failures:
            print(f"FAIL {failure}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
