"""Build and validate the DRES v2 submission bodies used at AI Challenge 2026.

This module only serializes local results. It never logs in or sends requests;
server acceptance still needs confirmation against the organizer's evaluation.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Mapping, Sequence, Set


class SubmissionError(ValueError):
    """Raised when a local answer cannot safely be serialized for DRES."""


_VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".mpeg", ".mpg")


def _video_id(value: Any) -> str:
    if not isinstance(value, str):
        raise SubmissionError("video_id must be a string without a file extension")
    result = value.strip()
    if not result or "/" in result or "\\" in result:
        raise SubmissionError("video_id must be a non-empty item name, not a path")
    if result.lower().endswith(_VIDEO_EXTENSIONS):
        raise SubmissionError("DRES mediaItemName must not include a video extension")
    return result


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise SubmissionError(f"{name} must be a non-negative integer")
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise SubmissionError(f"{name} must be a non-negative integer") from exc
    if number < 0 or str(value).strip() not in (str(number), f"+{number}"):
        raise SubmissionError(f"{name} must be a non-negative integer")
    return number


def pts_time_seconds_to_ms(pts_time: Any) -> int:
    """Convert a source PTS timestamp in seconds to the nearest millisecond."""
    if isinstance(pts_time, bool) or pts_time is None:
        raise SubmissionError("pts_time must be a finite, non-negative number of seconds")
    try:
        seconds = Decimal(str(pts_time))
    except (InvalidOperation, ValueError) as exc:
        raise SubmissionError("pts_time must be a finite, non-negative number of seconds") from exc
    if not seconds.is_finite() or seconds < 0:
        raise SubmissionError("pts_time must be a finite, non-negative number of seconds")
    return int((seconds * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _single_answer_payload(answer: Mapping[str, Any]) -> Dict[str, Any]:
    return {"answerSets": [{"answers": [dict(answer)]}]}


def build_kis_payload(video_id: str, pts_time: Any) -> Dict[str, Any]:
    """Build the Textual/Video KIS body from a video ID and frame PTS seconds.

    The PDF defines a point location but provides both DRES time bounds. This
    encodes the located frame as a point (start == end); the actual evaluation
    server's interpretation must be verified when organizer access is available.
    """
    name = _video_id(video_id)
    time_ms = str(pts_time_seconds_to_ms(pts_time))
    return _single_answer_payload({"mediaItemName": name, "start": time_ms, "end": time_ms})


def build_qa_payload(video_id: str, pts_time: Any, answer: str) -> Dict[str, Any]:
    name = _video_id(video_id)
    if not isinstance(answer, str) or not answer.strip():
        raise SubmissionError("Q&A answer must be a non-empty string")
    time_ms = pts_time_seconds_to_ms(pts_time)
    text = f"QA-{answer.strip()}-{name}-{time_ms}"
    return _single_answer_payload({"text": text})


def build_trake_payload(video_id: str, frame_ids: Sequence[Any]) -> Dict[str, Any]:
    name = _video_id(video_id)
    if isinstance(frame_ids, (str, bytes)) or not isinstance(frame_ids, Sequence) or not frame_ids:
        raise SubmissionError("TRAKE requires a non-empty sequence of frame IDs")
    ids = [_nonnegative_int(frame_id, "frame_id") for frame_id in frame_ids]
    if any(later <= earlier for earlier, later in zip(ids, ids[1:])):
        raise SubmissionError("TRAKE frame IDs must be strictly increasing")
    return _single_answer_payload({"text": f"TR-{name}-" + ",".join(map(str, ids))})


def validate_payload(payload: Any, query_type: str) -> None:
    """Validate the payload envelope and task-specific fields before transport."""
    if not isinstance(query_type, str) or not query_type.strip():
        raise SubmissionError("query_type must be a non-empty string")
    if not isinstance(payload, dict) or set(payload) != {"answerSets"}:
        raise SubmissionError("payload must contain only answerSets")
    answer_sets = payload["answerSets"]
    if not isinstance(answer_sets, list) or len(answer_sets) != 1:
        raise SubmissionError("payload must contain exactly one answerSet")
    answer_set = answer_sets[0]
    if not isinstance(answer_set, dict) or set(answer_set) != {"answers"}:
        raise SubmissionError("answerSet must contain only answers")
    answers = answer_set["answers"]
    if not isinstance(answers, list) or len(answers) != 1 or not isinstance(answers[0], dict):
        raise SubmissionError("payload must contain exactly one answer")
    answer = answers[0]
    kind = query_type.strip().upper().replace(" ", "_")
    if kind in {"KIS", "TEXTUAL_KIS", "VIDEO_KIS"}:
        if set(answer) != {"mediaItemName", "start", "end"}:
            raise SubmissionError("KIS answer requires mediaItemName, start, and end")
        _video_id(answer["mediaItemName"])
        if not isinstance(answer["start"], str) or not isinstance(answer["end"], str):
            raise SubmissionError("KIS start and end must be millisecond strings")
        start = _nonnegative_int(answer["start"], "start")
        end = _nonnegative_int(answer["end"], "end")
        if end < start:
            raise SubmissionError("end must be greater than or equal to start")
        return
    if kind in {"QA", "Q&A", "Q_A"}:
        if set(answer) != {"text"} or not isinstance(answer["text"], str) or not answer["text"].startswith("QA-") or len(answer["text"]) <= 3:
            raise SubmissionError("Q&A answer requires a QA-prefixed text field")
        return
    if kind == "TRAKE":
        if set(answer) != {"text"} or not isinstance(answer["text"], str) or not answer["text"].startswith("TR-") or len(answer["text"]) <= 3:
            raise SubmissionError("TRAKE answer requires a TR-prefixed text field")
        serialized_video_id, separator, serialized_frames = answer["text"][3:].rpartition("-")
        if not separator or not serialized_frames:
            raise SubmissionError("TRAKE text must contain a video ID and frame IDs")
        _video_id(serialized_video_id)
        frame_ids = serialized_frames.split(",")
        if any(not frame_id for frame_id in frame_ids):
            raise SubmissionError("TRAKE text contains an empty frame ID")
        parsed_ids = [_nonnegative_int(frame_id, "frame_id") for frame_id in frame_ids]
        if any(later <= earlier for earlier, later in zip(parsed_ids, parsed_ids[1:])):
            raise SubmissionError("TRAKE frame IDs must be strictly increasing")
        return
    raise SubmissionError(f"unsupported query type: {query_type!r}")


@dataclass
class SubmissionDeduper:
    """Track payload fingerprints without blocking operator-requested retries."""

    _seen: Dict[str, Set[str]] = field(default_factory=dict)

    @staticmethod
    def fingerprint(payload: Mapping[str, Any]) -> str:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def record(self, query_id: str, payload: Mapping[str, Any]) -> None:
        key = str(query_id).strip()
        if not key:
            raise SubmissionError("query_id must be non-empty")
        digest = self.fingerprint(payload)
        seen = self._seen.setdefault(key, set())
        seen.add(digest)

    def contains(self, query_id: str, payload: Mapping[str, Any]) -> bool:
        """Return whether this exact payload was already recorded for a query."""
        key = str(query_id).strip()
        if not key:
            raise SubmissionError("query_id must be non-empty")
        return self.fingerprint(payload) in self._seen.get(key, set())


def score_full_answer(elapsed_seconds: Any, task_seconds: Any, wrong_submissions: Any) -> float:
    """Calculate the full-correct score specified in the organizer PDF."""
    elapsed = _finite_nonnegative(elapsed_seconds, "elapsed_seconds")
    duration = _finite_nonnegative(task_seconds, "task_seconds")
    wrong = _nonnegative_int(wrong_submissions, "wrong_submissions")
    if duration <= 0 or elapsed > duration:
        raise SubmissionError("task_seconds must be positive and elapsed_seconds within the deadline")
    return max(0.0, 50.0 + 50.0 * (1.0 - elapsed / duration) - 10.0 * wrong)


def score_partial_trake(
    elapsed_seconds: Any,
    task_seconds: Any,
    wrong_submissions: Any,
    correct_frames: Any,
    total_frames: Any,
) -> float:
    """Calculate a partial TRAKE score for a 50%-to-under-100% result."""
    correct = _nonnegative_int(correct_frames, "correct_frames")
    total = _nonnegative_int(total_frames, "total_frames")
    if total <= 0 or correct * 2 < total or correct >= total:
        raise SubmissionError("partial TRAKE score requires 50% to under 100% correct frames")
    return score_full_answer(elapsed_seconds, task_seconds, wrong_submissions) / 2.0


def compare_submission_timing(
    *,
    early_seconds: Any,
    wait_seconds: Any,
    task_seconds: Any,
    wrong_submissions_before: Any,
    p_correct_early: Any,
    p_correct_wait: Any,
    p_recover_after_early_wrong: Any,
) -> Dict[str, Any]:
    """Compare one early attempt (with a possible later correction) to waiting.

    Probabilities are operator-provided assumptions, not learned estimates. The
    model assigns zero points when no correct answer is submitted by the
    deadline. It assumes the early strategy submits once now, and only after an
    incorrect early answer may submit one corrected answer at ``wait_seconds``.
    The wait strategy submits once at ``wait_seconds`` and therefore incurs no
    new wrong-answer penalty before that attempt.
    """
    early = _finite_nonnegative(early_seconds, "early_seconds")
    later = _finite_nonnegative(wait_seconds, "wait_seconds")
    duration = _finite_nonnegative(task_seconds, "task_seconds")
    prior_wrong = _nonnegative_int(wrong_submissions_before, "wrong_submissions_before")
    p_early = _probability(p_correct_early, "p_correct_early")
    p_wait = _probability(p_correct_wait, "p_correct_wait")
    p_recover = _probability(p_recover_after_early_wrong, "p_recover_after_early_wrong")
    if duration <= 0 or early > later or later > duration:
        raise SubmissionError("require 0 <= early_seconds <= wait_seconds <= task_seconds")

    early_score = score_full_answer(early, duration, prior_wrong)
    late_score = score_full_answer(later, duration, prior_wrong)
    corrected_late_score = score_full_answer(later, duration, prior_wrong + 1)
    early_expected = p_early * early_score + (1.0 - p_early) * p_recover * corrected_late_score
    wait_expected = p_wait * late_score
    delta = early_expected - wait_expected
    denominator = early_score - p_recover * corrected_late_score
    threshold = None if denominator == 0 else (
        p_wait * late_score - p_recover * corrected_late_score
    ) / denominator
    return {
        "early_expected_score": round(early_expected, 6),
        "wait_expected_score": round(wait_expected, 6),
        "early_minus_wait": round(delta, 6),
        "preferred_under_assumptions": "early" if delta > 1e-9 else "wait" if delta < -1e-9 else "tie",
        "early_correct_probability_break_even": None if threshold is None else round(threshold, 6),
        "assumptions": {
            "incorrect_final_answer_score": 0,
            "early_incorrect_attempt_penalty_applies_to_correction": True,
            "probabilities_are_user_supplied": True,
        },
    }


def _probability(value: Any, name: str) -> float:
    probability = _finite_nonnegative(value, name)
    if probability > 1:
        raise SubmissionError(f"{name} must be between 0 and 1")
    return probability


def _finite_nonnegative(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise SubmissionError(f"{name} must be a finite non-negative number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise SubmissionError(f"{name} must be a finite non-negative number") from exc
    if not math.isfinite(number) or number < 0:
        raise SubmissionError(f"{name} must be a finite non-negative number")
    return number
