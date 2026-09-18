# PROJECT CONTEXT — Video Retrieval System V3

## Mục tiêu

Hệ thống tìm kiếm keyframe/video đa phương thức cho AI Challenge. Người dùng tìm frame bằng mô tả tự nhiên, ảnh, OCR, ASR hoặc chuỗi sự kiện; xem metadata/bounding box/video và xuất submission KIS, QA hoặc TRAKE.

## Tech stack

- Python 3.10+ theo README; FastAPI >=0.100, Uvicorn >=0.22, Pydantic >=2.0. `requirements.txt` chỉ đặt lower bound, không có lockfile.
- PyTorch >=2.0, OpenCLIP >=2.20 (ViT-B-32/openai), FAISS CPU >=1.7.4, NumPy >=1.24, Pillow >=9.0.
- SQLite cho index metadata runtime; Supabase được gọi bằng REST/`urllib` qua các endpoint riêng (package `supabase` có khai báo nhưng không được import).
- Google Drive REST/CDN cho ảnh và video.
- Frontend một file HTML với TailwindCSS CDN không pin version, JavaScript inline và JSZip 3.10.1.

## Kiến trúc chính

~~~text
Browser / frontend/index.html
        |
        v
FastAPI: src/main.py
        |
        +-- SQLiteSearchEngine: CLIP + FAISS + SQLite
        |       +-- all_vectors.npy
        |       +-- video_index_v2.db
        |       \`-- keyframes.raw_json
        |
        +-- SupabaseService -> các endpoint Supabase REST độc lập
        +-- Drive proxy      -> Google Drive + LRU cache
        +-- JSON caches      -> video_drive_metadata.json / video_fps_map.json
        \`-- frontend result cards, preview, bbox, submission ZIP
~~~

### Luồng tìm kiếm

1. Frontend gọi `/api/v1/search`, `/api/v1/search/image` hoặc endpoint context/interval/similar.
2. Semantic text search thử dịch query sang tiếng Anh bằng Google Translate (nếu lỗi thì giữ nguyên), tách các vế theo dấu phẩy, chấm phẩy hoặc `and`, encode từng vế bằng OpenCLIP rồi lấy trung bình khi có nhiều vế.
3. FAISS IndexFlatIP tìm vector gần nhất; NumPy dot product là fallback.
4. Vector ID được tra trong video_index_v2.db, lấy raw_json và format thành result.
5. Frontend hiển thị ảnh/score/timestamp, mở Drive video hoặc thêm frame vào submission.

OCR/ASR runtime tách query thành token, dùng SQL `LIKE %token%` trên cột tương ứng và xếp hạng theo số token khớp; đây không phải BM25 hay fuzzy edit-distance. Temporal search chỉ dùng hai vế đầu, lấy tối đa 200 kết quả semantic mỗi vế và ghép cùng video khi frame sau cách frame trước tối đa 900 frame; `video_id` trong request không được áp dụng cho nhánh temporal.

Runtime dùng src/sqlite_engine.py và không dùng Supabase làm fallback cho kết quả search. src/search_engine.py là engine legacy/alternate, có cache metadata, object/OCR/ASR index, Supabase/SQLite fallback và code BM25, nhưng không được main.py sử dụng; phần build BM25 đang bị comment/disable.

## API chính

- GET / — frontend.
- GET /api/v1/health — trạng thái DB/vector/Supabase theo config legacy; số lượng keyframe hiện không lấy từ DB runtime V2.
- POST /api/v1/search — semantic, OCR, ASR; query chứa `->` dùng temporal search.
- POST /api/v1/search/image — tìm bằng ảnh upload.
- POST /api/v1/search/similar — tìm frame tương tự từ vector ID.
- GET /api/v1/search/context — frame kế tiếp hoặc frame xung quanh.
- GET /api/v1/search/interval — frame trong khoảng timestamp.
- GET /api/v1/video/{video_id}/convert_time — timestamp → frame index.
- GET /api/v1/video/{video_id} — Google Drive video metadata.
- GET /api/v1/drive/proxy/{file_id} — proxy/cache file Google Drive.
- /api/v1/supabase/* — truy vấn video/frame từ Supabase.

## Cấu trúc quan trọng

~~~text
vision/
├── frontend/index.html          # UI, search, preview, submission builder
├── src/main.py                  # FastAPI app và routes
├── src/config.py                # paths, model, host/port, CORS
├── src/sqlite_engine.py         # engine runtime: CLIP/FAISS/SQLite
├── src/search_engine.py         # engine legacy, BM25/object/OCR/ASR
├── src/db.py                    # DB manager cho indexer/schema cũ
├── src/supabase_service.py      # Supabase REST client
├── src/indexer.py               # local dataset → SQLite/vector/audit
├── src/gdrive_indexer.py        # Google Drive → local index/vector
├── src/gdrive_mapper.py         # Drive path → file ID/CDN URL
├── src/gemini_agent.py          # query expansion/rerank, chưa nối runtime
├── src/upload_supabase.py       # upload metadata lên Supabase
├── scripts/build_sqlite_cache.py # frame_map JSON → DB runtime V2; hiện hard-code path G:
├── scripts/                     # import OCR/ASR/object vào frame map
├── all_vectors.npy              # 177321 x 512 CLIP vectors
├── frame_map_supabase.json      # 177321 frame metadata; input migration nhưng lệch DB hiện tại
├── video_index_v2.db            # SQLite runtime, bảng keyframes
├── video_drive_metadata.json    # video → Drive IDs
└── video_fps_map.json           # video → FPS
~~~

Dữ liệu hiện tại: all_vectors.npy có shape 177321 x 512 float32; video_index_v2.db có 177321 rows, 873 video và vector_id liên tục 0..177320; frame_map_supabase.json có 177321 entry; metadata video/FPS đều có 873 video. DB V2 có ASR text ở 159256 row, OCR text ở 69160 row, OCR detections ở 68244 row và object text/detections ở 174585 row.

## Tính năng hiện có

- Semantic text search, dịch query, lọc theo video.
- Image similarity search và similar-by-vector.
- OCR/ASR token-substring search bằng SQL LIKE.
- Temporal search hai sự kiện bằng `query1 -> query2`.
- Context/interval search và timestamp → frame index.
- Ba endpoint lookup Supabase độc lập; Google Drive proxy/cache và video iframe.
- Frontend result grid; preview prev/next bằng nút, bàn phím hoặc swipe; object/OCR bounding boxes.
- Submission Builder KIS/QA/TRAKE, lưu localStorage và xuất submission.zip.
- Legacy local/cloud indexer và utility import OCR, ASR, object vào frame map.

## Vấn đề ảnh hưởng việc phát triển tiếp

- DB không thống nhất: config.DB_PATH/IndexDatabase hướng tới video_index.db với schema cũ, còn SQLiteSearchEngine dùng `DATA_ROOT.parent/video_index_v2.db` với raw_json. Khi import app, IndexDatabase có thể tự tạo DB legacy rỗng; health check đếm DB này rồi thay 0 bằng hằng 173605, nên không phản ánh 177321 row runtime.
- DATA_ROOT mặc định là BASE_DIR/data nhưng dữ liệu hiện đặt ở root; SQLiteSearchEngine lại suy DB V2 từ parent của DATA_ROOT. `video_drive_metadata.json` còn được mở theo current working directory thay vì BASE_DIR.
- requirements.txt thiếu rank-bm25 dù search_engine.py import package này; BM25 hiện bị disable.
- gemini_agent.py dùng `google.genai`/package `google-genai` nhưng requirements chỉ có `google-generativeai`; Gemini chưa import được trong môi trường theo requirements và chưa nối vào API.
- UI gọi ASR là BM25/Exact Text nhưng runtime chỉ dùng token-substring SQL LIKE; object search chưa có route. Frontend còn gửi `enable_rerank` nhưng SearchRequest không khai báo và runtime không rerank.
- Temporal search bỏ qua video filter, chỉ xử lý hai vế đầu nếu query có nhiều dấu `->`, và trả frame của sự kiện đầu kèm mô tả sự kiện sau thay vì cả cặp.
- OpenCLIP/vector/FAISS load ngay khi import app; vector 363 MB được copy/normalize trong RAM rồi lại add vào FAISS, startup nặng và model weights có thể tải lần đầu.
- Secrets còn hard-code, TLS verification bị tắt ở nhiều module, CORS mở mặc định và chưa có auth/rate limit.
- Không có test suite/CI; `.gitignore` còn ignore `test_*.py`.
- Nhãn version không thống nhất: README/context gọi V3, frontend hiển thị 2.0 và FastAPI khai báo 2.1.0.
- Drive proxy giữ tối đa 1000 file dưới dạng bytes trong LRU cache nhưng không có giới hạn tổng dung lượng.
- `frame_map_supabase.json` không đồng bộ với `video_index_v2.db`: JSON hiện có ASR text nhưng không có OCR text/detections hay object detections, trong khi `raw_json` của DB có các trường này. Rebuild V2 từ JSON hiện tại sẽ làm mất dữ liệu OCR/bounding box đang phục vụ UI.
- `src.indexer` và `src.gdrive_indexer` xóa dữ liệu trong DB legacy rồi ghi đè all_vectors.npy, nhưng không tạo schema V2 mà runtime đọc. `scripts/build_sqlite_cache.py` mới tạo V2 nhưng hard-code cả input/output ở `G:/Desktop/web_research` và xóa DB đích trước khi build; các importer cũng ghi đè toàn bộ frame_map JSON.

## Chạy local

~~~powershell
./.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python -m src.main
~~~

Hoặc:

~~~powershell
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
~~~

- UI: http://localhost:8000/
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

Để search runtime hoạt động, cần đặt `all_vectors.npy`, `video_index_v2.db`, `video_drive_metadata.json` và `video_fps_map.json` ở project root; `.env` dùng cho Supabase. `frame_map_supabase.json` cần cho pipeline/importer nhưng SQLiteSearchEngine không đọc trực tiếp ở runtime; không dùng file JSON hiện tại để rebuild V2 trước khi đồng bộ lại OCR/object detections từ DB hoặc nguồn gốc.

Indexer local hiện là pipeline legacy, không thay thế được DB runtime V2:

~~~powershell
python -m src.indexer --data_root <DATASET_ROOT>
~~~

Lệnh trên xóa/rebuild `video_index.db` schema cũ và ghi đè `all_vectors.npy`. Chưa có lệnh portable để rebuild `video_index_v2.db`; cần sửa path hard-code trong `scripts/build_sqlite_cache.py` trước khi dùng, đồng thời lưu ý script sẽ xóa DB đích.

## Bước tiếp theo

1. Hợp nhất DB path/schema, sửa health check theo DB runtime V2 và bỏ hằng count cũ.
2. Chuẩn hóa data paths (đặc biệt metadata theo BASE_DIR) và tách model/vector/FAISS loading khỏi import-time.
3. Chọn hướng Gemini/BM25: thêm đúng dependency và nối API, hoặc loại bỏ code/dependency chưa dùng; đổi nhãn ASR trên UI cho đúng runtime.
4. Bổ sung object route; quyết định semantics cho temporal nhiều vế/video filter; thêm test cho search/context/interval/time conversion.
5. Xử lý secrets, bật TLS verification, thu hẹp CORS và thêm authentication/rate limiting.
6. Đồng bộ frame_map với DB runtime, làm portable pipeline tạo V2/import OCR-ASR-object, tránh xóa/ghi đè mặc định và bổ sung runbook deploy/cache model cùng lockfile.

## Quy tắc cập nhật

Cập nhật trực tiếp file này khi thay đổi lớn về kiến trúc, API, database, data pipeline hoặc tính năng. Không tạo thêm file context khác.
