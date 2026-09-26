"""Local contract smoke for structured Assistant workspace context.

Uses a fake Agy session and the local frame index; it never contacts Agy or
transmits benchmark queries. Run from the repository root:
    python tools/benchmark_chat_workspace.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import ValidationError
from src import main as app_module


class FakeAgySession:
    instances = []

    def __init__(self, session_id: str, model: str):
        self.session_id = session_id
        self.model = model
        self.message = ""
        self.closed = False
        self.instances.append(self)

    async def send_message(self, message: str):
        self.message = message
        if "[DELAY MOCK]" in message:
            await asyncio.sleep(0.1)
        yield "data: [DONE]\n\n"

    async def close(self):
        self.closed = True


async def collect_response(request):
    response = await app_module.chat_endpoint(request)
    return [chunk async for chunk in response.body_iterator]


def require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


async def run_checks():
    original_session = app_module.AgySession
    real_timeout = asyncio.timeout
    app_module.AgySession = FakeAgySession
    FakeAgySession.instances.clear()
    app_module.session_pool.clear()
    try:
        request = app_module.ChatRequest(
            message="Tìm giúp cảnh phù hợp.",
            session_id="workspace-contract",
            question_type="QA",
            description="Một người cầm chiếc ô đỏ.",
            clues=["Đường phố ướt sau mưa."],
            remaining_seconds=92,
            pinned_frames=[
                {"video_id": "L26_V183", "frame_idx": 5895},
                {"video_id": "NO_SUCH_VIDEO", "frame_idx": 42},
            ],
        )
        await collect_response(request)
        session = FakeAgySession.instances[-1]
        require(session.model == "flash", "simple QA should use the flash route")
        for expected in (
            "Question type: QA",
            "Một người cầm chiếc ô đỏ.",
            "Đường phố ướt sau mưa.",
            "92 seconds",
            "L26_V183, 5895, 235.800s",
        ):
            require(expected in session.message, f"assistant context is missing: {expected}")
        require("NO_SUCH_VIDEO" not in session.message, "unindexed pinned frame leaked into context")

        trake = app_module.ChatRequest(message="Tìm các sự kiện.", question_type="TRAKE")
        await collect_response(trake)
        require(FakeAgySession.instances[-1].model == "pro", "TRAKE should use the pro route")
        require("ordered events" in FakeAgySession.instances[-1].message, "TRAKE guidance is missing")

        multi_event = app_module.ChatRequest(
            message="Một người bước vào phòng. Sau đó người đó ngồi xuống.",
            question_type="KIS_VIDEO",
        )
        await collect_response(multi_event)
        require(FakeAgySession.instances[-1].model == "pro", "multi-event KIS should use the pro route")

        try:
            app_module.ChatRequest(message="bad type", question_type="OTHER")
        except ValidationError:
            pass
        else:
            raise AssertionError("unsupported question_type should be rejected")

        timeout_request = app_module.ChatRequest(message="[DELAY MOCK]", session_id="no-chat-deadline")
        timeout_response = await app_module.chat_endpoint(timeout_request)
        timeout_chunks = [chunk async for chunk in timeout_response.body_iterator]
        timeout_session = FakeAgySession.instances[-1]
        require(not timeout_session.closed, "chat session was closed despite a normal response")
        require(any("[DONE]" in chunk for chunk in timeout_chunks), "long-running response did not finish normally")
        require("asyncio.timeout(120)" not in (ROOT / "src" / "main.py").read_text(encoding="utf-8"), "120-second route deadline is still configured")

        cancel_request = app_module.ChatRequest(message="[DELAY MOCK]", session_id="cancel")
        cancel_response = await app_module.chat_endpoint(cancel_request)
        cancel_task = asyncio.create_task(_drain(cancel_response))
        await asyncio.sleep(0.01)
        cancel_task.cancel()
        try:
            await cancel_task
        except asyncio.CancelledError:
            pass
        cancel_session = FakeAgySession.instances[-1]
        require(cancel_session.closed, "session was not closed after client cancellation")

        print("PASS structured context and verified pin (5 checks)")
        print("PASS question-type and multi-event routing (2 checks)")
        print("PASS invalid question type rejected (1 check)")
        print("PASS unbounded chat response and client-cancel cleanup (3 checks)")
    finally:
        app_module.asyncio.timeout = real_timeout
        app_module.AgySession = original_session
        app_module.session_pool.clear()


async def _drain(response):
    async for _chunk in response.body_iterator:
        pass


if __name__ == "__main__":
    asyncio.run(run_checks())
