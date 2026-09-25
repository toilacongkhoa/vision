import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables if .env file exists
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

# Data directory root path
DATA_ROOT = Path(os.getenv("DATA_ROOT", str(BASE_DIR / "data"))).resolve()

# Directory structure conventions inside DATA_ROOT
CLIP_DIR_NAME = os.getenv("CLIP_DIR_NAME", "CLIP")
KEYFRAMES_DIR_NAME = os.getenv("KEYFRAMES_DIR_NAME", "keyframes")
MAPPING_DIR_NAME = os.getenv("MAPPING_DIR_NAME", "map_keyframes")

# Database & Vector storage paths
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "video_index_v2.db"))).resolve()
CONSOLIDATED_VECTORS_PATH = Path(os.getenv("CONSOLIDATED_VECTORS_PATH", str(BASE_DIR / "all_vectors.npy"))).resolve()
TRAFFIC_DB_PATH = Path(os.getenv("TRAFFIC_DB_PATH", str(BASE_DIR / "camera" / "traffic_search.db"))).resolve()

# Allowed file extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
CSV_EXTENSIONS = {".csv", ".tsv", ".txt"}
VECTOR_EXTENSIONS = {".npy"}

# CLIP Model Settings
CLIP_MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "ViT-B-32-quickgelu")
CLIP_PRETRAINED = os.getenv("CLIP_PRETRAINED", "openai")

# Server Settings
# This application is installed per operator machine. Keep it private to the
# local machine unless the operator explicitly configures a LAN bind.
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
