"""Download/cache the configured OpenCLIP checkpoint for later offline use."""

from __future__ import annotations

import gc
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Runtime deliberately forces offline mode. This one-time operator command
# permits Hugging Face to use the network if its checkpoint is not cached.
os.environ.pop("HF_HUB_OFFLINE", None)

from src.config import CLIP_MODEL_NAME, CLIP_PRETRAINED  # noqa: E402

os.environ.pop("HF_HUB_OFFLINE", None)


def main() -> int:
    try:
        import open_clip

        model, _, _ = open_clip.create_model_and_transforms(
            CLIP_MODEL_NAME, pretrained=CLIP_PRETRAINED, device="cpu"
        )
        del model
        gc.collect()
        print(f"OpenCLIP checkpoint cached: {CLIP_MODEL_NAME}/{CLIP_PRETRAINED}")
        return 0
    except Exception as exc:
        print(
            f"Could not cache OpenCLIP checkpoint ({type(exc).__name__}). "
            "Check network access and rerun tools/preflight.py."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
