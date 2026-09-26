import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['HF_HUB_OFFLINE'] = '1'

import torch
# torch.set_num_threads(1)

import os
import sys
import ssl
import json
import sqlite3
import time
import math
import hashlib
import uuid
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal

# Ensure UTF-8 console output for Windows compatibility
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .agy_session import AgySession, is_complex_visual_query, session_pool
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import asyncio
class CandidateFrame(BaseModel):
    video_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    frame_idx: int = Field(..., ge=0, le=10_000_000)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    question_type: Literal["KIS_TEXT", "KIS_VIDEO", "QA", "TRAKE"] = "KIS_TEXT"
    description: str = Field("", max_length=4000)
    clues: List[str] = Field(default_factory=list, max_length=20)
    remaining_seconds: Optional[int] = Field(None, ge=0, le=300)
    pinned_frames: List[CandidateFrame] = Field(default_factory=list, max_length=20)


class FrameValidationRequest(BaseModel):
    candidates: List[CandidateFrame] = Field(default_factory=list, max_length=20)

from .config import DATA_ROOT, DB_PATH, CONSOLIDATED_VECTORS_PATH, TRAFFIC_DB_PATH, BASE_DIR, HOST, PORT, CORS_ORIGINS
from .sqlite_engine import SQLiteSearchEngine as VectorSearchEngine
from .traffic_search import TrafficSearchEngine
from .supabase_service import SupabaseService
from .dres_submission import (
    SubmissionError,
    build_kis_payload,
    build_qa_payload,
    build_trake_payload,
    validate_payload,
)
from .dres_api import create_dres_router

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

app = FastAPI(
    title="Video Retrieval & Supabase Google Drive API Backend",
    description="High-performance Video Keyframe Retrieval Backend with Supabase REST API & Google Drive Integration",
    version="2.1.0"
)
AGY_PREWARM_ON_STARTUP = os.getenv("AGY_PREWARM_ON_STARTUP", "true").strip().lower() not in {
    "0", "false", "no", "off"
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_root_path = Path(DATA_ROOT).resolve()
search_engine = VectorSearchEngine(data_root=data_root_path)
traffic_search_engine = TrafficSearchEngine(TRAFFIC_DB_PATH)
supabase_svc = SupabaseService(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)

frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


class SearchSimilarRequest(BaseModel):
    vector_id: int = Field(..., description="Vector ID of the frame to find similar images")
    top_k: int = Field(50, ge=1, le=200, description="Number of top matching results to retrieve")

class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query in English")
    top_k: int = Field(50, ge=1, le=200, description="Number of top matching results to retrieve")
    video_id: Optional[str] = Field(None, description="Optional Video ID filter constraint")
    mode: Literal["semantic", "smart", "ocr", "asr"] = Field("smart", description="Search mode: smart, semantic, ocr, or asr")

class SearchAllRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    top_k: int = Field(50, ge=1, le=200)
    video_id: Optional[str] = None


class TrafficSearchRequest(BaseModel):
    camera_id: Optional[str] = Field(None, max_length=32)
    video_id: Optional[str] = Field(None, max_length=64)
    object_class: Optional[str] = Field(None, max_length=64)
    color: Optional[str] = Field(None, max_length=64)
    direction: Optional[str] = Field(None, max_length=64)
    motion_state: Optional[str] = Field(None, max_length=64)
    event_type: Optional[str] = Field(None, max_length=128)
    start_time: Optional[float] = Field(None, ge=0)
    end_time: Optional[float] = Field(None, ge=0)
    min_confidence: float = Field(0.0, ge=0, le=1)
    min_severity: float = Field(0.0, ge=0, le=1)
    limit: int = Field(50, ge=1, le=200)


class DRESExportRequest(BaseModel):
    query_type: Literal["KIS", "QA", "TRAKE"]
    video_id: str = Field(..., min_length=1)
    frame_idx: Optional[int] = Field(None, ge=0)
    answer: Optional[str] = None
    frame_ids: Optional[List[int]] = None


@app.on_event("startup")
async def startup_event():
    print("[Startup] Video Retrieval & Supabase Backend online!", flush=True)
    if not AGY_PREWARM_ON_STARTUP:
        print("[Startup] Agy prewarming disabled by AGY_PREWARM_ON_STARTUP.", flush=True)
        return
    import asyncio
    
    async def warm_ai_sessions():
        async def warm_one(sid: str, model: str, label: str):
            try:
                print(f"[Startup] Background pre-warming {label} model...", flush=True)
                if sid not in session_pool:
                    session = AgySession(sid, model=model)
                    session_pool[sid] = session
                    await session.start(prewarm=True)
                print(f"[Startup] {label} model ready!", flush=True)
            except Exception as e:
                print(f"[Startup] {label} pre-warm notice: {e}", flush=True)

        await asyncio.gather(
            warm_one("local-flash", "flash", "Flash"),
            warm_one("local-pro", "pro", "Pro"),
        )

    asyncio.create_task(warm_ai_sessions())
    print("[Startup] Server ready to accept HTTP traffic!", flush=True)


@app.get("/")
def read_root():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "service": "Video Retrieval System & Supabase Backend API",
        "version": "2.1.0",
        "status": "online",
        "supabase_configured": supabase_svc.is_configured,
        "docs": "/docs"
    }


@app.get("/api/v1/health")
def health_check():
    database_connected = False
    total_keyframes = 0
    database_error = None
    try:
        db_path = Path(DB_PATH).resolve()
        with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=2) as conn:
            row = conn.execute("SELECT COUNT(*) FROM keyframes").fetchone()
            total_keyframes = int(row[0])
            sample = conn.execute(
                "SELECT video_id, frame_idx, pts_time FROM keyframes "
                "WHERE video_id IS NOT NULL AND frame_idx IS NOT NULL "
                "AND pts_time IS NOT NULL LIMIT 1"
            ).fetchone()
            database_connected = total_keyframes > 0 and sample is not None
            if not database_connected:
                database_error = "No indexed frame with Video ID, Frame ID and PTS."
    except (sqlite3.Error, OSError) as exc:
        database_error = type(exc).__name__

    vector_matrix_loaded = getattr(search_engine, "vectors", None) is not None
    clip_model_loaded = getattr(search_engine, "model", None) is not None
    search_ready = database_connected and vector_matrix_loaded and clip_model_loaded
    searchable_modes = []
    if database_connected:
        searchable_modes.extend(["ocr", "asr"])
    if database_connected and vector_matrix_loaded and clip_model_loaded:
        searchable_modes.extend(["semantic", "smart", "image"])
    return {
        "status": "healthy" if search_ready else "degraded",
        "search_ready": search_ready,
        "searchable_modes": searchable_modes,
        "supabase_connected": supabase_svc.is_configured,
        "database_connected": database_connected,
        "database_error": database_error,
        "vector_matrix_loaded": vector_matrix_loaded,
        "clip_model_loaded": clip_model_loaded,
        "total_keyframes": total_keyframes,
    }


# Load video metadata into memory
video_metadata_cache = {}
try:
    with open(BASE_DIR / "video_drive_metadata.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        if "videos" in data:
            video_metadata_cache = data["videos"]

    # M/N/S Drive mappings are kept in a small, tracked overlay because the
    # full metadata JSON is a local dataset artifact and is intentionally
    # ignored by git. Existing L mappings and richer video metadata win unless
    # the overlay explicitly supplies the two Drive fields.
    drive_index_path = BASE_DIR / "docs" / "drive_video_index.jsonl"
    if drive_index_path.exists():
        with open(drive_index_path, "r", encoding="utf-8-sig") as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                mapping = json.loads(line)
                video_id = mapping.get("video_id")
                if video_id not in video_metadata_cache:
                    raise ValueError(
                        f"Unknown video_id in Drive index at line {line_number}: {video_id}"
                    )
                video_metadata_cache[video_id]["drive_file_id"] = mapping["drive_file_id"]
                video_metadata_cache[video_id]["drive_url"] = mapping["drive_url"]
except Exception as e:
    print(f"Warning: Could not load video_drive_metadata.json: {e}")

@app.get("/api/v1/video/{video_id}")
def get_video_info(video_id: str):
    info = video_metadata_cache.get(video_id)
    if not info:
        raise HTTPException(status_code=404, detail="Video metadata not found")
    return {
        "video_id": video_id,
        "drive_file_id": info.get("drive_file_id"),
        "drive_url": info.get("drive_url")
    }


# ====================================================================
# SUPABASE & GOOGLE DRIVE ENDPOINTS
# ====================================================================

@app.get("/api/v1/supabase/video/{video_id}")
def get_supabase_video(video_id: str):
    """Retrieve video metadata & Google Drive File IDs directly from Supabase."""
    video = supabase_svc.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video ID '{video_id}' not found in Supabase")
    return video


@app.get("/api/v1/supabase/frame/{frame_id}")
def get_supabase_frame(frame_id: str):
    """Retrieve single frame metadata & Google Drive CDN Image URL directly from Supabase."""
    frame = supabase_svc.get_frame(frame_id)
    if not frame:
        raise HTTPException(status_code=404, detail=f"Frame ID '{frame_id}' not found in Supabase")
    return frame


@app.get("/api/v1/supabase/video/{video_id}/frames")
def get_supabase_video_frames(video_id: str, limit: int = Query(500, ge=1, le=2000)):
    """Retrieve all keyframes of a video ordered by frame_number from Supabase."""
    frames = supabase_svc.get_frames_by_video(video_id, limit=limit)
    return {
        "video_id": video_id,
        "total_frames": len(frames),
        "frames": frames
    }


import asyncio
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from fastapi.responses import Response

# Limit concurrent Google Drive requests to prevent 403 Rate Limits and thread blocking
drive_semaphore = asyncio.Semaphore(8)
drive_executor = ThreadPoolExecutor(max_workers=8)

@lru_cache(maxsize=1000)
def fetch_drive_file_cached(file_id: str) -> tuple[bytes, str]:
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req, context=ssl_context, timeout=20)
    return res.read(), res.headers.get('Content-Type', 'application/octet-stream')

async def fetch_drive_file_async(file_id: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(drive_executor, fetch_drive_file_cached, file_id)

@app.get("/api/v1/drive/proxy/{file_id}")
async def proxy_google_drive_file(file_id: str):
    """Proxy any file content from Google Drive with in-memory LRU caching."""
    async with drive_semaphore:
        for attempt in range(3):
            try:
                content, mime_type = await fetch_drive_file_async(file_id)
                return Response(content=content, media_type=mime_type)
            except Exception as e:
                if attempt == 2:
                    raise HTTPException(status_code=500, detail=f"Failed fetching Google Drive File {file_id}: {str(e)}")
                await asyncio.sleep(0.5)


# ====================================================================
# VECTOR SEARCH ENDPOINTS
# ====================================================================

@app.get("/api/v1/traffic/filters")
def traffic_filters():
    if not traffic_search_engine.available():
        raise HTTPException(status_code=503, detail="Traffic camera database is not available")
    return {"status": "success", **traffic_search_engine.filters()}


@app.post("/api/v1/traffic/search")
def traffic_search(request: TrafficSearchRequest):
    if not traffic_search_engine.available():
        raise HTTPException(status_code=503, detail="Traffic camera database is not available")
    params = request.model_dump()
    if params.get("start_time") is not None and params.get("end_time") is not None and params["end_time"] < params["start_time"]:
        raise HTTPException(status_code=422, detail="end_time must be greater than or equal to start_time")
    rows = traffic_search_engine.search(**params)
    results = []
    for row in rows:
        approximate_frame = round(row["preview_time"] * float(row.get("source_fps") or 25.0))
        frame = search_engine.nearest_frame_by_time(row["video_id"], row["preview_time"]) or {}
        confidence = float(row.get("confidence") or 0.0)
        result = {
            **row,
            "frame_idx": frame.get("frame_idx", approximate_frame),
            "pts_time": frame.get("pts_time", row["preview_time"]),
            "timestamp": frame.get("timestamp"),
            "image_path": frame.get("image_path"),
            "r2_url": frame.get("r2_url"),
            "gdrive_file_id": frame.get("gdrive_file_id"),
            "object_file_id": frame.get("object_file_id"),
            "ocr_json_id": frame.get("ocr_json_id"),
            "vector_id": frame.get("vector_id"),
            "score": round(confidence * 100.0, 2),
        }
        results.append(result)
    applied_filters = {key: value for key, value in params.items() if value not in (None, "", 0.0) and key != "limit"}
    return {"status": "success", "total": len(results), "interpreted_filters": applied_filters, "results": results}

@app.get("/api/v1/search/context")
def search_context(video_id: str, frame_idx: int, limit: int = 50, surrounding: bool = False):
    results = search_engine.search_context(video_id, frame_idx, limit, surrounding=surrounding)
    return {"status": "success", "results": results}

@app.get("/api/v1/video/{video_id}/frames")
def video_frames(video_id: str, start_frame: int, end_frame: int, limit: int = 80):
    """Return the stored keyframes in a bounded range for smooth filmstrip prefetching."""
    if end_frame < start_frame:
        start_frame, end_frame = end_frame, start_frame
    limit = max(1, min(limit, 200))
    results = search_engine.search_frame_range(video_id, start_frame, end_frame, limit)
    return {"status": "success", "video_id": video_id, "start_frame": start_frame, "end_frame": end_frame, "results": results}

@app.get("/api/v1/video/{video_id}/filmstrip")
def video_filmstrip(video_id: str, anchor_frame: int, direction: str = "around", limit: int = 40):
    if direction not in {"around", "before", "after"}:
        raise HTTPException(status_code=400, detail="direction must be around, before, or after")
    results = search_engine.search_frame_page(video_id, anchor_frame, direction, limit)
    return {"status": "success", "video_id": video_id, "anchor_frame": anchor_frame, "direction": direction, "results": results}

@app.get("/api/v1/video/{video_id}/asr")
def video_asr(video_id: str, center_time: float, window: float = 30.0, limit: int = 100):
    """Return ASR transcript around the preview timestamp without loading the video."""
    window = max(1.0, min(float(window), 300.0))
    center_time = max(0.0, float(center_time))
    start_time = max(0.0, center_time - window)
    end_time = center_time + window
    segments = search_engine.get_asr_segments(video_id, start_time, end_time, limit)
    return {
        "status": "success",
        "video_id": video_id,
        "center_time": center_time,
        "start_time": start_time,
        "end_time": end_time,
        "segments": segments,
    }

@app.get("/api/v1/search/interval")
def search_interval(video_id: str, start_time: float, end_time: float, limit: int = 200):
    results = search_engine.search_interval(video_id, start_time, end_time, limit)
    return {"status": "success", "results": results}

@app.get("/api/v1/video/{video_id}/convert_time")
def convert_time_to_frame(video_id: str, time_sec: float, fps: float = 25.0):
    # Fetch actual FPS from local JSON map to be portable across machines
    actual_fps = fps
    try:
        json_path = BASE_DIR / "video_fps_map.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                fps_map = json.load(f)
                if video_id in fps_map:
                    actual_fps = fps_map[video_id]
    except Exception as e:
        print(f"Warning: Could not read local FPS map: {e}")

    frame_idx = round(time_sec * actual_fps)
    return {"status": "success", "video_id": video_id, "time_sec": time_sec, "frame_idx": frame_idx, "fps": actual_fps}


def _fps_for_video(video_id: str) -> float:
    """Return configured FPS, falling back to 25 when metadata is unavailable."""
    try:
        json_path = BASE_DIR / "video_fps_map.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                fps_map = json.load(f)
            if isinstance(fps_map, dict):
                fps = float(fps_map.get(video_id, 25.0))
                if fps > 0 and math.isfinite(fps):
                    return fps
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return 25.0


@app.post("/api/v1/submission/dres/export")
def export_dres_submission(request: DRESExportRequest):
    """Serialize one selected answer as a DRES body; this endpoint does not submit it."""
    try:
        if request.query_type == "TRAKE":
            if request.frame_idx is not None or request.frame_ids is None:
                raise SubmissionError("TRAKE export requires frame_ids only")
            payload = build_trake_payload(request.video_id, request.frame_ids)
        else:
            if request.frame_idx is None or request.frame_ids is not None:
                raise SubmissionError("KIS/Q&A export requires one frame_idx only")
            candidates = search_engine.search_frame_range(
                request.video_id, request.frame_idx, request.frame_idx, limit=1
            )
            pts_time = None
            if candidates and int(candidates[0].get("frame_idx", -1)) == request.frame_idx:
                pts_time = candidates[0].get("pts_time")
            # Allow operators to export even when the selected frame is absent
            # from the local index or has no PTS. This estimate may be inaccurate
            # for variable-frame-rate sources, so the review UI marks it clearly.
            if pts_time is None:
                pts_time = request.frame_idx / _fps_for_video(request.video_id)
            if request.query_type == "KIS":
                payload = build_kis_payload(request.video_id, pts_time)
            else:
                payload = build_qa_payload(request.video_id, pts_time, request.answer or "")
        validate_payload(payload, request.query_type)
        return payload
    except SubmissionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


app.include_router(create_dres_router())

@app.post("/api/v1/search/similar")
def search_similar(req: SearchSimilarRequest):
    results = search_engine.search(
        query_text="",
        query_vector_id=req.vector_id,
        top_k=req.top_k
    )
    return {"status": "success", "results": results}

@app.post("/api/v1/search/image")
async def search_by_image(file: UploadFile = File(...), top_k: int = Form(50), video_id: Optional[str] = Form(None)):
    image_bytes = await file.read()
    results = await asyncio.to_thread(
        search_engine.search_by_image,
        image_bytes,
        top_k=top_k,
        video_id_filter=video_id,
    )
    return {
        "status": "success",
        "total_results": len(results),
        "results": results
    }


def validate_frame_candidates(candidates: List[CandidateFrame]) -> List[Dict[str, Any]]:
    """Return only candidates whose exact Video ID/frame pair exists in the index."""
    verified = []
    db_path = Path(DB_PATH).resolve()
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=2) as conn:
        for candidate in candidates:
            row = conn.execute(
                "SELECT video_id, frame_idx, pts_time FROM keyframes "
                "WHERE video_id = ? AND frame_idx = ? AND pts_time IS NOT NULL LIMIT 1",
                (candidate.video_id, candidate.frame_idx),
            ).fetchone()
            if row is not None:
                verified.append({
                    "video_id": str(row[0]),
                    "frame_idx": int(row[1]),
                    "pts_time": float(row[2]),
                })
    return verified


@app.post("/api/v1/frames/validate")
async def validate_frames(req: FrameValidationRequest):
    try:
        verified = await asyncio.to_thread(validate_frame_candidates, req.candidates)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Frame index is unavailable") from exc
    return {"verified": verified}

@app.post("/api/v1/chat")
async def chat_endpoint(req: ChatRequest):
    # TRAKE needs sequence reasoning; other routes use the light model unless
    # the request itself clearly describes multiple linked events.
    is_complex = req.question_type == "TRAKE" or is_complex_visual_query(req.message)

    # Keep each client's Agy conversation isolated.  The model is part of the
    # key so switching between simple and complex routing cannot mix contexts.
    client_session_id = (req.session_id or "").strip()
    if not client_session_id or client_session_id == "local-user":
        client_session_id = uuid.uuid4().hex
    session_digest = hashlib.sha256(client_session_id.encode("utf-8")).hexdigest()[:24]
    route = "pro" if is_complex else "flash"
    sid = f"chat-{route}-{session_digest}"
    
    if sid not in session_pool:
        session = AgySession(sid, model=route)
        session_pool[sid] = session
    else:
        session = session_pool[sid]

    try:
        verified_pins = await asyncio.to_thread(validate_frame_candidates, req.pinned_frames)
    except sqlite3.Error:
        verified_pins = []
    type_guidance = {
        "KIS_TEXT": "Find one best-supported frame. Track which textual/visual clues are verified; use OCR or ASR only when the clue concerns on-screen text or speech.",
        "KIS_VIDEO": "Return a short visual shortlist early, then inspect candidate frames or a sequence. Do not ask for or reconstruct a recording of the query clip.",
        "QA": "Find and verify the scene, then answer the question only from visible, OCR, ASR, or indexed context evidence. State what evidence is missing.",
        "TRAKE": "Split the request into ordered events, search each stage, and require one video with strictly increasing indexed frame IDs. Mark missing stages instead of guessing.",
    }[req.question_type]
    context_lines = [
        "[EXAM WORKSPACE CONTEXT]",
        f"Question type: {req.question_type}",
        f"Workflow: {type_guidance}",
    ]
    if req.description.strip():
        context_lines.append("Question description: " + req.description.strip())
    clues = [clue.strip() for clue in req.clues if clue.strip()]
    if clues:
        context_lines.append("Clues in order:\n" + "\n".join(f"{i}. {clue}" for i, clue in enumerate(clues, 1)))
    if req.remaining_seconds is not None:
        context_lines.append(f"Time remaining on the local question timer: {req.remaining_seconds} seconds.")
    if verified_pins:
        context_lines.append("Verified pinned candidates (Video ID, indexed Frame ID, source PTS seconds):\n" + "\n".join(
            f"- {item['video_id']}, {item['frame_idx']}, {item['pts_time']:.3f}s" for item in verified_pins
        ))
    elif req.pinned_frames:
        context_lines.append("No pinned candidate was verified in the frame index; do not use the submitted IDs as evidence.")
    context_lines.append("Only report a candidate Video ID and Frame ID after a search tool returns it; never invent IDs or calculate PTS from FPS.")
    context_lines.append("Answer in Vietnamese with: primary/alternate candidates, cited tool evidence for each, confidence and why, missing evidence, and one next action. For TRAKE, list each ordered stage with its verified Video ID/Frame ID and mark any missing stage.")
    assistant_message = "\n".join(context_lines) + "\n\n[USER MESSAGE]\n" + req.message

    async def gen():
        try:
            async for chunk in session.send_message(assistant_message):
                yield chunk
        except asyncio.CancelledError:
            await session.close()
            raise
        except Exception as exc:
            await session.close()
            yield f"data: [ERROR] Lỗi hệ thống ({type(exc).__name__}); phiên đã được dọn.\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

@app.post("/api/v1/search")
def search_keyframes(req: SearchRequest):
    import time
    start_time = time.time()
    
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    # Fast Local/Cached Auto-translate Vietnamese to English for semantic search
    if req.mode == "semantic":
        try:
            from .fast_translator import fast_translator
            translated = fast_translator.translate(req.query)
            if translated != req.query:
                print(f"[FastTranslator] '{req.query}' -> '{translated}'", flush=True)
                req.query = translated
        except Exception as e:
            print(f"[FastTranslator] Translation warning: {e}", flush=True)

    if req.mode == "ocr":
        results = search_engine.exact_ocr_search(
            query_text=req.query,
            top_k=req.top_k,
            video_id_filter=req.video_id
        )
        print(f"[Search API] OCR search took {time.time() - start_time:.3f}s", flush=True)
    elif req.mode == "asr":
        results = search_engine.exact_asr_search(
            query_text=req.query,
            top_k=req.top_k,
            video_id_filter=req.video_id
        )
        print(f"[Search API] ASR search took {time.time() - start_time:.3f}s", flush=True)
    elif req.mode == "smart":
        results = search_engine.smart_search(
            query_text=req.query,
            top_k=req.top_k,
            video_id_filter=req.video_id,
        )
        print(f"[Search API] Smart hybrid search took {time.time() - start_time:.3f}s", flush=True)
    else:
        results = search_engine.search(
            query_text=req.query,
            top_k=req.top_k,
            video_id_filter=req.video_id
        )

    return {
        "query": req.query,
        "mode": req.mode,
        "total_results": len(results),
        "results": results
    }

def _search_one_mode(query: str, mode: str, top_k: int, video_id: Optional[str]):
    """Run one independent retrieval branch for the all-modes endpoint."""
    if mode == "semantic":
        return search_engine.search(query_text=query, top_k=top_k, video_id_filter=video_id)
    if mode == "ocr":
        return search_engine.exact_ocr_search(query, top_k=top_k, video_id_filter=video_id)
    return search_engine.exact_asr_search(query, top_k=top_k, video_id_filter=video_id)

@app.post("/api/v1/search/all")
async def search_all_modes(req: SearchAllRequest):
    """Search CLIP, OCR and ASR concurrently; the UI renders each branch separately."""
    import asyncio
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    async def run(mode: str):
        started = time.perf_counter()
        results = await asyncio.to_thread(
            _search_one_mode, req.query, mode, req.top_k, req.video_id
        )
        return mode, {
            "status": "complete",
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "total_results": len(results),
            "results": results,
        }

    branches = await asyncio.gather(*(run(mode) for mode in ("semantic", "ocr", "asr")))
    return {"query": req.query, "results": dict(branches)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)

