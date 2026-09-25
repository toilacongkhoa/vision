"""Run isolated Agy candidate-selection sessions on a frozen VLM manifest.

Only the query and at most five candidate frame IDs enter the model prompt.
Each subprocess runs in an empty temporary directory. Stream events are checked
so a scored result must have called exactly one inspect_candidate_grid tool with
the manifest's five frame pairs. Reading that tool's local schema is allowed.
"""

from __future__ import annotations

import argparse
import json
import ntpath
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from benchmark_vlm_selection import _validate_manifest, candidate_set_digest


def _prompt(case: dict[str, Any], profile: str) -> str:
    candidates = [
        {
            "candidate_id": item["candidate_id"],
            "video_id": item["video_id"],
            "frame_idx": item["frame_idx"],
        }
        for item in case["candidates"]
    ]
    common = (
        "Candidate-selection benchmark. Call ONLY "
        "video-researcher/inspect_candidate_grid exactly once with the five "
        "candidates below, in the listed order. Do not search or read files. "
        "Use only the returned images and the query. Return one JSON object "
        "with primary_candidate_id, ranked_candidate_ids (all five IDs best "
        "to worst), answer (null for KIS), confidence (0 to 1), and "
        "visual_evidence. No markdown.\n"
    )
    if profile == "evidence":
        common += (
            "Before ranking, check every candidate against the specific "
            "objects, action, text, and sequence in the query. Reject a "
            "lookalike when a required detail is visibly absent. Base the "
            "answer on evidence at the selected location.\n"
        )
    return (
        common + "QUERY:\n" + case["query"] + "\nCANDIDATES:\n"
        + json.dumps(candidates, ensure_ascii=False)
    )


def _response_json(response: str) -> dict[str, Any]:
    clean = response.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(clean)
    if not isinstance(data, dict):
        raise ValueError("final response is not a JSON object")
    return data


def _audit_tools(case: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    calls = [
        item["step_update"] for item in events
        if item.get("event") == "step_update"
        and item.get("step_update", {}).get("step_type") == "tool"
        and item["step_update"].get("state") == "ACTIVE"
    ]
    done_grid = [
        item["step_update"] for item in events
        if item.get("event") == "step_update"
        and item.get("step_update", {}).get("step_type") == "tool"
        and item["step_update"].get("state") == "DONE"
        and item["step_update"].get("tool_name") == "call_mcp_tool"
    ]
    image_paths = set()
    for item in done_grid:
        output = str(item.get("tool_info", {}).get("output", ""))
        for match in re.finditer(r"file:///([^\]\s]+\.jpg)", output, flags=re.IGNORECASE):
            image_paths.add(ntpath.normcase(ntpath.normpath(unquote(match.group(1)))))
    expected_schema = ntpath.normcase(ntpath.normpath(str(
        Path.home() / ".gemini" / "antigravity-cli" / "mcp"
        / "video-researcher" / "inspect_candidate_grid.json"
    )))
    schema_reads = []
    image_reads = []
    for call in calls:
        if call.get("tool_name") != "view_file":
            continue
        path = ntpath.normcase(ntpath.normpath(str(
            call.get("tool_info", {}).get("parameters", {}).get("AbsolutePath", "")
        )))
        if path == expected_schema:
            schema_reads.append(call)
        elif path in image_paths:
            image_reads.append(call)
    grid_calls = [call for call in calls if call.get("tool_name") == "call_mcp_tool"]
    expected_frames = [
        (item["video_id"], item["frame_idx"]) for item in case["candidates"]
    ]
    grid_valid = False
    if len(grid_calls) == 1:
        parameters = grid_calls[0].get("tool_info", {}).get("parameters", {})
        actual = parameters.get("Arguments", {}).get("candidates", [])
        grid_valid = (
            parameters.get("ServerName") == "video-researcher"
            and parameters.get("ToolName") == "inspect_candidate_grid"
            and [(item.get("video_id"), item.get("frame_idx")) for item in actual]
            == expected_frames
        )
    return {
        "tool_calls": len(calls),
        "schema_reads": len(schema_reads),
        "image_reads": len(image_reads),
        "grid_calls": len(grid_calls),
        "tool_names": [call.get("tool_name") for call in calls],
        "tool_contract_valid": grid_valid and len(calls) == 1 + len(schema_reads) + len(image_reads),
    }


def _run_case(case: dict[str, Any], model: str, profile: str, timeout: int,
              stream_path: Path) -> dict[str, Any]:
    args = [
        "agy", "-p", _prompt(case, profile), "--model", model,
        "--output-format", "stream-json", "--print-timeout", f"{timeout}s",
        "--dangerously-skip-permissions",
    ]
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="vision-vlm-") as scratch:
        try:
            process = subprocess.run(
                args, cwd=scratch, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout + 30,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {"timed_out": True, "error": f"subprocess timeout: {exc}",
                    "latency_ms": (time.perf_counter() - started) * 1000}
    latency_ms = (time.perf_counter() - started) * 1000
    stream_path.write_text(process.stdout, encoding="utf-8")
    try:
        events = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        return {"error": f"invalid Agy stream: {exc}", "latency_ms": latency_ms,
                "exit_code": process.returncode}
    initial = next((item["init"] for item in events if item.get("event") == "init"), {})
    result = next((item["result"] for item in events if item.get("event") == "result"), {})
    conversation_id = next(
        (item.get("conversation_id") for item in events if item.get("event") == "init"), None
    )
    audit = _audit_tools(case, events)
    tool_valid = audit["tool_contract_valid"]
    error = None
    final = {}
    if process.returncode or result.get("status") != "SUCCESS":
        error = f"Agy exit={process.returncode} status={result.get('status')}"
    elif initial.get("model") != model or not conversation_id:
        error = "model or conversation ID mismatch"
    elif not tool_valid:
        error = f"tool contract failed: {audit['tool_names']}"
    else:
        try:
            final = _response_json(str(result.get("response", "")))
        except (ValueError, IndexError) as exc:
            error = f"invalid model response: {exc}"
    usage = result.get("usage") or {}
    return {
        "conversation_id": conversation_id,
        "model": initial.get("model"),
        **audit,
        "primary_candidate_id": final.get("primary_candidate_id"),
        "ranked_candidate_ids": final.get("ranked_candidate_ids", []),
        "answer": final.get("answer"),
        "confidence": final.get("confidence"),
        "visual_evidence": final.get("visual_evidence"),
        "latency_ms": round(latency_ms, 2),
        "model_duration_ms": round(float(result.get("duration_seconds", 0)) * 1000, 2),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "timed_out": bool(result.get("status") == "TIMEOUT"),
        "error": error,
        "exit_code": process.returncode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--model", default="gemini-3.8-flash-medium")
    parser.add_argument("--profile", choices=("baseline", "evidence"), default="baseline")
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--case-id", help="Run only one case for a pilot")
    parser.add_argument("--audit-dir", type=Path, help="Directory for raw Agy event streams")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = _validate_manifest(manifest)
    if errors:
        parser.error("invalid manifest: " + "; ".join(errors))
    cases = [case for case in manifest["cases"] if not args.case_id or case["case_id"] == args.case_id]
    if not cases:
        parser.error("case ID not found")
    for case in cases:
        frames = [(item.get("video_id"), item.get("frame_idx")) for item in case["candidates"]]
        if len(frames) != 5 or len(set(frames)) != 5 or any(item.get("frames") for item in case["candidates"]):
            parser.error(f"{case['case_id']} must have exactly five unique single-frame candidates")
    existing = []
    if args.results.exists():
        existing = [json.loads(line) for line in args.results.read_text(encoding="utf-8").splitlines() if line.strip()]
    completed = {(row["case_id"], row["run_id"]) for row in existing}
    sessions = {row.get("conversation_id") for row in existing if row.get("conversation_id")}
    audit_dir = args.audit_dir or args.results.parent / (args.results.stem + "_streams")
    audit_dir.mkdir(parents=True, exist_ok=True)
    for run_number in range(1, args.runs + 1):
        run_id = f"{args.run_prefix}-{run_number:02d}"
        for case in cases:
            key = (case["case_id"], run_id)
            if key in completed:
                continue
            stream_path = audit_dir / f"{run_id}_{case['case_id']}.jsonl"
            record = _run_case(case, args.model, args.profile, args.timeout, stream_path)
            if record.get("conversation_id") in sessions:
                record["error"] = "reused conversation ID"
            if record.get("conversation_id"):
                sessions.add(record["conversation_id"])
            record.update({
                "case_id": case["case_id"],
                "run_id": run_id,
                "candidate_set_sha256": candidate_set_digest(case),
                "profile": args.profile,
            })
            with args.results.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            completed.add(key)
            print(
                f"{run_id} {case['case_id']}: primary={record['primary_candidate_id']} "
                f"tool_ok={record['tool_contract_valid']} error={record['error']} "
                f"latency_ms={record['latency_ms']}", flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
