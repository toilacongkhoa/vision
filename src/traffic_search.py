"""Read-only structured search for the traffic-camera analytics database."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List, Optional


def canonical_video_id(video_key: str) -> str:
    value = str(video_key or "").split("__")[-1]
    return value.replace("-", "_")


class TrafficSearchEngine:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        return connection

    def available(self) -> bool:
        return self.db_path.is_file()

    def filters(self) -> Dict[str, List[str]]:
        with closing(self._connect()) as connection:
            cameras = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT DISTINCT substr(
                        substr(video_key, instr(video_key, '__') + 2),
                        1,
                        instr(substr(video_key, instr(video_key, '__') + 2), '-') - 1
                    ) AS camera_id
                    FROM videos
                    WHERE instr(video_key, '__') > 0
                    ORDER BY camera_id
                    """
                )
                if row[0]
            ]

            def distinct(column: str) -> List[str]:
                return [
                    row[0]
                    for row in connection.execute(
                        f"SELECT DISTINCT {column} FROM tracks WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
                    )
                ]

            event_types = [
                row[0]
                for row in connection.execute(
                    "SELECT event_type FROM events GROUP BY event_type ORDER BY COUNT(*) DESC, event_type"
                )
            ]
            return {
                "cameras": cameras,
                "classes": distinct("class"),
                "colors": distinct("color"),
                "directions": distinct("direction"),
                "motion_states": distinct("motion_state"),
                "event_types": event_types,
            }

    @staticmethod
    def _video_clauses(camera_id: Optional[str], video_id: Optional[str], alias: str) -> tuple[List[str], List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if camera_id:
            normalized = camera_id.strip().upper().replace("-", "_")
            clauses.append(f"{alias}.video_key LIKE ?")
            params.append(f"%__{normalized}-%")
        if video_id:
            normalized = video_id.strip().upper().replace("_", "-")
            clauses.append(f"{alias}.video_key LIKE ?")
            params.append(f"%__{normalized}")
        return clauses, params

    def search(
        self,
        *,
        camera_id: Optional[str] = None,
        video_id: Optional[str] = None,
        object_class: Optional[str] = None,
        color: Optional[str] = None,
        direction: Optional[str] = None,
        motion_state: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        min_confidence: float = 0.0,
        min_severity: float = 0.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        track_filters = {
            "class": object_class,
            "color": color,
            "direction": direction,
            "motion_state": motion_state,
        }
        clauses, params = self._video_clauses(camera_id, video_id, "v")
        for column, value in track_filters.items():
            if value:
                clauses.append(f"t.{column} = ?")
                params.append(value)

        if event_type:
            clauses.append("e.event_type = ?")
            params.append(event_type)
            clauses.append("COALESCE(e.confidence, 0) >= ?")
            params.append(float(min_confidence))
            clauses.append("COALESCE(e.severity, 0) >= ?")
            params.append(float(min_severity))
            if start_time is not None:
                clauses.append("COALESCE(e.end_time, e.start_time, 0) >= ?")
                params.append(float(start_time))
            if end_time is not None:
                clauses.append("COALESCE(e.start_time, 0) <= ?")
                params.append(float(end_time))
            sql = f"""
                SELECT e.event_id, e.video_key, e.track_uid, e.related_track_uid,
                       e.event_type, e.start_time, e.end_time, e.confidence,
                       e.severity, e.metadata_json, t.class AS object_class,
                       t.color, t.direction, t.motion_state, t.class_conf,
                       v.source_fps, v.duration, v.width, v.height
                FROM events e
                JOIN videos v ON v.video_key = e.video_key
                LEFT JOIN tracks t ON t.track_uid = e.track_uid
                WHERE {' AND '.join(clauses) if clauses else '1=1'}
                ORDER BY COALESCE(e.severity, 0) DESC,
                         COALESCE(e.confidence, 0) DESC,
                         e.video_key, e.start_time
                LIMIT ?
            """
        else:
            clauses.append("COALESCE(t.class_conf, 0) >= ?")
            params.append(float(min_confidence))
            if start_time is not None:
                clauses.append("COALESCE(t.end_time, t.start_time, 0) >= ?")
                params.append(float(start_time))
            if end_time is not None:
                clauses.append("COALESCE(t.start_time, 0) <= ?")
                params.append(float(end_time))
            sql = f"""
                SELECT NULL AS event_id, t.video_key, t.track_uid,
                       NULL AS related_track_uid, NULL AS event_type,
                       t.start_time, t.end_time, t.class_conf AS confidence,
                       NULL AS severity, NULL AS metadata_json,
                       t.class AS object_class, t.color, t.direction,
                       t.motion_state, t.class_conf, v.source_fps, v.duration,
                       v.width, v.height
                FROM tracks t
                JOIN videos v ON v.video_key = t.video_key
                WHERE {' AND '.join(clauses) if clauses else '1=1'}
                ORDER BY COALESCE(t.class_conf, 0) DESC,
                         t.duration DESC, t.video_key, t.start_time
                LIMIT ?
            """

        params.append(limit)
        with closing(self._connect()) as connection:
            rows = [dict(row) for row in connection.execute(sql, params)]
        for row in rows:
            row["video_id"] = canonical_video_id(row["video_key"])
            start = float(row.get("start_time") or 0.0)
            end = float(row.get("end_time") if row.get("end_time") is not None else start)
            row["preview_time"] = max(0.0, (start + end) / 2.0)
        return rows
