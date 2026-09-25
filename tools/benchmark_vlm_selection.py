"""Score repeated VLM candidate-selection runs against a frozen manifest.

The manifest fixes the query and candidate IDs/pairs. A separate runner writes
one JSONL record per case/run with a primary candidate and ordered alternatives.
This tool scores only the primary output for Top-1 while reporting Hit@K/MRR,
high-confidence errors, latency, and optional token/cost fields.
Q&A manifests list accepted_answers; full-answer accuracy requires both the
primary location and answer to be correct.

Example::

    python tools/benchmark_vlm_selection.py --manifest cases.json \
        --results runs.jsonl --min-runs 5 --json

Run ``--self-test`` to validate the scoring contract without model/API access.
Self-test fixtures are synthetic and do not count as VLM accuracy results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = 1
MIN_INDEPENDENT_RUNS = 5
# Welch degrees of freedom are at least four with five runs per side. Using
# t(4) is conservative when more degrees of freedom are available.
CONSERVATIVE_T95 = 2.7764451051977987
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def candidate_set_digest(case: Dict[str, Any]) -> str:
    """Hash candidate identity and frame pairs so repeated runs cannot drift."""
    candidates = [
        {
            "candidate_id": str(item["candidate_id"]),
            "frames": item.get("frames") or [{
                "video_id": item.get("video_id"),
                "frame_idx": item.get("frame_idx"),
            }],
        }
        for item in case.get("candidates", [])
    ]
    return hashlib.sha256(_canonical_json(candidates)).hexdigest()


def _normalise_answer(value: str) -> str:
    return " ".join(value.split()).casefold()


def _validate_manifest(manifest: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty list")
        return errors
    seen_cases = set()
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{prefix}.case_id must be a non-empty string")
        elif case_id in seen_cases:
            errors.append(f"duplicate case_id: {case_id}")
        seen_cases.add(case_id)
        if case.get("query_type") not in {"KIS", "QA", "TRAKE"}:
            errors.append(f"{prefix}.query_type must be KIS, QA, or TRAKE")
        if case.get("query_type") == "QA":
            answers = case.get("accepted_answers")
            if not isinstance(answers, list) or not answers or any(
                not isinstance(answer, str) or not answer.strip() for answer in answers
            ):
                errors.append(f"{prefix}.accepted_answers must list verified non-empty answers")
        if not isinstance(case.get("query"), str) or not case["query"].strip():
            errors.append(f"{prefix}.query must be a non-empty string")
        candidates = case.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            errors.append(f"{prefix}.candidates must be a non-empty list")
            continue
        candidate_ids = []
        for cindex, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                errors.append(f"{prefix}.candidates[{cindex}] must be an object")
                continue
            cid = candidate.get("candidate_id")
            if not isinstance(cid, str) or not cid.strip():
                errors.append(f"{prefix}.candidates[{cindex}].candidate_id is required")
            else:
                candidate_ids.append(cid)
            frames = candidate.get("frames")
            if frames is None:
                frames = [{"video_id": candidate.get("video_id"), "frame_idx": candidate.get("frame_idx")}]
            if not isinstance(frames, list) or not frames:
                errors.append(f"{prefix}.candidates[{cindex}] must identify one frame or a sequence")
            elif any(
                not isinstance(frame, dict)
                or not isinstance(frame.get("video_id"), str)
                or not isinstance(frame.get("frame_idx"), int)
                for frame in frames
            ):
                errors.append(f"{prefix}.candidates[{cindex}] frames need video_id and integer frame_idx")
        if len(candidate_ids) != len(set(candidate_ids)):
            errors.append(f"{prefix} candidate_id values must be unique")
        accepted = case.get("accepted_candidate_ids")
        if not isinstance(accepted, list) or not accepted:
            errors.append(f"{prefix}.accepted_candidate_ids must list the verified correct choice(s)")
        elif any(cid not in candidate_ids for cid in accepted):
            errors.append(f"{prefix}.accepted_candidate_ids contains an unknown candidate")
        if case.get("query_type") == "TRAKE":
            accepted_ids = {cid for cid in accepted if isinstance(cid, str)} if isinstance(accepted, list) else set()
            for candidate in candidates:
                frames = candidate.get("frames")
                if not isinstance(frames, list) or len(frames) < 2:
                    errors.append(f"{prefix} TRAKE candidates must contain an ordered frames sequence")
                    continue
                # Reversed, repeated, or cross-video sequences are useful hard
                # negatives, but they must never be labelled as correct.
                if candidate.get("candidate_id") in accepted_ids and all(
                    isinstance(frame, dict)
                    and isinstance(frame.get("video_id"), str)
                    and isinstance(frame.get("frame_idx"), int)
                    for frame in frames
                ):
                    videos = {frame["video_id"] for frame in frames}
                    ordered = all(
                        earlier["frame_idx"] < later["frame_idx"]
                        for earlier, later in zip(frames, frames[1:])
                    )
                    if len(videos) != 1 or not ordered:
                        errors.append(
                            f"{prefix} accepted TRAKE candidate {candidate['candidate_id']!r} "
                            "must have one video and strictly increasing frame_idx"
                        )
    return errors


def _percentile(values: Sequence[float], p: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def score(manifest: Dict[str, Any], result_rows: Iterable[Dict[str, Any]], min_runs: int = MIN_INDEPENDENT_RUNS,
          high_confidence: float = 0.8) -> Dict[str, Any]:
    errors = _validate_manifest(manifest)
    if errors:
        raise ValueError("invalid manifest: " + "; ".join(errors))

    cases = {case["case_id"]: case for case in manifest["cases"]}
    expected = {
        case_id: {"ids": {item["candidate_id"] for item in case["candidates"]},
                  "accepted": set(case["accepted_candidate_ids"]),
                  "answers": {_normalise_answer(answer) for answer in case.get("accepted_answers", [])},
                  "digest": candidate_set_digest(case)}
        for case_id, case in cases.items()
    }
    seen_runs = set()
    records: List[Dict[str, Any]] = []
    input_errors: List[str] = []
    for row_num, row in enumerate(result_rows, start=1):
        if not isinstance(row, dict):
            input_errors.append(f"line {row_num}: record must be an object")
            continue
        case_id, run_id = row.get("case_id"), row.get("run_id")
        if case_id not in cases:
            input_errors.append(f"line {row_num}: unknown case_id {case_id!r}")
            continue
        if not isinstance(run_id, str) or not run_id:
            input_errors.append(f"line {row_num}: run_id is required")
            continue
        pair_key = (case_id, run_id)
        if pair_key in seen_runs:
            input_errors.append(f"line {row_num}: duplicate case_id/run_id {pair_key}")
            continue
        seen_runs.add(pair_key)

        expected_set = expected[case_id]
        drift = row.get("candidate_set_sha256") != expected_set["digest"]
        ranked = row.get("ranked_candidate_ids") or []
        if not isinstance(ranked, list) or any(not isinstance(cid, str) for cid in ranked):
            input_errors.append(f"line {row_num}: ranked_candidate_ids must be a list of IDs")
            ranked = []
        primary = row.get("primary_candidate_id")
        if primary is not None and not isinstance(primary, str):
            input_errors.append(f"line {row_num}: primary_candidate_id must be a string or null")
            primary = None
        if primary and (not ranked or ranked[0] != primary):
            input_errors.append(f"line {row_num}: primary_candidate_id must equal ranked_candidate_ids[0]")
        unknown = sorted(set(ranked + ([primary] if primary else [])) - expected_set["ids"])
        if unknown:
            input_errors.append(f"line {row_num}: unknown candidate IDs {unknown}")
        if len(ranked) != len(set(ranked)):
            input_errors.append(f"line {row_num}: ranked_candidate_ids contains duplicates")
        answer = row.get("answer")
        if answer is not None and not isinstance(answer, str):
            input_errors.append(f"line {row_num}: answer must be a string or null")
            answer = None

        confidence = row.get("confidence")
        if confidence is not None and (not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1):
            input_errors.append(f"line {row_num}: confidence must be between 0 and 1")
            confidence = None
        latency = row.get("latency_ms")
        if latency is not None and (not isinstance(latency, (int, float)) or latency < 0):
            input_errors.append(f"line {row_num}: latency_ms must be non-negative")
            latency = None
        if drift:
            input_errors.append(f"line {row_num}: candidate set drift for {case_id}/{run_id}")

        hit_rank = next((index for index, cid in enumerate(ranked, 1) if cid in expected_set["accepted"]), None)
        top1_correct = primary in expected_set["accepted"] if primary else False
        is_qa = cases[case_id]["query_type"] == "QA"
        answer_correct = bool(is_qa and answer and _normalise_answer(answer) in expected_set["answers"])
        full_answer_correct = bool(top1_correct and (answer_correct if is_qa else True))
        records.append({
            "case_id": case_id,
            "query_type": cases[case_id]["query_type"],
            "run_id": run_id,
            "primary_candidate_id": primary,
            "top1_correct": top1_correct,
            "answer_correct": answer_correct if is_qa else None,
            "full_answer_correct": full_answer_correct,
            "hit_rank": hit_rank,
            "confidence": float(confidence) if confidence is not None else None,
            "high_confidence_wrong": bool(primary and confidence is not None and confidence >= high_confidence and not full_answer_correct),
            "latency_ms": float(latency) if latency is not None else None,
            "input_tokens": row.get("input_tokens"),
            "output_tokens": row.get("output_tokens"),
            "cost": row.get("cost"),
            "timed_out": bool(row.get("timed_out", False)),
            "candidate_set_stable": not drift,
        })

    by_case_runs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_case_runs[record["case_id"]].append(record)
    coverage = {
        case_id: {"runs": len(by_case_runs.get(case_id, [])), "minimum_runs": min_runs,
                  "meets_minimum": len(by_case_runs.get(case_id, [])) >= min_runs}
        for case_id in cases
    }

    def aggregate(selected: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(selected)
        latencies = [r["latency_ms"] for r in selected if r["latency_ms"] is not None]
        hit_ranks = [r["hit_rank"] for r in selected if r["hit_rank"] is not None]
        inputs = [r["input_tokens"] for r in selected if isinstance(r["input_tokens"], (int, float))]
        outputs = [r["output_tokens"] for r in selected if isinstance(r["output_tokens"], (int, float))]
        costs = [r["cost"] for r in selected if isinstance(r["cost"], (int, float))]
        denom = total or 1
        qa_at_correct_location = [r for r in selected if r["query_type"] == "QA" and r["top1_correct"]]
        return {
            "runs": total,
            "top1_correct": sum(r["top1_correct"] for r in selected),
            "top1_accuracy": sum(r["top1_correct"] for r in selected) / denom,
            "full_answer_correct": sum(r["full_answer_correct"] for r in selected),
            "full_answer_accuracy": sum(r["full_answer_correct"] for r in selected) / denom,
            "qa_answer_correct_given_location": sum(bool(r["answer_correct"]) for r in qa_at_correct_location),
            "qa_answer_accuracy_given_location": (
                sum(bool(r["answer_correct"]) for r in qa_at_correct_location) / len(qa_at_correct_location)
                if qa_at_correct_location else None
            ),
            "hit_at_3": sum(r["hit_rank"] is not None and r["hit_rank"] <= 3 for r in selected),
            "hit_at_5": sum(r["hit_rank"] is not None and r["hit_rank"] <= 5 for r in selected),
            "mrr": (sum(1.0 / rank for rank in hit_ranks) / denom) if total else 0.0,
            "high_confidence_wrong": sum(r["high_confidence_wrong"] for r in selected),
            "high_confidence_threshold": high_confidence,
            "timeout_rate": sum(r["timed_out"] for r in selected) / denom,
            "latency_ms_p50": _percentile(latencies, 0.50),
            "latency_ms_p95": _percentile(latencies, 0.95),
            "input_tokens_total": sum(inputs) if inputs else None,
            "output_tokens_total": sum(outputs) if outputs else None,
            "cost_total": sum(costs) if costs else None,
            "candidate_sets_stable": all(r["candidate_set_stable"] for r in selected),
        }

    type_groups = {
        query_type: aggregate([r for r in records if r["query_type"] == query_type])
        for query_type in ("KIS", "QA", "TRAKE")
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_cases": len(cases),
        "result_runs": len(records),
        "min_runs": min_runs,
        "case_run_coverage": coverage,
        "coverage_complete": all(value["meets_minimum"] for value in coverage.values()),
        "aggregate": aggregate(records),
        "by_query_type": type_groups,
        "input_errors": input_errors,
        "records": records,
    }


def compare_reports(baseline: Dict[str, Any], candidate: Dict[str, Any],
                    metric: str = "top1_accuracy") -> Dict[str, Any]:
    """Compare complete independent runs over the same frozen case set."""
    if metric not in {"top1_accuracy", "full_answer_accuracy", "mrr", "latency_ms"}:
        raise ValueError(f"unsupported comparison metric: {metric}")
    case_ids = set(baseline["case_run_coverage"])
    reasons = []
    if case_ids != set(candidate["case_run_coverage"]):
        reasons.append("case sets differ")

    def run_values(report: Dict[str, Any], label: str) -> List[float]:
        if report["input_errors"] or not report["coverage_complete"]:
            reasons.append(f"{label} has input errors or fewer than five runs per case")
            return []
        if not report["aggregate"]["candidate_sets_stable"]:
            reasons.append(f"{label} candidate set drift")
            return []
        by_run: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for record in report["records"]:
            by_run[record["run_id"]].append(record)
        values = []
        for run_id, records in by_run.items():
            if {record["case_id"] for record in records} != case_ids or len(records) != len(case_ids):
                reasons.append(f"{label} run {run_id!r} does not cover every case exactly once")
                continue
            if metric == "latency_ms":
                if any(record["latency_ms"] is None for record in records):
                    reasons.append(f"{label} run {run_id!r} has missing latency")
                    continue
                values.append(statistics.mean(record["latency_ms"] for record in records))
            elif metric == "mrr":
                values.append(statistics.mean(
                    1.0 / record["hit_rank"] if record["hit_rank"] else 0.0
                    for record in records
                ))
            elif metric == "full_answer_accuracy":
                values.append(statistics.mean(float(record["full_answer_correct"]) for record in records))
            else:
                values.append(statistics.mean(float(record["top1_correct"]) for record in records))
        if len(values) < MIN_INDEPENDENT_RUNS:
            reasons.append(f"{label} has fewer than five complete independent runs")
        return values

    before = run_values(baseline, "baseline")
    after = run_values(candidate, "candidate")
    result: Dict[str, Any] = {
        "metric": metric,
        "comparable": not reasons,
        "reasons": reasons,
        "baseline_runs": len(before),
        "candidate_runs": len(after),
        "independence_note": "Run IDs are distinct; separate model sessions must be verified by the runner.",
    }
    if reasons:
        return result

    baseline_mean = statistics.mean(before)
    candidate_mean = statistics.mean(after)
    baseline_sd = statistics.stdev(before)
    candidate_sd = statistics.stdev(after)
    difference = candidate_mean - baseline_mean
    standard_error = math.sqrt(baseline_sd ** 2 / len(before) + candidate_sd ** 2 / len(after))
    margin = CONSERVATIVE_T95 * standard_error
    lower, upper = difference - margin, difference + margin
    higher_is_better = metric != "latency_ms"
    ci_excludes_zero = lower > 0 if higher_is_better else upper < 0
    exceeds_noise = difference > 2 * baseline_sd if higher_is_better else -difference > 2 * baseline_sd
    latency_reduction = (
        (baseline_mean - candidate_mean) / baseline_mean
        if metric == "latency_ms" and baseline_mean > 0 else None
    )
    def case_mean(report: Dict[str, Any], case_id: str) -> float:
        records = [record for record in report["records"] if record["case_id"] == case_id]
        if metric == "latency_ms":
            return statistics.mean(record["latency_ms"] for record in records)
        if metric == "mrr":
            return statistics.mean(
                1.0 / record["hit_rank"] if record["hit_rank"] else 0.0
                for record in records
            )
        if metric == "full_answer_accuracy":
            return statistics.mean(float(record["full_answer_correct"]) for record in records)
        return statistics.mean(float(record["top1_correct"]) for record in records)

    by_case = []
    for case_id in sorted(case_ids):
        before_case = case_mean(baseline, case_id)
        after_case = case_mean(candidate, case_id)
        case_diff = after_case - before_case
        by_case.append({"case_id": case_id, "baseline_mean": before_case,
                        "candidate_mean": after_case, "difference": case_diff,
                        "regressed": case_diff < 0 if higher_is_better else case_diff > 0})
    result.update({
        "baseline_mean": baseline_mean,
        "baseline_sd": baseline_sd,
        "candidate_mean": candidate_mean,
        "candidate_sd": candidate_sd,
        "difference": difference,
        "difference_ci95_conservative": [lower, upper],
        "ci_excludes_zero_in_improvement_direction": ci_excludes_zero,
        "difference_exceeds_2x_baseline_sd": exceeds_noise,
        "latency_reduction": latency_reduction,
        "by_case": by_case,
        "regressed_cases": [item["case_id"] for item in by_case if item["regressed"]],
        "statistical_threshold_met": ci_excludes_zero and exceeds_noise and (
            metric != "latency_ms" or (latency_reduction is not None and latency_reduction >= 0.10)
        ),
    })
    return result


def _self_test() -> Dict[str, Any]:
    manifest = {
        "schema_version": 1,
        "cases": [{
            "case_id": "kis-fixed",
            "query_type": "KIS",
            "query": "a person cooks soup",
            "candidates": [
                {"candidate_id": "correct", "video_id": "V1", "frame_idx": 10},
                {"candidate_id": "near-miss", "video_id": "V2", "frame_idx": 20},
                {"candidate_id": "other", "video_id": "V3", "frame_idx": 30},
            ],
            "accepted_candidate_ids": ["correct"],
        }],
    }
    digest = candidate_set_digest(manifest["cases"][0])
    rows = [
        {"case_id": "kis-fixed", "run_id": "r1", "candidate_set_sha256": digest,
         "primary_candidate_id": "correct", "ranked_candidate_ids": ["correct", "near-miss"],
         "confidence": 0.9, "latency_ms": 100, "input_tokens": 20, "output_tokens": 5, "cost": 0.01},
        {"case_id": "kis-fixed", "run_id": "r2", "candidate_set_sha256": digest,
         "primary_candidate_id": "near-miss", "ranked_candidate_ids": ["near-miss", "correct"],
         "confidence": 0.95, "latency_ms": 200, "timed_out": False},
        {"case_id": "kis-fixed", "run_id": "r3", "candidate_set_sha256": digest,
         "primary_candidate_id": "other", "ranked_candidate_ids": ["other", "correct"],
         "confidence": 0.5, "latency_ms": 300},
    ]
    report = score(manifest, rows, min_runs=3)
    five_run_report = score(
        manifest,
        rows + [dict(rows[0], run_id="r4"), dict(rows[0], run_id="r5")],
        min_runs=MIN_INDEPENDENT_RUNS,
    )
    insufficient_report = score(manifest, rows)
    a = report["aggregate"]
    checks = {
        "primary_top1_is_separate_from_any_hit": a["top1_correct"] == 1 and a["hit_at_3"] == 3,
        "ranked_hit_mrr": abs(a["mrr"] - (1 + 0.5 + 0.5) / 3) < 1e-12,
        "high_confidence_wrong_counted": a["high_confidence_wrong"] == 1,
        "latency_percentiles": a["latency_ms_p50"] == 200 and a["latency_ms_p95"] == 290,
        "candidate_set_hash_stable": a["candidate_sets_stable"],
        "three_run_scoring_fixture_complete": report["coverage_complete"],
        "three_runs_insufficient_for_model_decision": not insufficient_report["coverage_complete"],
        "five_runs_sufficient_for_coverage": five_run_report["coverage_complete"],
    }
    def trake_manifest(accepted_frames: List[Tuple[str, int]]) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "cases": [{
                "case_id": "trake-fixed",
                "query_type": "TRAKE",
                "query": "event one then event two",
                "candidates": [
                    {"candidate_id": "accepted", "frames": [
                        {"video_id": video, "frame_idx": frame} for video, frame in accepted_frames
                    ]},
                    {"candidate_id": "negative", "frames": [
                        {"video_id": "V2", "frame_idx": 200},
                        {"video_id": "V2", "frame_idx": 100},
                    ]},
                ],
                "accepted_candidate_ids": ["accepted"],
            }],
        }

    checks.update({
        "trake_valid_accepted_sequence": not _validate_manifest(trake_manifest([("V1", 100), ("V1", 200)])),
        "trake_reversed_accepted_rejected": bool(_validate_manifest(trake_manifest([("V1", 200), ("V1", 100)]))),
        "trake_duplicate_accepted_rejected": bool(_validate_manifest(trake_manifest([("V1", 100), ("V1", 100)]))),
        "trake_cross_video_accepted_rejected": bool(_validate_manifest(trake_manifest([("V1", 100), ("V2", 200)]))),
    })
    baseline_rows = [dict(rows[1], run_id=f"base-{index}") for index in range(5)]
    candidate_rows = [dict(rows[0], run_id=f"candidate-{index}") for index in range(5)]
    baseline_report = score(manifest, baseline_rows)
    candidate_report = score(manifest, candidate_rows)
    gain = compare_reports(baseline_report, candidate_report)
    neutral = compare_reports(baseline_report, baseline_report)
    insufficient = compare_reports(insufficient_report, candidate_report)
    two_case_manifest = {"schema_version": 1, "cases": [
        manifest["cases"][0], dict(manifest["cases"][0], case_id="kis-second"),
    ]}
    split_run_rows = baseline_rows + [
        dict(row, case_id="kis-second", run_id=f"second-{index}")
        for index, row in enumerate(baseline_rows)
    ]
    split_run_report = score(two_case_manifest, split_run_rows)
    split_runs = compare_reports(split_run_report, split_run_report)
    checks.update({
        "five_run_gain_passes_statistical_gate": gain.get("statistical_threshold_met") is True
        and gain["difference_ci95_conservative"] == [1.0, 1.0],
        "unchanged_model_fails_statistical_gate": neutral.get("statistical_threshold_met") is False,
        "three_run_comparison_rejected": not insufficient["comparable"],
        "incomplete_run_panels_rejected": not split_runs["comparable"],
    })
    qa_case = {
        "case_id": "qa-fixed", "query_type": "QA", "query": "What color?",
        "accepted_answers": ["blue", "azure"],
        "candidates": [
            {"candidate_id": "correct", "video_id": "V1", "frame_idx": 100},
            {"candidate_id": "wrong", "video_id": "V2", "frame_idx": 200},
        ],
        "accepted_candidate_ids": ["correct"],
    }
    qa_manifest = {"schema_version": 1, "cases": [qa_case]}
    qa_digest = candidate_set_digest(qa_case)
    def qa_report(primary: str, answer: Optional[str]) -> Dict[str, Any]:
        ranked = [primary, "wrong" if primary == "correct" else "correct"]
        return score(qa_manifest, [{
            "case_id": "qa-fixed", "run_id": f"qa-{index}",
            "candidate_set_sha256": qa_digest, "primary_candidate_id": primary,
            "ranked_candidate_ids": ranked, "answer": answer, "confidence": 0.95,
        } for index in range(5)])
    qa_wrong_answer = qa_report("correct", "red")
    qa_correct = qa_report("correct", "  AZURE  ")
    qa_wrong_location = qa_report("wrong", "blue")
    qa_missing_answer = qa_report("correct", None)
    qa_gain = compare_reports(qa_wrong_answer, qa_correct, "full_answer_accuracy")
    checks.update({
        "qa_wrong_answer_not_full_correct": qa_wrong_answer["aggregate"]["top1_correct"] == 5
        and qa_wrong_answer["aggregate"]["full_answer_correct"] == 0,
        "qa_correct_alias_is_full_correct": qa_correct["aggregate"]["full_answer_correct"] == 5,
        "qa_correct_answer_wrong_location_fails": qa_wrong_location["aggregate"]["full_answer_correct"] == 0,
        "qa_missing_answer_fails": qa_missing_answer["aggregate"]["full_answer_correct"] == 0,
        "qa_high_confidence_wrong_answer_counted": qa_wrong_answer["aggregate"]["high_confidence_wrong"] == 5,
        "qa_missing_answer_labels_rejected": bool(_validate_manifest({
            "schema_version": 1, "cases": [dict(qa_case, accepted_answers=[])]
        })),
        "qa_full_answer_gain_comparable": qa_gain.get("statistical_threshold_met") is True,
    })
    report["self_test"] = {"scenarios": len(checks), "passed": sum(checks.values()),
                           "failed": sum(not value for value in checks.values()), "checks": checks,
                           "synthetic_only": True, "comparison_fixture": gain}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="Frozen candidate/query JSON manifest")
    parser.add_argument("--results", type=Path, help="JSONL result rows from independent model runs")
    parser.add_argument("--baseline-results", type=Path, help="JSONL baseline runs on the same manifest")
    parser.add_argument("--metric", choices=("top1_accuracy", "full_answer_accuracy", "mrr", "latency_ms"), default="top1_accuracy")
    parser.add_argument("--min-runs", type=int, default=MIN_INDEPENDENT_RUNS)
    parser.add_argument("--high-confidence", type=float, default=0.8)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        report = _self_test()
        if args.json:
            print(json.dumps(report, ensure_ascii=True, indent=2))
        else:
            t = report["self_test"]
            print(f"VLM SELECTION SCORECARD CONTRACT: {'PASS' if t['failed'] == 0 else 'FAIL'}, "
                  f"scenarios={t['scenarios']}, passed={t['passed']}, failed={t['failed']} "
                  "(synthetic only; not VLM accuracy)")
        return 0 if report["self_test"]["failed"] == 0 else 1

    if args.min_runs < MIN_INDEPENDENT_RUNS:
        parser.error(f"--min-runs must be at least {MIN_INDEPENDENT_RUNS} for model results")
    if not 0 <= args.high_confidence <= 1:
        parser.error("--high-confidence must be between 0 and 1")
    if not args.manifest or not args.results:
        parser.error("--manifest and --results are required unless --self-test is used")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in args.results.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = score(manifest, rows, min_runs=args.min_runs, high_confidence=args.high_confidence)
    if args.baseline_results:
        baseline_rows = [json.loads(line) for line in args.baseline_results.read_text(encoding="utf-8").splitlines() if line.strip()]
        baseline_report = score(manifest, baseline_rows, min_runs=args.min_runs,
                                high_confidence=args.high_confidence)
        report["statistical_comparison"] = compare_reports(baseline_report, report, metric=args.metric)
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        summary = report["aggregate"]
        print("VLM CANDIDATE SELECTION")
        print(f"cases={report['manifest_cases']} runs={report['result_runs']} "
              f"coverage_complete={report['coverage_complete']} errors={len(report['input_errors'])}")
        print(f"Top-1={summary['top1_correct']}/{summary['runs']} ({summary['top1_accuracy']:.1%}) "
              f"Hit@3={summary['hit_at_3']}/{summary['runs']} "
              f"Hit@5={summary['hit_at_5']}/{summary['runs']} MRR={summary['mrr']:.4f}")
        print(f"full-answer={summary['full_answer_correct']}/{summary['runs']} "
              f"QA-answer-given-location={summary['qa_answer_correct_given_location']}")
        print(f"high-confidence-wrong={summary['high_confidence_wrong']} "
              f"latency-p50/p95={summary['latency_ms_p50']}/{summary['latency_ms_p95']} ms "
              f"timeout-rate={summary['timeout_rate']:.1%}")
        if args.baseline_results:
            comparison = report["statistical_comparison"]
            print(f"statistical comparison: comparable={comparison['comparable']} "
                  f"threshold_met={comparison.get('statistical_threshold_met', False)} "
                  f"reasons={comparison['reasons']}")
    return 1 if (report["input_errors"] or not report["coverage_complete"]
                 or (args.baseline_results and not report["statistical_comparison"]["comparable"])) else 0


if __name__ == "__main__":
    raise SystemExit(main())
