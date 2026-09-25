"""Create and verify a SHA-256 manifest for external Vision data files."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys


DATA_FILES = (
    "video_index_v2.db",
    "all_vectors.npy",
    "video_drive_metadata.json",
    "video_fps_map.json",
    "frame_map_supabase.json",
)
MANIFEST_NAME = "vision-data.manifest.sha256"
CHUNK_SIZE = 8 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_manifest(root: Path) -> tuple[Path, list[str]]:
    root = root.resolve()
    manifest_path = root / MANIFEST_NAME
    lines = ["# Vision external data manifest v1; excludes local credentials and config."]
    missing = []
    for relative_name in DATA_FILES:
        path = root / relative_name
        if not path.is_file():
            missing.append(relative_name)
            continue
        lines.append(f"{sha256_file(path)}  {path.stat().st_size}  {relative_name}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest_path, missing


def verify_manifest(root: Path) -> list[str]:
    root = root.resolve()
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        return [f"Missing manifest: {manifest_path}"]

    errors = []
    seen = set()
    for line_number, raw_line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            expected_hash, expected_size, relative_name = line.split("  ", 2)
            expected_size = int(expected_size)
        except (ValueError, TypeError):
            errors.append(f"Malformed manifest line {line_number}")
            continue
        if relative_name not in DATA_FILES or relative_name in seen:
            errors.append(f"Unexpected or duplicate manifest entry: {relative_name}")
            continue
        seen.add(relative_name)
        path = root / relative_name
        if not path.is_file():
            errors.append(f"Missing data file: {relative_name}")
            continue
        actual_size = path.stat().st_size
        if actual_size != expected_size:
            errors.append(
                f"Size mismatch for {relative_name}: expected {expected_size}, got {actual_size}"
            )
            continue
        if sha256_file(path) != expected_hash:
            errors.append(f"SHA-256 mismatch for {relative_name}")

    for required in ("video_index_v2.db", "all_vectors.npy"):
        if required not in seen:
            errors.append(f"Manifest does not include required file: {required}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="hash available data files")
    create.add_argument("--root", type=Path, default=Path.cwd())
    verify = commands.add_parser("verify", help="verify hashes and file sizes")
    verify.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    if args.command == "create":
        path, missing = create_manifest(args.root)
        print(f"Wrote {path}")
        for name in missing:
            print(f"NOT INCLUDED (file absent): {name}")
        if "video_index_v2.db" in missing or "all_vectors.npy" in missing:
            print("ERROR: required search data is missing; manifest is incomplete.")
            return 1
        return 0

    errors = verify_manifest(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Data manifest verified: {args.root.resolve() / MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
