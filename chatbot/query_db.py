import sqlite3

conn = sqlite3.connect(r'C:\Users\ADMIN\error_on_line_23\vision\video_index_v2.db')
cursor = conn.cursor()

queries = [
    "SELECT video_id, frame_idx, pts_time, asr_text, ocr_text FROM keyframes WHERE asr_text LIKE '%sưu tầm%' AND (asr_text LIKE '%bà%' OR asr_text LIKE '%đồ chơi%') LIMIT 20",
    "SELECT video_id, frame_idx, pts_time, asr_text, ocr_text FROM keyframes WHERE asr_text LIKE '%bà%' AND asr_text LIKE '%đồ chơi%' LIMIT 20",
    "SELECT video_id, frame_idx, pts_time, asr_text, ocr_text FROM keyframes WHERE asr_text LIKE '%đam mê%' AND asr_text LIKE '%bà%' LIMIT 20",
    "SELECT video_id, frame_idx, pts_time, asr_text, ocr_text FROM keyframes WHERE asr_text LIKE '%truyền cảm hứng%' LIMIT 20",
    "SELECT video_id, frame_idx, pts_time, asr_text, ocr_text FROM keyframes WHERE asr_text LIKE '%sưu tầm%' AND asr_text LIKE '%game%' LIMIT 20",
    "SELECT video_id, frame_idx, pts_time, asr_text, ocr_text FROM keyframes WHERE asr_text LIKE '%sưu tập%' AND asr_text LIKE '%game%' LIMIT 20",
    "SELECT video_id, frame_idx, pts_time, asr_text, ocr_text FROM keyframes WHERE asr_text LIKE '%sưu tầm%' LIMIT 10",
]

for i, q in enumerate(queries):
    print(f"=== Query {i} ===")
    cursor.execute(q)
    rows = cursor.fetchall()
    for r in rows:
        print(f"[{r[0]}, {r[1]}, pts={r[2]}] ASR: {r[3][:100]}... | OCR: {r[4][:100] if r[4] else ''}")
