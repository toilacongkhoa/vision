import json
import unittest

from src.sqlite_engine import SQLiteSearchEngine, build_r2_url


BASE = "https://pub-63867f61a3cb4f34a8b442399021fbbd.r2.dev"


class R2PathTests(unittest.TestCase):
    def test_legacy_object_path_is_preserved(self):
        rec = {
            "video_id": "L26_V001",
            "frame_number": 1,
            "image": {"rel_path": "Keyframes_L26_a/keyframes/L26_V001/001.jpg"},
        }
        self.assertEqual(
            build_r2_url(rec),
            f"{BASE}/Keyframes_L26_a/keyframes/L26_V001/001.webp",
        )

    def test_colab_string_path_is_normalized(self):
        rec = {
            "video_id": "L27_V005",
            "frame_number": 1,
            "image": "/content/drive/MyDrive/data/Keyframes_L27/keyframes/L27_V005/001.jpg",
        }
        self.assertEqual(
            build_r2_url(rec),
            f"{BASE}/Keyframes_L27/keyframes/L27_V005/001.webp",
        )

    def test_missing_l27_path_is_inferred(self):
        rec = {"video_id": "L27_V006", "frame_number": 1, "image": {"file_id": "drive"}}
        self.assertEqual(
            build_r2_url(rec),
            f"{BASE}/Keyframes_L27/keyframes/L27_V006/001.webp",
        )

    def test_v5_group_paths(self):
        cases = {
            "M01_V001": "Keyframes_M01/keyframes/M01_V001/001.webp",
            "N010_V001": "Keyframes_N001-N010/keyframes/N010-V001/001.webp",
            "N011_V001": "Keyframes_N011-N020/keyframes/N011-V001/001.webp",
            "N100_V001": "Keyframes_N091-N100/keyframes/N100-V001/001.webp",
            "S01_V001": "Keyframes_S01/keyframes/S01-V001/0001.webp",
        }
        for video_id, expected in cases.items():
            with self.subTest(video_id=video_id):
                rec = {"video_id": video_id, "keyframe": {"id": 1}}
                self.assertEqual(build_r2_url(rec), f"{BASE}/{expected}")

    def test_v5_result_metadata(self):
        rec = {
            "schema": "vision_v5_keyframe_v1",
            "video_id": "N001_V001",
            "vector": {"global_id": 271998},
            "keyframe": {"id": 1, "frame_idx": 50, "pts_time": 2.0},
        }
        engine = SQLiteSearchEngine.__new__(SQLiteSearchEngine)
        result = engine._format_result(json.dumps(rec), 0.75)
        self.assertEqual(result["vector_id"], 271998)
        self.assertEqual(result["frame_idx"], 50)
        self.assertEqual(result["pts_time"], 2.0)
        self.assertTrue(result["r2_url"].endswith("/N001-V001/001.webp"))


if __name__ == "__main__":
    unittest.main()
