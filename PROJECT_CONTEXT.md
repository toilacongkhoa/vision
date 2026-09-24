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
├── tools/benchmark_chatbot.py    # benchmark chatbot SSE, namespace session riêng mỗi lượt
├── src/dres_submission.py       # serializer/validator DRES và công thức điểm 2026
├── src/dres_client.py           # HTTP client DRES v2, HTTPS, session variants, unknown submit outcomes
├── src/dres_api.py              # API routes login/evaluation/submit và duplicate guard, injectable cho test
├── tools/benchmark_dres_submission.py # contract benchmark payload, timestamp, duplicate và scoring DRES
├── tools/dres_contract_checks.py # mock contract tests cho DRES client/API/dedup
├── tools/benchmark_chatbot_primary.py # regression chấm candidate đầu KIS/Q&A
├── tools/benchmark_vlm_selection.py # scorecard candidate-level VLM, hash candidate set và nhiều lượt
├── tools/run_vlm_selection.py   # chạy/audit phiên Agy độc lập trên manifest frame cố định
├── tools/benchmark_chatbot_stream.py # regression parser/diagnostic SSE chatbot
├── tools/benchmark_chatbot_sessions.py # regression cô lập session giữa lượt/case
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
- Frontend result grid; preview prev/next bằng nút, bàn phím hoặc swipe; infinite filmstrip; object/OCR bounding boxes; telemetry thời gian API/tải ảnh. Nếu ảnh keyframe lỗi, UI lần lượt thử URL ảnh dự phòng và hiện thông báo nếu hết nguồn, giữ video ID/frame/timestamp cho operator tiếp tục xác minh. P0 UI có workspace câu thi đang hoạt động với loại câu, timer 4/5 phút phía trình duyệt, câu hỏi/mô tả đầu, lịch sử clue có thời điểm và trạng thái draft/final/prepared/sent/accepted/rejected do operator ghi nhận. Workspace, query tìm kiếm, shortlist/eliminated và candidate/answer trong Submission Builder tự lưu cùng `vrs_submission_v2`; reset câu có xác nhận và giữ danh sách candidate/answer trong Submission Builder. P1 card actions cho ghim, loại/khôi phục, mở preview và chọn candidate đã ghim sang Submission Builder; shortlist hiển thị thumbnail/metadata hai cột để so sánh cạnh nhau, và trạng thái khôi phục sau refresh. Với TRAKE, mô tả ban đầu và clue tạo các event theo thứ tự; candidate ghim được gán event, bảng báo thiếu/trùng candidate, video khác nhau hoặc timestamp không tăng, và lưu mapping sau refresh. Sequence hợp lệ có thể đồng bộ thành một query TRAKE riêng trong Submission Builder, một row gồm video ID và frame list theo thứ tự event; đồng bộ lại chỉ ghi đè draft chưa bị operator sửa, nếu đã sửa thì tạo query riêng mới. Diễn tập qua API healthy xác nhận KIS và Q&A trả candidate, clue có thể chạy tìm kiếm lặp lại, hai candidate shortlist cùng query draft khôi phục sau refresh; sequence TRAKE thử nghiệm cho kết quả hợp lệ với 5 frame cùng video tăng thời gian, phát hiện được thứ tự/video sai và đưa frames theo thứ tự sang Builder sau refresh. P0 workspace đạt tiêu chí thao tác/lưu nháp; correctness nội dung chưa được chấm, chưa xác minh DRES server nhận bài. Năm lượt P3 keyboard-only (hai TRAKE, một QA, một Video KIS, một KIS textual) xác nhận các đường preview/reload và một số lỗi inline; một lượt TRAKE kiểm tra focus trong modal, vòng Tab, Escape trả focus, note TEST ONLY và duplicate warning sau reload. Đây vẫn là dữ liệu tổng hợp, chưa kiểm chứng correctness hoặc các kịch bản đủ điều kiện P3.
- Chat UI render Markdown, trích `VideoID, FrameIdx` thành candidate cards và mở preview/context trực tiếp.
- Submission Builder KIS/QA/TRAKE, lưu localStorage và xuất submission.zip; DRES JSON được backend local serialize/validate rồi hiện trong hộp review cùng ID/query/answer/frame, timestamp ms từ chính payload và ảnh/evidence OCR/ASR/object của frame. ID video, frame index, answer Q&A và dãy frame TRAKE được validate ngay tại ô nhập, báo lỗi cạnh ô, đồng thời chặn mở review đến khi sửa đúng; raw TRAKE draft được giữ khi đang nhập để không mất text chưa hợp lệ. Nút Submission Build mở thẳng Builder và focus query đang chọn; các query có nút chọn riêng dùng bàn phím, focus được giữ sau khi chọn. Diễn tập keyboard-only TRAKE xác nhận sai thứ tự báo lỗi inline, dãy được sửa có thể mở review và vẫn giữ sau refresh. History local ghi từng lần chuẩn bị và payload. Review có DRES login/evaluation/submit; session chỉ ở RAM trình duyệt. 2xx được ghi Sent, HTTP 412 là Rejected, còn timeout/5xx là chưa rõ kết quả; UI/backend chặn exact payload đã Sent/Rejected/unknown cho cùng query. Accepted vẫn do operator ghi nhận sau khi xác minh response. Không có request DRES thật trong các kiểm thử hiện tại. Nếu answer thay đổi sau review, bắt buộc chuẩn bị lại.
- `src/dres_submission.py` tạo payload DRES v2 cho Textual/Video KIS, Q&A, TRAKE; đổi `pts_time` giây sang millisecond bằng Decimal half-up; kiểm tra ID/frame/sequence; chống gửi lặp payload giống hệt theo query nhưng cho phép gửi đáp án đã sửa; tính điểm full/partial theo hướng dẫn Chung kết 2026. `src/dres_client.py` và `src/dres_api.py` nối login/list ACTIVE/submit DRES v2, yêu cầu HTTPS, hỗ trợ sessionId JSON hoặc session cookie fallback, validate trước POST và khóa duplicate Sent/Rejected/unknown trong tiến trình app. `DRES_API_BASE_URL` cấu hình ở backend, mặc định `https://eventretrieval.one`. `DRES_USERNAME`/`DRES_PASSWORD` tùy chọn trong Git-ignored `.env` dùng cho nút **Get session from .env**; route này chỉ nhận cùng-origin localhost, credential không trả về UI/log, còn sessionId chỉ ở RAM trình duyệt. Đăng nhập thủ công trong modal vẫn có thể dùng. Backend `localhost:8000` hiện đã nạp các route DRES; health báo healthy. `python -m tools.dres_contract_checks` kiểm tra route/client/dedup; `tools/benchmark_dres_submission.py` khóa payload/scoring contracts; `tools/benchmark_dres_operator.py` kiểm tra route/UI contracts trong `.venv`. Chưa chạy login/submit live, xác nhận `start=end` hoặc giải nghĩa response cùng evaluation BTC. `compare_submission_timing` và `tools/simulate_dres_timing.py` so sánh kỳ vọng điểm nộp sớm (có thể sửa sau lần sai) với chờ, nhận xác suất do operator nhập; không tự hiệu chuẩn hay đề xuất chính sách. `tools/benchmark_dres_timing.py --json` khóa 6 contract mô phỏng. Audit read-only kết quả VLM vòng 101 thấy confidence trung bình 0,941/0,942 nhưng Top-1 0,367/0,300 (30 lượt/cấu hình); Brier 0,554/0,617. Mỗi query chỉ có một output cuối, không có nhiều checkpoint theo thời gian; không dùng confidence này làm xác suất chiến thuật hoặc để hiệu chuẩn. `POST /api/v1/submission/dres/export` tra cứu frame chính xác và serialize payload local; Submission Builder mở review trước khi tải, đối chiếu frame/timestamp/evidence. `start=end` biểu diễn timestamp điểm và vẫn chờ xác minh với evaluation server.
- Vòng 106 retrieval benchmark trên 57 query: semantic 2/57 (MRR 0,0079); ASR fallback 7/57 (R@1/5/10/50=2/2/3/7, MRR 0,0358); hybrid 8/57 nhưng MRR 0,0232, latency p50/p95 1.441/3.833 ms. Weighted RRF benchmark-only ASR:hybrid 2:1 cho 7/57 và MRR 0,0358; 1:2 cho 8/57, MRR 0,0363 nhưng làm mất một ASR hit, chỉ thêm ròng một hit và chậm hơn ASR. Không giữ fusion. Hai TRAKE case không có hit nào trong 8 event ở top-50; temporal ordering chưa phải nút thắt.
- Vòng 107–108 fast-path profile trên semantic 57-case benchmark: model init cProfile ~6,44 giây; OpenCLIP `encode_text` ~24,1 giây cumulative/64 calls dưới profiler. Thử PyTorch intra/inter-op threads=4 giữ accuracy 2/57 và MRR 0,0079 nhưng latency p50/p95 thành 843/1.758 ms, TTFC p50/p95 1.663/1.784 ms, xấu hơn baseline 405/1.559 và 1.327/1.423 ms. Không giữ cấu hình hoặc đổi runtime.
- Vòng 109 thử PyTorch intra/inter-op threads=1 hai lượt: accuracy 2/57, MRR 0,0079; latency p50/p95 lần lượt 268/579 ms và 1.629/3.289 ms, median 949/1.934 ms so baseline mặc định ba lượt median 487/1.559 ms; kết quả không tái lập nên loại cấu hình. `tools/benchmark.py` có thể gọi Google Translate/MyMemory nếu query cache miss; không xác nhận được request có ra ngoài trong lượt đó.
- Vòng 110 offline-only: baseline mặc định 14 threads ba lượt đều 2/57, MRR 0,0079; median latency p50/p95 420/1.186 ms, TTFC p50/p95 567/686 ms. Một lượt 1 thread đạt 2/57 nhưng p50/p95 779/4.094 ms, TTFC 4.081/7.329 ms; loại. Đây không so sánh trực tiếp được với benchmark cũ có thể dùng online translation.
- `tools/benchmark_vlm_selection.py` chấm kết quả VLM trên manifest query/candidate cố định và JSONL kết quả nhiều lượt: primary location Top-1, Hit@3/@5, MRR, Q&A answer accuracy khi location đúng và full-answer accuracy, chọn sai với confidence cao, latency p50/p95, timeout, token/cost nếu adapter cung cấp. Manifest Q&A phải có `accepted_answers`; output Q&A phải có `answer` đúng thì full answer mới đúng. Hash khóa danh sách ID/frame giữa các lượt; TRAKE biểu diễn mỗi candidate thành một chuỗi frame và chỉ cho gắn nhãn đúng với sequence cùng video, tăng nghiêm ngặt. CLI mặc định yêu cầu ít nhất 5 lượt/case và từ chối hạ ngưỡng; smoke nấu ăn 3 lượt hiện báo coverage chưa đủ. `--baseline-results` so sánh hai cấu hình trên cùng manifest, chỉ dùng panel lượt đầy đủ, báo trung bình/độ lệch chuẩn, CI 95% bảo thủ của chênh lệch, ngưỡng 2× độ lệch chuẩn baseline và case hồi quy; session độc lập vẫn phải được runner xác minh. `--self-test` chỉ kiểm tra scorecard tổng hợp, không đo accuracy model thật.
- `tools/benchmark_chatbot.py` hiện chấm KIS/Q&A bằng cặp `VideoID, FrameIdx` đầu tiên trong output Agy; hit ở candidate sau chỉ báo qua `any_location_correct`, không làm `correct=True`. `tools/benchmark_chatbot_primary.py --json` khóa sáu tình huống candidate đầu/dự phòng và answer Q&A. Đây là phép suy ra thứ tự gợi ý từ văn xuôi, chưa phải schema `primary_submission` tường minh; TRAKE vẫn dùng phép chấm chuỗi cũ.

## Vấn đề ảnh hưởng việc phát triển tiếp

- DB artifact hiện thiếu `ocr_fts`/`asr_fts`: OCR/ASR API và MCP `search_video_evidence` phải dùng fallback scan bằng LIKE qua `/api/v1/search/all`; các term fallback đã được truy vấn song song để giảm latency, nhưng vẫn chậm hơn native FTS. README đang mô tả DB có FTS nhưng repo không còn migration/builder để tạo chúng.
- Path chưa thống nhất hoàn toàn: SQLiteSearchEngine và MCP đã dùng chung `DB_PATH`, được khóa bằng `tools/benchmark_database_config.py` 2/2 scenario pass. `PORT` vẫn không được MCP/frontend dùng vì API base hard-code `127.0.0.1:8000`/`localhost:8000`; override port trong `.env.example` vì vậy chưa hoạt động end-to-end.
- `.venv` hiện chưa đồng bộ hoàn toàn với requirements pins: `mcp==1.29.1` đã được cài để Agy khởi động được `video-researcher`, nhưng CTranslate2, Transformers, SentencePiece và Sacremoses vẫn cần kiểm tra/cài nếu dùng translator offline. `search_video_evidence` vẫn phụ thuộc các bảng FTS chưa có trong DB.
- `tools/benchmark_chatbot.py` báo số SSE/tool event, DONE, số ký tự và raw data tail; diagnostic được in ASCII-safe trên Windows. Mỗi invocation mặc định tạo namespace session ngẫu nhiên, hoặc nhận `--session-run-id`, để không tái sử dụng lịch sử Agy của lượt benchmark trước. `tools/benchmark_chatbot_sessions.py` khóa session isolation 3/3; `tools/benchmark_chatbot_stream.py` khóa parser client 3/3; `tools/benchmark_agy_result_stream.py` khóa Agy result→SSE 3/3. Agy 1.2.8 đã xác thực trong profile người dùng; khi chạy trong Codex sandbox, profile `.gemini` không ghi được và tạo lỗi auth giả, nên production chatbot benchmark phải chạy backend với quyền truy cập profile bình thường. Baseline cô lập gần nhất trên 3 KIS case đạt 1/3, trung bình 52,86 giây, 0 lỗi; đủ tin cậy để tiếp tục P4 nhưng còn biến thiên model.
- P0 VLM candidate-selection có scorecard và runner audit session độc lập. Vòng 101 dùng manifest 6 case/5 frame hard-negative/case, năm panel cho mỗi cấu hình, Agy 1.2.9 + Gemini 3.8 Flash Medium. Baseline đạt Top-1 11/30, full answer 10/30, MRR 0,599; profile prompt `evidence` đạt 9/30, 6/30, MRR 0,544, chậm hơn 12,9% theo latency trung bình panel. Cả hai có QA answer đúng 0 lần khi location đúng. Không giữ prompt thay đổi; runtime giữ nguyên. Manifest, JSONL và raw streams ở `tools/benchmark_data/vlm_diverse_6.json`, `vlm_diverse_baseline_v2_*`, `vlm_diverse_evidence_v1_*`. Đây vẫn là workload nhỏ, chưa đủ để quyết định runtime cho Chung kết; 14.2 cần benchmark agent end-to-end có OCR/ASR/TRAKE và output cuối.
- Repo đã xóa toàn bộ script index/migration/import OCR-ASR-object; chưa có pipeline tái tạo `video_index_v2.db`, FTS hay optional `metadata_cache.pkl` từ dữ liệu nguồn.
- Vector và OpenCLIP vẫn load/warm ngay khi import app. FAISS bị disable tuyệt đối nhưng `faiss-cpu` vẫn được pin; metadata cache được hỗ trợ nhưng không có file/builder trong workspace.
- FastTranslator chỉ nhận diện tiếng Việt qua ký tự có dấu/`đ`; query tiếng Việt không dấu không được dịch. Model offline và các dependency dịch offline không có trong workspace; runtime khi cache miss phụ thuộc Google/MyMemory và Internet, rồi âm thầm dùng nguyên văn tiếng Việt nếu cả hai thất bại. Chỉ 1/57 query benchmark khớp cache toàn câu, nên môi trường không có network đưa phần lớn tiếng Việt trực tiếp vào OpenCLIP tiếng Anh. Việc gửi query thi ra dịch vụ bên thứ ba cần được cho phép riêng. Từ vòng 110, `tools/benchmark.py` và `tools/benchmark_multimodal.py` mặc định tắt local/online translator fallback để không gửi query ra ngoài; cờ `--allow-online-translation` bật lại có chủ đích, và API mode yêu cầu cờ này vì client không thể kiểm soát server. Vì cache hiện có thể đã nhận thêm bản dịch từ benchmark cũ, số offline sau vòng 110 không được so trực tiếp với baseline trước đó.
- Health chỉ kiểm tra file tồn tại và hard-code 177321, không kiểm tra schema/count/model/Agy/MCP. Metadata Drive/FPS được resolve theo `BASE_DIR`; `tools/benchmark_runtime_paths.py` khóa hồi quy launch CWD cho metadata Drive.
- Agy tạo một session process cho mỗi client/model route; process vẫn chạy với `--dangerously-skip-permissions`, stderr bị discard và chưa có cleanup toàn cục khi shutdown. Cần bổ sung TTL/eviction nếu có nhiều client đồng thời.
- TLS verification bị tắt cho Supabase/Drive proxy; CORS mặc định `*` với credentials; chưa có auth/rate limit. MCP `search_image_by_url` tải URL tùy ý, chưa chặn SSRF/content-size trước khi download.
- Frontend render output Agy bằng `marked.parse(...).innerHTML` không sanitize; tool labels và một số metadata cũng được nối vào HTML, có nguy cơ XSS.
- Drive proxy cache tối đa 1000 full file bytes nhưng không giới hạn tổng dung lượng. Khi `r2_url` tồn tại nhưng tải lỗi, frontend/MCP không retry qua Google Drive; Drive chỉ được chọn khi record không có R2 URL.
- ASR UI được đặt nhãn `ASR Transcript Search`: API chạy exact phrase FTS khi artifact tồn tại và fallback substring scan khi thiếu bảng FTS; không dùng BM25. Frontend vẫn gửi `enable_rerank` ngoài schema. Form Video Interval vẫn nằm trong HTML nhưng không còn tab để mở; `/search/all` cũng chưa nối UI.
- Submission Builder xuất CSV trong ZIP và tải JSON DRES; code login/list evaluation/submit DRES đã có nhưng chưa gửi trực tuyến. Chưa có credential/evaluation của BTC để xác minh response, cách server hiểu `start/end` hoặc delimiter câu trả lời Q&A. Simulator nộp sớm/chờ chỉ tính theo xác suất do operator nhập; chưa có dữ liệu hiệu chuẩn xác suất theo query type/evidence và chưa hiển thị preview/count submit trong UI.
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
