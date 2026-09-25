"""Local installation diagnostics. Does not start the server or download models."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import (  # noqa: E402
    BASE_DIR,
    CLIP_MODEL_NAME,
    CLIP_PRETRAINED,
    CONSOLIDATED_VECTORS_PATH,
    DATA_ROOT,
    DB_PATH,
    HOST,
    PORT,
)


results: list[tuple[str, str, str]] = []
database_rows: int | None = None
vector_rows: int | None = None


def report(level: str, label: str, detail: str) -> None:
    results.append((level, label, detail))
    print(f"{level:8} {label}: {detail}")


def check_python() -> None:
    if sys.version_info >= (3, 12):
        report("PASS", "Python", f"{sys.version.split()[0]} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")
        if sys.maxsize <= 2**32:
            report("ERROR", "Python architecture", "Install 64-bit Python for PyTorch/OpenCLIP.")
    else:
        report("ERROR", "Python", f"{sys.version.split()[0]} found; Python 3.12 or newer is required.")


def check_dependencies() -> None:
    modules = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "torch": "torch",
        "open_clip_torch": "open_clip",
        "numpy": "numpy",
        "pydantic": "pydantic",
        "python-dotenv": "dotenv",
    }
    missing = [dist for dist, module in modules.items() if importlib.util.find_spec(module) is None]
    if missing:
        report("ERROR", "Dependencies", "Missing: " + ", ".join(missing) + "; install requirements.txt.")
        return
    versions = []
    for dist in modules:
        try:
            versions.append(f"{dist} {importlib.metadata.version(dist)}")
        except importlib.metadata.PackageNotFoundError:
            pass
    report("PASS", "Dependencies", ", ".join(versions))
    try:
        checked = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            cwd=BASE_DIR,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if checked.returncode == 0:
            report("PASS", "pip check", "installed packages have no declared dependency conflicts.")
        else:
            details = (checked.stdout or checked.stderr).strip().replace("\n", "; ")
            report("DEGRADED", "pip check", details[:600] or "dependency conflicts were reported.")
    except (OSError, subprocess.TimeoutExpired) as exc:
        report("DEGRADED", "pip check", f"Could not complete pip check ({type(exc).__name__}).")


def check_sqlite() -> None:
    global database_rows
    if not DB_PATH.is_file():
        report("ERROR", "Database", f"Missing file: {DB_PATH}")
        return
    try:
        uri = DB_PATH.as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=3) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "keyframes" not in tables:
                report("ERROR", "Database schema", "Required table 'keyframes' was not found.")
                return
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(keyframes)")
            }
            required_columns = {"vector_id", "video_id", "frame_idx", "pts_time", "raw_json"}
            missing = sorted(required_columns - columns)
            if missing:
                report("ERROR", "Database schema", "Missing keyframes columns: " + ", ".join(missing))
                return
            count = connection.execute("SELECT COUNT(*) FROM keyframes").fetchone()[0]
            database_rows = int(count)
            sample = connection.execute(
                "SELECT video_id, frame_idx, pts_time, raw_json FROM keyframes "
                "WHERE video_id IS NOT NULL AND frame_idx IS NOT NULL "
                "AND pts_time IS NOT NULL LIMIT 1"
            ).fetchone()
            if count == 0 or sample is None:
                report("ERROR", "Database content", "No keyframe with Video ID, Frame ID and PTS was found.")
                return
            try:
                float(sample[2])
            except (TypeError, ValueError):
                report("ERROR", "Database sample", "The sample PTS value is not numeric.")
                return
            try:
                raw = json.loads(sample[3])
            except (TypeError, json.JSONDecodeError):
                report("ERROR", "Database sample", "A keyframe raw_json sample is invalid.")
                return
            if not isinstance(raw, dict):
                report("ERROR", "Database sample", "A keyframe raw_json sample is not an object.")
                return
            report("PASS", "Database", f"read-only schema OK; {count:,} rows; sample has video/frame/PTS.")
    except (sqlite3.Error, OSError, ValueError) as exc:
        report("ERROR", "Database", f"Cannot read configured DB ({type(exc).__name__}).")


def check_vectors() -> None:
    global vector_rows
    if not CONSOLIDATED_VECTORS_PATH.is_file():
        report("ERROR", "Vectors", f"Missing semantic/image search matrix: {CONSOLIDATED_VECTORS_PATH}")
        return
    try:
        import numpy as np

        matrix = np.load(CONSOLIDATED_VECTORS_PATH, mmap_mode="r", allow_pickle=False)
        if matrix.ndim != 2 or not matrix.shape[0] or not matrix.shape[1]:
            report("ERROR", "Vectors", f"Expected a non-empty 2D matrix; got shape {matrix.shape}.")
            return
        if matrix.dtype.kind != "f":
            report("ERROR", "Vectors", f"Expected floating point vectors; got {matrix.dtype}.")
            return
        vector_rows = int(matrix.shape[0])
        if database_rows is not None and vector_rows != database_rows:
            report("ERROR", "Vector alignment", f"Database has {database_rows:,} rows but vectors have {vector_rows:,} rows.")
            return
        report("PASS", "Vectors", f"shape={matrix.shape}, dtype={matrix.dtype}; inspected via memory map.")
    except Exception as exc:
        report("ERROR", "Vectors", f"Cannot open vector matrix ({type(exc).__name__}).")


def check_json_data(path: Path, label: str, required: bool) -> None:
    if not path.is_file():
        report("ERROR" if required else "DEGRADED", label, f"Missing file: {path}")
        return
    try:
        with path.open("r", encoding="utf-8") as stream:
            value: Any = json.load(stream)
        if label == "Video metadata" and not isinstance(value, dict):
            raise ValueError("root should be a JSON object")
        if label == "FPS metadata" and not isinstance(value, dict):
            raise ValueError("root should be a JSON object keyed by Video ID")
        report("PASS" if required else "OPTIONAL", label, "valid JSON")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        report("ERROR" if required else "DEGRADED", label, f"Cannot read valid JSON ({type(exc).__name__}).")


def check_model() -> None:
    try:
        import open_clip
        import torch

        cfg = open_clip.get_pretrained_cfg(CLIP_MODEL_NAME, CLIP_PRETRAINED)
        if not isinstance(cfg, dict):
            report("DEGRADED", "OpenCLIP weights", f"No local weight path can be confirmed for {CLIP_MODEL_NAME}/{CLIP_PRETRAINED}; search cannot encode until weights load.")
            return
        model_cfg = open_clip.get_model_config(CLIP_MODEL_NAME) or {}
        model_quick_gelu = bool(model_cfg.get("quick_gelu", False))
        pretrained_quick_gelu = bool(cfg.get("quick_gelu", False))
        if model_quick_gelu != pretrained_quick_gelu:
            report(
                "DEGRADED",
                "OpenCLIP activation",
                f"Model config quick_gelu={model_quick_gelu} differs from pretrained tag quick_gelu={pretrained_quick_gelu}; use the matching model variant.",
            )
        from urllib.parse import urlparse

        hf_repo = (cfg.get("hf_hub") or "").strip().strip("/")
        if hf_repo:
            repo_cache = Path(torch.hub.get_dir()).parent.parent / "huggingface" / "hub" / f"models--{hf_repo.replace('/', '--')}"
            hf_root = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{hf_repo.replace('/', '--')}"
            for cache_root in dict.fromkeys((repo_cache, hf_root)):
                if cache_root.is_dir():
                    checkpoint = next(
                        (
                            path
                            for filename in (
                                "open_clip_model.safetensors",
                                "model.safetensors",
                                "pytorch_model.bin",
                            )
                            for path in cache_root.glob(f"snapshots/*/{filename}")
                            if path.is_file() and path.stat().st_size > 1024 * 1024
                        ),
                        None,
                    )
                    if checkpoint:
                        report("PASS", "OpenCLIP weights", f"cached Hugging Face checkpoint found for {CLIP_MODEL_NAME}/{CLIP_PRETRAINED}.")
                        return

        url = cfg.get("url")
        if url:
            filename = Path(urlparse(url).path).name
            cache = Path(torch.hub.get_dir()) / "checkpoints" / filename
            if cache.is_file() and cache.stat().st_size > 0:
                report("PASS", "OpenCLIP weights", f"cached checkpoint found for {CLIP_MODEL_NAME}/{CLIP_PRETRAINED}.")
                return
        report("DEGRADED", "OpenCLIP weights", f"{CLIP_MODEL_NAME}/{CLIP_PRETRAINED} checkpoint not found in its Hugging Face or PyTorch cache; download/verify it before offline use.")
    except Exception as exc:
        report("DEGRADED", "OpenCLIP weights", f"Could not verify checkpoint cache ({type(exc).__name__}).")


def check_optional_services() -> None:
    agy = os.getenv("AGY_PATH", "agy")
    found = shutil.which(agy) if not Path(agy).is_absolute() else (agy if Path(agy).is_file() else None)
    if found:
        report("OPTIONAL", "Agy CLI", "available; Assistant can be enabled.")
    else:
        report("OPTIONAL", "Agy CLI", "not found; Assistant is unavailable, manual search remains usable.")
    cache_path = BASE_DIR / "translation_cache.db"
    offline_model = BASE_DIR / "models" / "opus-mt-vi-en-ct2"
    if offline_model.is_dir():
        report("OPTIONAL", "Offline translator", "model directory found.")
    else:
        report("DEGRADED", "Offline translator", "model absent; translation may use cache/online fallback and needs network for uncached queries.")
    if cache_path.is_file():
        report("OPTIONAL", "Translation cache", f"found ({cache_path.stat().st_size:,} bytes).")
    else:
        report("OPTIONAL", "Translation cache", "absent; it will be created/rebuilt as needed.")


def check_host_resources() -> None:
    try:
        free_bytes = shutil.disk_usage(BASE_DIR).free
        report("PASS" if free_bytes >= 2 * 1024**3 else "DEGRADED", "Disk space", f"{free_bytes / 1024**3:.1f} GiB free at project location; 2 GiB is the preflight minimum.")
    except OSError:
        report("DEGRADED", "Disk space", "could not inspect project volume.")
    if HOST in {"0.0.0.0", "::"}:
        report("DEGRADED", "Bind address", f"{HOST} exposes the service beyond loopback; set HOST=127.0.0.1 for a per-machine install.")
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        memory = MemoryStatus()
        memory.dwLength = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            report("INFO", "Memory", f"{memory.ullAvailPhys / 1024**3:.1f} GiB available / {memory.ullTotalPhys / 1024**3:.1f} GiB total; compare with the actual model/runtime peak before release.")
        else:
            report("DEGRADED", "Memory", "Windows could not report available physical memory.")
    except (AttributeError, OSError):
        report("INFO", "Memory", "physical memory details unavailable on this platform.")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((HOST, PORT))
        report("PASS", "Port", f"{HOST}:{PORT} is available.")
    except OSError:
        report("ERROR", "Port", f"{HOST}:{PORT} is occupied or cannot be bound; stop the other server or update PORT.")
    report("INFO", "Configuration", f"DB={DB_PATH}; vectors={CONSOLIDATED_VECTORS_PATH}; DATA_ROOT={DATA_ROOT}")


def main() -> int:
    print(f"Vision preflight - project {BASE_DIR}")
    check_python()
    check_dependencies()
    check_sqlite()
    check_vectors()
    check_json_data(BASE_DIR / "video_drive_metadata.json", "Video metadata", required=False)
    check_json_data(BASE_DIR / "video_fps_map.json", "FPS metadata", required=False)
    check_model()
    check_optional_services()
    check_host_resources()
    try:
        from tools.data_manifest import verify_manifest

        manifest_errors = verify_manifest(BASE_DIR)
        if manifest_errors:
            report("DEGRADED", "Data manifest", "Not verified: " + "; ".join(manifest_errors[:3]))
        else:
            report("PASS", "Data manifest", "file sizes and SHA-256 values match.")
    except Exception as exc:
        report("DEGRADED", "Data manifest", f"Verification unavailable ({type(exc).__name__}).")

    errors = sum(level == "ERROR" for level, _, _ in results)
    degraded = sum(level == "DEGRADED" for level, _, _ in results)
    print(f"\nSummary: {errors} blocking error(s), {degraded} degraded/optional warning(s).")
    print("No credentials are displayed. ERROR means the required local workflow is not ready.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
