# PROJECT CONTEXT — Video Retrieval System V3

## Mục tiêu

Hệ thống tìm kiếm keyframe/video đa phương thức cho AI Challenge. Người dùng tìm frame bằng mô tả tự nhiên, ảnh, OCR, ASR hoặc chuỗi sự kiện; xem metadata/bounding box/video và xuất submission KIS, QA hoặc TRAKE.

## Tech stack

- Windows 10/11, Python 3.10–3.12; FastAPI 0.141.1, Uvicorn 0.52.4, Pydantic 2.13.4. `requirements.txt` pin exact version nhưng chưa có lock/hash file.
- PyTorch 2.13.0, OpenCLIP 3.3.0 (ViT-B-32/openai), NumPy 2.4.6, Pillow 12.3.0. `faiss-cpu` 1.15.0 vẫn là dependency nhưng runtime hiện tắt FAISS và dùng NumPy dot product/argpartition.
- SQLite cho metadata keyframe và cache dịch; code hỗ trợ FTS5 OCR/ASR nhưng DB hiện tại chưa có các bảng FTS. Supabase tùy chọn được gọi bằng REST/`urllib`.
- `deep-translator`; CTranslate2 4.8.2 + Transformers 5.17.0 + SentencePiece/Sacremoses cho model dịch Việt–Anh offline tùy chọn.
- Antigravity CLI (`agy`) + MCP SDK 1.29.1 + HTTPX 0.28.1 cho chatbot tìm kiếm/kiểm chứng trực quan.
- Cloudflare R2 là nguồn ảnh ưu tiên; Google Drive metadata, iframe và proxy được dùng khi kết quả không có R2 URL.
- Frontend một file HTML với TailwindCSS CDN và Marked CDN không pin version, JavaScript inline, JSZip 3.10.1.

## Kiến trúc chính

~~~text
Browser / frontend/index.html
        |
        +-- manual search / preview / submission
        |          |
        |          v
        |   FastAPI: src/main.py
        |          +-- SQLiteSearchEngine
        |          |      +-- OpenCLIP + NumPy
        |          |      +-- all_vectors.npy
        |          |      \`-- video_index_v2.db / optional metadata_cache.pkl
        |          +-- FastTranslator -> memory + translation_cache.db
        |          |                     +-- optional CTranslate2 model
        |          |                     \`-- Google/MyMemory fallback
        |          +-- R2 URL / Google Drive proxy + iframe
        |          +-- SupabaseService (optional endpoints)
        |          \`-- video_drive_metadata.json / video_fps_map.json
        |
        \`-- POST /api/v1/chat (SSE)
                   \`-- two prewarmed AgySession subprocesses (flash/pro)
                              \`-- configured MCP `video-researcher` (stdio)
                                         \`-- mcp_server.py -> FastAPI / SQLite / R2 contact sheets
~~~

### Luồng tìm kiếm

1. Manual search gọi `/api/v1/search`, `/api/v1/search/image`, `/api/v1/search/similar` hoặc các endpoint context/interval/filmstrip.
2. Semantic query tiếng Việt có dấu được FastTranslator dịch từ memory/SQLite cache, model CTranslate2 nếu có, rồi Google/MyMemory fallback; query không được nhận diện là tiếng Việt được giữ nguyên. Embedding OpenCLIP và candidate ranking theo chuỗi text/mệnh đề đã dịch được giữ trong hai LRU in-process tối đa 256 entry; query một mệnh đề có thể tái sử dụng prefix của entry top-K lớn hơn. Các vế phân cách bằng dấu phẩy, chấm phẩy hoặc `and` được encode riêng và hợp nhất thứ hạng bằng Reciprocal Rank Fusion (RRF); prefix reuse không áp dụng cho RRF vì cutoff có thể đổi thứ hạng. Opt-in mode `smart` giữ query tiếng Việt gốc, tạo lexical query online-safe bằng stopword tĩnh và tối đa 6 token, chạy semantic/ASR rồi xếp candidate theo ba tầng: 5 kết quả RRF consensus đầu, tối đa 10 kết quả semantic đầu chưa trùng, sau đó ASR theo thứ tự; semantic vẫn là mode mặc định nhanh hơn. OCR đã được loại khỏi fusion production vì benchmark đủ 57 case cho thấy nhánh này không thêm hit và làm giảm kết quả hợp nhất.
3. `all_vectors.npy` đã L2-normalized; runtime tính NumPy dot product và dùng `argpartition` chọn top-K. Similar-by-vector trả danh sách rỗng cho vector ID ngoài phạm vi và giữ cache LRU in-process tối đa 256 bộ candidate theo vector/top-K; entry top-K lớn hơn được tái sử dụng theo prefix cho request nhỏ hơn cùng vector. Image search cũng giữ LRU 256 bộ candidate theo SHA-256 nội dung ảnh/top-K và tái sử dụng prefix, nhờ đó bỏ encode/scoring cho upload lặp lại y hệt. FAISS luôn bị disable trong `_init_faiss`.
4. Metadata lấy từ `metadata_cache.pkl` nếu file tồn tại; workspace hiện không có cache này nên engine batch-query `video_index_v2.db`, đọc `keyframes.raw_json` và sinh R2 URL từ `image.rel_path` (`.jpg` → `.webp`). Metadata đã format của semantic và fuzzy top-K được cache trong process; kết nối SQLite được tái sử dụng theo từng thread ở chế độ read-only/query-only/autocommit với page cache 64 MB và mmap 256 MB.
5. OCR/ASR thử exact phrase qua `ocr_fts`/`asr_fts`; trạng thái tồn tại của mỗi bảng FTS được cache trong process, nên DB thiếu bảng đi thẳng sang token-substring `LIKE` mà không lặp exception. Candidate fallback được giữ trong cache LRU in-process tối đa 256 query/filter; request top-K nhỏ có thể tái sử dụng prefix đã xếp hạng của entry top-K lớn hơn cùng field/query/filter. Cache chỉ lưu ID/score và warm query tái sử dụng metadata đã format. Các term fallback của MCP `search_video_evidence` được truy vấn song song; DB hiện tại không có hai bảng FTS nên cold query vẫn chậm hơn native FTS.
6. Frontend ưu tiên R2 để hiển thị kết quả, mở preview/bounding box/filmstrip, mở Google Drive video hoặc thêm frame vào submission.

Chatbot phân loại request có marker trình tự hoặc nhiều câu sang session `pro`, còn lại sang `flash`; hai Agy process được prewarm song song sau startup. Agy dùng prompt giới hạn tool budget, gọi MCP để search semantic/OCR/ASR, gom evidence đa sự kiện, dựng contact sheet tối đa 20 ảnh và sequence sheet, rồi stream câu trả lời về frontend bằng SSE. Backend không còn `temporal_search`; chuỗi sự kiện được xử lý ở tầng Agy/MCP bằng nhiều search và kiểm chứng ảnh.

## API chính

- GET / — frontend.
- GET /api/v1/health — kiểm tra file DB/vector và Supabase config; `total_keyframes` hiện hard-code 177321.
- POST /api/v1/search — một mode semantic, smart hybrid, OCR hoặc ASR.
- POST /api/v1/search/all — chạy semantic/OCR/ASR đồng thời và trả ba nhánh riêng; frontend hiện không gọi endpoint này.
- POST /api/v1/search/image — tìm bằng ảnh upload.
- POST /api/v1/search/similar — tìm frame tương tự từ vector ID.
- POST /api/v1/chat — chatbot Agy qua SSE.
- GET /api/v1/search/context — frame kế tiếp hoặc frame xung quanh theo stored keyframes.
- GET /api/v1/search/interval — frame trong khoảng timestamp.
- GET /api/v1/video/{video_id}/frames — keyframe trong khoảng frame number.
- GET /api/v1/video/{video_id}/filmstrip — phân trang keyframe `around`/`before`/`after` theo thứ tự DB.
- GET /api/v1/video/{video_id}/convert_time — timestamp → frame index.
- GET /api/v1/video/{video_id} — Google Drive video metadata.
- GET /api/v1/drive/proxy/{file_id} — proxy/cache file Google Drive.
- GET `/api/v1/supabase/video/{video_id}`, `/frame/{frame_id}`, `/video/{video_id}/frames` — lookup Supabase tùy chọn.

## Cấu trúc quan trọng

~~~text
vision/
├── frontend/index.html           # UI search/chat/preview/filmstrip/submission
├── mcp_server.py                 # 9 MCP tools search, evidence và contact sheets
├── src/main.py                   # FastAPI routes, SSE chat, Agy prewarm
├── src/config.py                 # paths, model, host/port, CORS
├── src/sqlite_engine.py          # OpenCLIP + NumPy + SQLite retrieval
├── src/fast_translator.py        # VI→EN local/online + SQLite cache
├── src/agy_session.py            # Agy subprocess, model routing, prompt và SSE
├── src/supabase_service.py       # Supabase REST client tùy chọn
├── .env.example                  # biến môi trường mẫu
├── requirements.txt              # exact dependency pins
├── tools/benchmark.py            # benchmark semantic retrieval KIS/QA/TRAKE
├── tools/benchmark_multimodal.py # benchmark semantic/OCR/ASR/reference hybrid
├── tools/benchmark_operator_search.py # benchmark UI mode wiring và API smart route/output
├── tools/benchmark_trake_sequence.py # regression benchmark chấm chuỗi TRAKE
├── tools/benchmark_qa_evidence.py # regression benchmark evidence Q&A gắn đúng location
├── tools/benchmark_chatbot.py    # benchmark chatbot SSE
├── tools/benchmark_chatbot_stream.py # regression parser/diagnostic SSE chatbot
├── tools/benchmark_agy_result_stream.py # regression Agy result → SSE response/error
├── tools/benchmark_similar.py    # regression benchmark valid/invalid và prefix-cache similar
├── tools/benchmark_semantic_cache.py # regression benchmark semantic cache
├── tools/benchmark_fuzzy_cache.py # regression benchmark fallback OCR/ASR và cache
├── tools/benchmark_image_cache.py # regression benchmark repeated/mixed-top-K image search
├── tools/benchmark_runtime_paths.py # regression benchmark metadata path theo launch CWD
├── tools/benchmark_database_config.py # regression benchmark DB_PATH cho engine/MCP
├── all_vectors.npy               # runtime local, 177321 x 512 float32
├── video_index_v2.db             # runtime local, keyframes; hiện chưa có FTS
├── video_drive_metadata.json     # runtime local, 873 video → Drive IDs
├── video_fps_map.json            # 873 video → FPS
├── translation_cache.db          # generated local translation cache
├── metadata_cache.pkl            # optional, hiện không có trong workspace
└── models/opus-mt-vi-en-ct2/     # optional offline translator, hiện không có
~~~

Dữ liệu hiện tại: all_vectors.npy có shape 177321 x 512 float32 và đã normalized; video_index_v2.db có 177321 rows, 873 video, vector_id liên tục 0..177320 nhưng chỉ có bảng `keyframes`; metadata video/FPS đều có 873 video. `translation_cache.db` hiện có 57 entry, nhưng chỉ 1/57 query của benchmark thi chính khớp cache toàn câu. `frame_map_supabase.json` vẫn tồn tại như artifact local bị ignore nhưng không được source runtime tham chiếu.

Các thư mục/script build index và module legacy (`scripts/*.py`, `src/db.py`, `src/search_engine.py`, indexer/GDrive mapper/Gemini/uploader) đã bị xóa khỏi source tracked; `scripts/` hiện chỉ còn pycache local bị ignore.

## Tính năng hiện có

- Semantic text search, dịch Việt–Anh có memory/SQLite cache và lọc theo video.
- `tools/benchmark.py` đánh giá retrieval KIS/Q&A/TRAKE trên 57 case và báo đúng/sai, location rank, Recall@1/5/10/50, MRR, latency p50/p95, TTFC của case đúng. Q&A chỉ chấm `answer_evidence` trong candidate khớp đúng video/cửa sổ location; đây là evidence proxy của retrieval, không phải answer generation, và được khóa bởi `tools/benchmark_qa_evidence.py`. TRAKE báo event-rank độc lập nhưng chỉ chấm case đúng khi chọn được đủ candidate cùng video với frame tăng nghiêm ngặt; `tools/benchmark_trake_sequence.py` khóa các case ordered, dùng trùng frame và đảo thứ tự. Tolerance ±150 giây là cấu hình benchmark hiện tại, không phải luật Chung kết 2026 đã xác nhận.
- `tools/benchmark_multimodal.py` chạy semantic, OCR, ASR và production `smart_search` trên engine tách biệt để tránh cache làm sai latency; lexical query dùng stopword tĩnh và tối đa 6 token theo thứ tự, không dùng answer hay thống kê toàn bộ test set. Tool báo rank/Recall/MRR/p50/p95/TTFC theo từng strategy và danh sách semantic target bị hybrid làm mất. Production smart semantic+ASR với consensus-head fusion hiện đạt 8/57, R@5/10/50 = 3/4/8, MRR 0,0232 và bảo toàn 2/2 semantic hit so với semantic 2/57; lượt đo gần nhất có p50/p95 khoảng 1,67/2,66 giây trên DB thiếu FTS, nên mode vẫn opt-in.
- Image similarity search và similar-by-vector đều có regression benchmark; image search bao phủ repeated input và mixed top-K. API có thể chạy semantic/OCR/ASR đồng thời hoặc production smart hybrid theo mode opt-in. Fallback OCR/ASR có benchmark chuyên biệt cho cold/warm cache, mixed top-K và video filter. Frontend cho phép operator chọn `Smart Hybrid (Semantic + ASR)` nhưng vẫn giữ semantic làm mặc định; `tools/benchmark_operator_search.py` kiểm tra dropdown mode, wiring request, schema/routing smart và output `video_id/frame_idx`, hiện pass 4/4. MCP chưa gọi mode này trực tiếp.
- OCR/ASR exact-phrase FTS khi DB hỗ trợ, fallback token-substring SQL LIKE với DB hiện tại.
- Context, frame range, interval, filmstrip phân trang và timestamp → frame index.
- Chatbot SSE với model routing flash/pro, session isolation theo `session_id`, prewarm, tool-status heartbeat và stop/abort trên frontend.
- MCP search semantic/OCR/ASR/image URL/context; evidence recall đa sự kiện; candidate contact sheet, sequence sheet và vision probe.
- R2 image URL, Google Drive proxy/cache, video iframe và ba endpoint lookup Supabase tùy chọn.
- Frontend result grid; preview prev/next bằng nút, bàn phím hoặc swipe; infinite filmstrip; object/OCR bounding boxes; telemetry thời gian API/tải ảnh.
- Chat UI render Markdown, trích `VideoID, FrameIdx` thành candidate cards và mở preview/context trực tiếp.
- Submission Builder KIS/QA/TRAKE, lưu localStorage và xuất submission.zip.

## Vấn đề ảnh hưởng việc phát triển tiếp

- DB artifact hiện thiếu `ocr_fts`/`asr_fts`: OCR/ASR API và MCP `search_video_evidence` phải dùng fallback scan bằng LIKE qua `/api/v1/search/all`; các term fallback đã được truy vấn song song để giảm latency, nhưng vẫn chậm hơn native FTS. README đang mô tả DB có FTS nhưng repo không còn migration/builder để tạo chúng.
- Path chưa thống nhất hoàn toàn: SQLiteSearchEngine và MCP đã dùng chung `DB_PATH`, được khóa bằng `tools/benchmark_database_config.py` 2/2 scenario pass. `PORT` vẫn không được MCP/frontend dùng vì API base hard-code `127.0.0.1:8000`/`localhost:8000`; override port trong `.env.example` vì vậy chưa hoạt động end-to-end.
- `.venv` hiện chưa đồng bộ hoàn toàn với requirements pins: `mcp==1.29.1` đã được cài để Agy khởi động được `video-researcher`, nhưng CTranslate2, Transformers, SentencePiece và Sacremoses vẫn cần kiểm tra/cài nếu dùng translator offline. `search_video_evidence` vẫn phụ thuộc các bảng FTS chưa có trong DB.
- `tools/benchmark_chatbot.py` báo số SSE/tool event, DONE, số ký tự và raw data tail; diagnostic được in ASCII-safe trên Windows. `tools/benchmark_chatbot_stream.py` khóa parser client 3/3, còn `tools/benchmark_agy_result_stream.py` khóa Agy result→SSE 3/3: forward result-only response, forward error và không lặp response sau text delta. Production hiện báo rõ `[ERROR] Lỗi Agy: authentication failed or timed out` thay vì silent DONE; cần đăng nhập/khôi phục Agy trước khi benchmark accuracy hoặc tối ưu MCP/prompt tiếp.
- Repo đã xóa toàn bộ script index/migration/import OCR-ASR-object; chưa có pipeline tái tạo `video_index_v2.db`, FTS hay optional `metadata_cache.pkl` từ dữ liệu nguồn.
- Vector và OpenCLIP vẫn load/warm ngay khi import app. FAISS bị disable tuyệt đối nhưng `faiss-cpu` vẫn được pin; metadata cache được hỗ trợ nhưng không có file/builder trong workspace.
- FastTranslator chỉ nhận diện tiếng Việt qua ký tự có dấu/`đ`; query tiếng Việt không dấu không được dịch. Model offline và các dependency dịch offline không có trong workspace; khi cache miss, runtime phụ thuộc Google/MyMemory và Internet, rồi âm thầm dùng nguyên văn tiếng Việt nếu cả hai thất bại. Chỉ 1/57 query benchmark hiện khớp cache toàn câu, nên môi trường không có network đưa phần lớn tiếng Việt trực tiếp vào OpenCLIP tiếng Anh. Việc gửi query thi ra dịch vụ bên thứ ba cần được cho phép riêng; chưa có ablation an toàn để chọn/download model đa ngôn ngữ mới.
- Health chỉ kiểm tra file tồn tại và hard-code 177321, không kiểm tra schema/count/model/Agy/MCP. Metadata Drive/FPS được resolve theo `BASE_DIR`; `tools/benchmark_runtime_paths.py` khóa hồi quy launch CWD cho metadata Drive.
- Agy tạo một session process cho mỗi client/model route; process vẫn chạy với `--dangerously-skip-permissions`, stderr bị discard và chưa có cleanup toàn cục khi shutdown. Cần bổ sung TTL/eviction nếu có nhiều client đồng thời.
- TLS verification bị tắt cho Supabase/Drive proxy; CORS mặc định `*` với credentials; chưa có auth/rate limit. MCP `search_image_by_url` tải URL tùy ý, chưa chặn SSRF/content-size trước khi download.
- Frontend render output Agy bằng `marked.parse(...).innerHTML` không sanitize; tool labels và một số metadata cũng được nối vào HTML, có nguy cơ XSS.
- Drive proxy cache tối đa 1000 full file bytes nhưng không giới hạn tổng dung lượng. Khi `r2_url` tồn tại nhưng tải lỗi, frontend/MCP không retry qua Google Drive; Drive chỉ được chọn khi record không có R2 URL.
- UI còn nhãn `ASR BM25 (Exact Text)` dù runtime không dùng BM25; frontend gửi `enable_rerank` ngoài schema. Form Video Interval vẫn nằm trong HTML nhưng không còn tab để mở; `/search/all` cũng chưa nối UI.
- Nhãn version không thống nhất: README/context gọi V3, frontend hiển thị 2.0 và FastAPI khai báo 2.1.0. Không có test suite/CI trong source clone-ready; `.gitignore` còn ignore `scripts/` và `test_*.py`.

## Chạy local

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
~~~

Cần đặt `all_vectors.npy`, `video_index_v2.db`, `video_drive_metadata.json` và `video_fps_map.json` ở project root. Đặt model dịch offline tại `models/opus-mt-vi-en-ct2/` nếu có; nếu không, translation cache miss cần Internet.

Cấu hình MCP một lần từ terminal đã activate `.venv` (thay đường dẫn tuyệt đối):

~~~powershell
agy mcp add video-researcher python "C:\duong-dan\toi\vision\mcp_server.py"
agy mcp list
python -m src.main
~~~

- Chờ log `[Startup] Flash model ready!` và `[Startup] Pro model ready!` để chatbot ổn định; HTTP server nhận request trước khi prewarm hoàn tất.
- UI: http://localhost:8000/
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

`.env.example` khai báo SUPABASE_URL/KEY (tùy chọn), HOST, PORT, CORS_ORIGINS, DB_PATH, CONSOLIDATED_VECTORS_PATH, DATA_ROOT và AGY_PATH. Engine/FastAPI/MCP đã dùng chung `DB_PATH`; hiện vẫn nên giữ port 8000 vì MCP/frontend chưa dùng override port. Workspace hiện tại có Agy và MCP entry `video-researcher`; `mcp==1.29.1` đã được cài trong `.venv` và đã xác minh import được 9 tool.

## Bước tiếp theo

1. Thêm migration/builder portable cho `keyframes`, `ocr_fts`, `asr_fts` và metadata cache; rebuild/kiểm tra DB artifact để MCP evidence dùng native FTS nhanh hơn fallback hiện tại.
2. Dùng config chung cho API base/port trong FastAPI, MCP và frontend; sửa health check theo runtime thật.
3. Đồng bộ `.venv` với requirements, thêm startup health cho Agy/MCP/model và giữ lại script verification/test trong source thay vì ignore/xóa.
4. Tách session Agy theo user hoặc làm stateless, tôn trọng `session_id`, bỏ quyền bypass mặc định, giữ stderr/log và cleanup subprocess khi shutdown.
5. Sanitize Markdown/HTML, chặn SSRF, bật TLS verification, giới hạn Drive cache, thu hẹp CORS và thêm auth/rate limiting.
6. Lazy-load model/vector; bỏ FAISS dependency hoặc bật lại có benchmark; sửa translator tiếng Việt không dấu, UI labels/form dead code/version và nối hoặc bỏ `/search/all`.

## Quy tắc cập nhật

Cập nhật trực tiếp file này khi thay đổi lớn về kiến trúc, API, database, data pipeline hoặc tính năng. Không tạo thêm file context khác.
