import sqlite3
import json

conn = sqlite3.connect(r'C:\Users\ADMIN\error_on_line_23\vision\video_index_v2.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT vector_id, video_id, frame_idx, pts_time, asr_text, ocr_text, raw_json 
    FROM keyframes 
    WHERE video_id = 'L21_V018' AND frame_idx BETWEEN 20000 AND 22500
    ORDER BY frame_idx
""")

rows = cursor.fetchall()
print(f"Total keyframes found: {len(rows)}")
for r in rows:
    raw = json.loads(r[6]) if r[6] else {}
    img_path = raw.get('image_path') or raw.get('r2_url') or raw.get('url')
    print(f"frame_idx: {r[2]}, pts: {r[3]}, ocr: {r[5]}, img: {img_path}")
