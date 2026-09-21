"""Small static security scan for the MCP image URL boundary."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MCP_PATH = PROJECT_ROOT / "mcp_server.py"


def scan_mcp(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    match = re.search(
        r"async def search_image_by_url\(.*?(?=\n@\w+\.tool\(\)|\Z)",
        source,
        flags=re.DOTALL,
    )
    if match is None:
        return ["search_image_by_url function not found"]

    function_source = match.group(0)
    findings: list[str] = []
    if "_validate_external_image_url(image_url)" not in function_source:
        findings.append("search_image_by_url fetches image_url without URL validation")
    if "MAX_EXTERNAL_IMAGE_BYTES" not in function_source:
        findings.append("search_image_by_url fetches without an explicit response-size limit")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp", type=Path, default=MCP_PATH)
    args = parser.parse_args()
    findings = scan_mcp(args.mcp)
    print(f"MCP_IMAGE_URL_FINDINGS: {len(findings)}")
    for finding in findings:
        print(f"- {finding}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
