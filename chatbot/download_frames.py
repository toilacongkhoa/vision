import httpx
import requests
from PIL import Image
import io
import os

frames = [20935, 21042, 21101, 21220, 21270, 21368, 21503]
out_dir = r"C:\Users\ADMIN\.gemini\antigravity-cli\brain\80c16579-8c3b-4d78-8ba5-7b6ddc9130f9"

for f in frames:
    res = requests.get('http://127.0.0.1:8000/api/v1/search/context', params={'video_id': 'L21_V018', 'frame_idx': f, 'limit': 1})
    data = res.json()
    if data['results']:
        r2_url = data['results'][0].get('r2_url') or data['results'][0].get('image_path')
        print(f, r2_url)
        img_data = httpx.get(r2_url).content
        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        img.save(os.path.join(out_dir, f"frame_{f}.jpg"))
        print(f"Saved frame_{f}.jpg")
