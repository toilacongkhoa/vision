import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.traffic_search import TrafficSearchEngine, canonical_video_id


class TrafficSearchTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.path = Path(handle.name)
        connection = sqlite3.connect(self.path)
        try:
            connection.executescript(
                """
                CREATE TABLE videos (video_key TEXT PRIMARY KEY, filename TEXT, source_path TEXT,
                    source_fps REAL, effective_fps REAL, width INTEGER, height INTEGER,
                    duration REAL, worker_id INTEGER, processed_at TEXT);
                CREATE TABLE tracks (track_uid TEXT PRIMARY KEY, video_key TEXT, local_track_id INTEGER,
                    class TEXT, class_conf REAL, start_time REAL, end_time REAL, duration REAL,
                    observed_frames INTEGER, color TEXT, color_conf REAL, direction TEXT,
                    motion_state TEXT, mean_speed_norm REAL, median_speed_norm REAL,
                    p95_speed_norm REAL, stop_ratio REAL, moving_ratio REAL, straightness REAL,
                    start_x REAL, start_y REAL, end_x REAL, end_y REAL);
                CREATE TABLE events (event_id INTEGER PRIMARY KEY, video_key TEXT, track_uid TEXT,
                    related_track_uid TEXT, event_type TEXT, start_time REAL, end_time REAL,
                    confidence REAL, severity REAL, metadata_json TEXT);
                """
            )
            connection.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?,?,?,?)", (
                "N001-N010__N001-V001", "sample.mov", "sample.mov", 25.0, 5.0,
                1920, 1080, 100.0, 0, "now"))
            connection.execute("INSERT INTO tracks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                "N001-N010__N001-V001:1", "N001-N010__N001-V001", 1, "car", 0.95,
                5.0, 9.0, 4.0, 20, "red", 0.9, "right", "mostly_moving",
                1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0, 0, 1, 1))
            connection.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)", (
                1, "N001-N010__N001-V001", "N001-N010__N001-V001:1", None,
                "left_turn_candidate", 6.0, 8.0, 0.8, 0.4, "{}"))
            connection.commit()
        finally:
            connection.close()
        self.engine = TrafficSearchEngine(self.path)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_canonical_video_id(self):
        self.assertEqual(canonical_video_id("N001-N010__N001-V001"), "N001_V001")

    def test_track_filters_are_combined(self):
        rows = self.engine.search(camera_id="N001", object_class="car", color="red", limit=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["video_id"], "N001_V001")
        self.assertEqual(rows[0]["preview_time"], 7.0)

    def test_event_search_returns_event_and_track_metadata(self):
        rows = self.engine.search(event_type="left_turn_candidate", min_severity=0.3, limit=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["object_class"], "car")
        self.assertEqual(rows[0]["event_type"], "left_turn_candidate")

    def test_ai_chat_traffic_tool_and_grid_handoff_are_present(self):
        root = Path(__file__).resolve().parents[1]
        mcp_source = (root / "mcp_server.py").read_text(encoding="utf-8")
        frontend = (root / "frontend" / "index.html").read_text(encoding="utf-8")
        instructions = (root / "src" / "agy_session.py").read_text(encoding="utf-8")
        self.assertIn("async def search_traffic_camera", mcp_source)
        self.assertIn("[TRAFFIC_CAMERA_RESULTS]", mcp_source)
        self.assertIn("rawAssistantText.includes('[TRAFFIC_CAMERA_RESULTS]')", frontend)
        self.assertIn("search_traffic_camera", instructions)


if __name__ == "__main__":
    unittest.main()
