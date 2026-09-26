import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from src.sqlite_engine import SQLiteSearchEngine


class AsrPreviewTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db_path = Path(handle.name)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE asr_segments (
                    id INTEGER PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    segment_index INTEGER NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    text TEXT,
                    source_type TEXT
                )
                """
            )
            conn.executemany(
                "INSERT INTO asr_segments VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (1, "M01_V001", 0, 0.0, 4.0, "đoạn đầu", "subtitle"),
                    (2, "M01_V001", 1, 5.0, 9.0, "đoạn giữa", "subtitle"),
                    (3, "M01_V001", 2, 10.0, 14.0, "đoạn cuối", "subtitle"),
                    (4, "M01_V002", 0, 5.0, 9.0, "video khác", "subtitle"),
                ],
            )
            conn.commit()
        finally:
            conn.close()
        self.engine = SQLiteSearchEngine.__new__(SQLiteSearchEngine)
        self.engine.db_path = self.db_path
        self.engine._db_local = threading.local()

    def tearDown(self):
        connection = getattr(self.engine._db_local, "connection", None)
        if connection is not None:
            connection.close()
        self.db_path.unlink(missing_ok=True)

    def test_returns_only_overlapping_segments_for_video(self):
        segments = self.engine.get_asr_segments("M01_V001", 3.0, 10.0, 100)
        self.assertEqual([row["segment_index"] for row in segments], [0, 1, 2])
        self.assertEqual(segments[1]["text"], "đoạn giữa")

    def test_accepts_reversed_interval_and_enforces_limit(self):
        segments = self.engine.get_asr_segments("M01_V001", 12.0, 2.0, 1)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["segment_index"], 0)

    def test_frontend_exposes_asr_panel_and_speech_inputs(self):
        html = (Path(__file__).resolve().parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="previewAsrPanel"', html)
        self.assertIn("loadPreviewAsr(videoId, currentPts)", html)
        self.assertIn("window.SpeechRecognition || window.webkitSpeechRecognition", html)
        for target in ("queryInput", "aiChatInput"):
            self.assertIn(target, html)


if __name__ == "__main__":
    unittest.main()
