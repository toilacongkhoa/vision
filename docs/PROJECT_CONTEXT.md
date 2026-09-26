# Bối cảnh dự án — Video Retrieval System

> Cập nhật: 2026-09-26 trên nhánh `codex/r2-data-schema-fixes` (`6c78452` trước các sửa đổi trong workspace). File này mô tả mã nguồn và dữ liệu **đang có trên máy hiện tại**. Các số đo ngày 2026-09-25 ở phần dưới là lịch sử trên bộ L cũ; không được dùng làm số đo của bộ L/M/N/S mới. `docs/plan.md` ghi gate nghiệm thu; kiểm tra offline không xác nhận DRES thật đã nhận/chấm bài.

## Mục đích và ưu tiên hiện tại

Ứng dụng “Hệ thống tìm kiếm video” giúp đội thi AI Challenge tìm keyframe, kiểm chứng video/vị trí và chuẩn bị đáp án cho Textual KIS, Video KIS, Q&A, TRAKE. Người thao tác ghi câu hỏi và gợi ý, tìm bằng văn bản hoặc ảnh, xem frame/video lân cận, giữ ứng viên, chọn đáp án, xem payload DRES rồi tải JSON hoặc gửi qua DRES. Video KIS dùng mô tả hoặc phác họa do người thi nhập; quy định cuộc thi không cho thu lại clip truy vấn bằng thiết bị điện tử để nạp vào công cụ.

Ưu tiên kế tiếp là để bốn thành viên **mỗi người chạy một bản cài trên máy của mình**, với độ chính xác, tốc độ tìm kiếm và độ ổn định đủ dùng lúc thi, cùng Assistant chuyên biệt cho `Textual KIS`, `Video KIS`, `Q&A`, `TRAKE`. Đây là kế hoạch, chưa phải phần đã triển khai; không có yêu cầu một backend phục vụ bốn người đồng thời. Tên hiển thị là “Hệ thống tìm kiếm video” (không kèm số phiên bản). Các nhãn, trạng thái và chỉ dẫn do ứng dụng kiểm soát đã được Việt hóa; giữ các tên riêng, chữ viết tắt và khóa kỹ thuật cần đối chiếu. Danh sách chọn dạng câu giữ nguyên tiếng Anh. Luồng UI và DRES hiện có cần được giữ đúng khi thực hiện kế hoạch mới.

## Kiến trúc runtime

```text
Trình duyệt / frontend/index.html (HTML + Tailwind CDN + JavaScript inline)
  ├─ câu đang thi, tìm kiếm, kết quả, preview, chatbot, Submission Builder
  ├─ localStorage: vrs_submission_v2; sessionStorage: ID phiên chat
  └─ HTTP → FastAPI / src/main.py
      ├─ SQLiteSearchEngine / src/sqlite_engine.py
      │   ├─ OpenCLIP ViT-B-32-quickgelu/openai + NumPy + all_vectors.npy
      │   └─ video_index_v2.db: keyframes, OCR/ASR qua FTS hoặc LIKE
      ├─ TrafficSearchEngine / src/traffic_search.py → camera/traffic_search.db
      │   └─ videos, tracks, events; ánh xạ Nxxx-Vyyy → Nxxx_Vyyy
      ├─ FastTranslator / src/fast_translator.py: cache + model offline tùy chọn
      ├─ metadata video/FPS + docs/drive_video_index.jsonl, R2 URL, Drive proxy
      ├─ DRES export / src/dres_submission.py
      ├─ DRES login/list/submit / src/dres_api.py + src/dres_client.py
      └─ chat SSE / src/agy_session.py → Antigravity CLI (`agy`)
          └─ MCP `video-researcher` / mcp_server.py → API tìm kiếm, camera và ảnh kiểm chứng
```

Backend khởi tạo search engine khi import ứng dụng, tải vector và model OpenCLIP; chatbot mặc định prewarm hai phiên Agy `flash`/`pro` sau startup. Có thể đặt `AGY_PREWARM_ON_STARTUP=false` để giảm RAM lúc startup; phiên Agy sẽ chỉ được tạo khi có chat. Mỗi client chat có `session_id` riêng; chat trả SSE/heartbeat và không có deadline cứng toàn lượt; client hủy thì session được dọn. `AgySession.RESPONSE_TIMEOUT_SECONDS=None` nghĩa là heartbeat bên trong không có deadline riêng; prewarm có timeout riêng 90 giây. Tìm ảnh chạy ở worker thread để không chặn event loop. MCP hiện đăng ký **10 tool**, gồm semantic/OCR/ASR, camera, evidence đa sự kiện, context, ảnh URL và contact/sequence sheet. MCP HTTP riêng (`tools/run_mcp_http.py`) dùng `MCP_HOST`/`MCP_PORT`, mặc định loopback `127.0.0.1:8001`; `MCP_API_KEY` tùy chọn bảo vệ `/mcp`, còn `/health` không yêu cầu key. Nó chỉ cung cấp công cụ đọc, không có submit DRES. Câu trả lời tự do của model khác với nhãn UI cố định cần dịch.

Semantic search có thể dịch truy vấn tiếng Việt sang tiếng Anh bằng cache, model offline tùy chọn hoặc dịch vụ dự phòng trước khi encode. `smart` là mode mặc định, kết hợp semantic và ASR; `semantic` chỉ dùng semantic search. OCR/ASR dùng FTS5 khi DB có bảng tương ứng, nếu thiếu thì fallback `LIKE`. `_init_faiss()` hiện không dùng FAISS; xếp hạng vector bằng NumPy. Tìm bằng ảnh, tìm frame tương tự và các nhánh tìm kiếm có cache trong tiến trình.

## Bản đồ mã nguồn

| Đường dẫn | Vai trò |
|---|---|
| `frontend/index.html` | Toàn bộ trang UI, CSS, các chuỗi HTML tĩnh và chuỗi JavaScript sinh lúc chạy; trọng tâm Việt hóa. |
| `src/main.py` | FastAPI: trang chủ, health, search, frame/video/context, chat SSE và xuất DRES JSON cục bộ. |
| `src/sqlite_engine.py` | OpenCLIP/NumPy retrieval, metadata SQLite, OCR/ASR, smart fusion và cache. |
| `src/traffic_search.py` | Truy vấn chỉ đọc dữ liệu camera: video, track, sự kiện, lớp đối tượng, màu, hướng, chuyển động, thời gian. |
| `src/fast_translator.py` | Dịch truy vấn phục vụ retrieval; không phải hệ thống dịch nhãn UI. |
| `src/agy_session.py`, `mcp_server.py`, `tools/run_mcp_http.py` | Phiên AI Assistant, 10 MCP tool và endpoint Streamable HTTP tùy chọn. |
| `src/dres_submission.py` | Tạo/kiểm payload KIS, QA, TRAKE; đổi PTS giây thành mili giây. |
| `src/dres_client.py`, `src/dres_api.py` | Giao tiếp DRES v2 qua HTTPS: login, evaluation `ACTIVE`, submit; request lặp hợp lệ được chuyển tiếp. |
| `src/config.py`, `.env.example`, `requirements.txt` | Cấu hình đường dẫn, server, biến môi trường và dependency. |
| `src/supabase_service.py` | Metadata Supabase tùy chọn. |
| `tools/preflight.py`, `tools/data_manifest.py` | Kiểm tra dữ liệu/môi trường và manifest SHA-256 cho gói dữ liệu ngoài Git. |
| `tools/benchmark_*.py`, `tools/dres_contract_checks.py`, `tools/test_*.py` | Benchmark và kiểm tra cục bộ; không phải mã runtime. |
| `docs/plan.md`, `docs/TEST_PLAN.md` | Gate sẵn sàng thi và phạm vi kiểm thử. |
| `docs/AI_Challenge_2026_Chung_Ket.md`, `docs/DRES_OPERATOR_CHECKLIST.md` | Tóm lược quy định Chung kết và checklist nộp bài. |

`docs/PROJECT_CONTEXT.md` và `docs/plan.md` được theo dõi bằng Git. Một số ghi chú cục bộ, dữ liệu lớn và `.env` vẫn bị `.gitignore` loại khỏi Git. Không đưa credential, DB, vector, archive dữ liệu hoặc artifact benchmark lên Git khi chỉ làm tài liệu/UI.

## Dữ liệu và cấu hình

- Runtime mặc định tìm `video_index_v2.db`, `all_vectors.npy`, `video_drive_metadata.json`, `video_fps_map.json` ở thư mục gốc và `camera/traffic_search.db` cho tìm kiếm camera. `docs/drive_video_index.jsonl` là overlay được Git theo dõi, bổ sung Drive ID/URL cho 614 video M/N/S. `translation_cache.db` là cache cục bộ; `models/opus-mt-vi-en-ct2/` là model dịch offline tùy chọn. `frame_map_supabase.json` không được runtime web gọi trực tiếp.
- **Ảnh chụp dữ liệu 2026-09-26:** main DB 397.591 keyframe, 1.487 video (`L`: 873 video/177.321 frame; `M`: 304/94.677; `N`: 298/88.453; `S`: 12/37.140). Vector NumPy `(397591, 512)` float32, `vector_id` liên tục 0–397590. Main DB có 88.433 ASR segment trên 316 video. DB camera có 298 video, 143.662 track, 1.171.482 event; cả 298 video camera đều ánh xạ được sang main index. Metadata video có 1.487 mục, overlay có 614 ID duy nhất và đều tồn tại trong metadata. Không có bảng FTS OCR/ASR trong bản dữ liệu này, nên đường tìm từ khóa dùng fallback trong `src/sqlite_engine.py`.
- Manifest `vision-data.manifest.sha256` được tạo lại cho DB, vector, camera DB, metadata và FPS ngày 2026-09-26; `frame_map_supabase.json` không có trên máy và không nằm trong manifest. `tools/data_manifest.py verify --root .` đã xác nhận đủ kích thước và SHA-256. Manifest không gồm `.env`, cache dịch hoặc file log camera.
- `DB_PATH`, `CONSOLIDATED_VECTORS_PATH`, `TRAFFIC_DB_PATH`, `DATA_ROOT`, `HOST`, `PORT`, `CORS_ORIGINS`, `AGY_PATH`, `AGY_PREWARM_ON_STARTUP`, `MCP_HOST/PORT/API_KEY`, `SUPABASE_URL/KEY` và `DRES_API_BASE_URL` được cấu hình qua `.env`. DRES có thể dùng `DRES_USERNAME/PASSWORD` trên server khi operator chủ động bấm lấy session từ `.env` trên cùng origin localhost.
- Frontend dùng origin hiện tại, MCP đọc `PORT` cấu hình. Health truy vấn SQLite thật, báo tổng frame, vector/model đã nạp và các mode sẵn sàng; readiness không kiểm tra tình trạng DRES hoặc dịch vụ ảnh ngoài.
- Các số liệu artifact trong tài liệu cũ là quan sát tại thời điểm thử, không phải hằng số giao thức. Không cần đọc/sửa file nhị phân để dịch UI.

## API và dữ liệu phải giữ nguyên khi dịch UI

| Nhóm | Endpoint/giá trị |
|---|---|
| Tìm kiếm | `POST /api/v1/search` với `mode=smart/semantic/ocr/asr`; `top_k` mặc định 50 cho tìm kiếm văn bản, ảnh, ảnh tương tự và tìm kiếm tổng hợp. Hai bộ chọn kết quả khởi động ở 50; số đã chọn trước đây không còn ghi đè mặc định sau khi tải lại UI. |
| Camera giao thông | `GET /api/v1/traffic/filters`, `POST /api/v1/traffic/search`; lọc camera/video, lớp, màu, hướng, trạng thái, loại sự kiện, khoảng giây và ngưỡng confidence/severity. Kết quả ghép frame gần thời điểm preview từ main index; UI có tab camera riêng. Thiếu camera DB trả 503. |
| Kiểm chứng frame | `GET /api/v1/search/context` (mặc định 50 frame; khi `surrounding=true`, backend và UI sắp theo khoảng cách tới `frame_idx`, hòa thì chỉ số nhỏ hơn đứng trước), `/search/interval`, `/video/{video_id}/frames`, `/filmstrip`, `/convert_time`, `/video/{video_id}`, `/drive/proxy/{file_id}`. |
| ASR preview | `GET /api/v1/video/{video_id}/asr?center_time=...&window=...`; chỉ trả segment giao với khoảng xem, giới hạn 500. UI có panel transcript và nhập giọng nói khi trình duyệt hỗ trợ `SpeechRecognition`/`webkitSpeechRecognition`. |
| Chat | `POST /api/v1/chat` trả SSE; `[TOOL]`, `[ERROR]`, `[DONE]` là marker protocol. |
| DRES | `POST /api/v1/submission/dres/export` chỉ serialize/validate cục bộ; `/api/v1/dres/login`, `/login/configured`, `/evaluations`, `/submit` liên hệ DRES. |
| Trạng thái lưu | `KIS_TEXT`, `KIS_VIDEO`, `QA`, `TRAKE`; attempt `prepared`, `submitted`, `accepted`, `rejected`, `outcome_unknown`; khóa `vrs_submission_v2`. |
| Payload | `answerSets`, `answers`, `mediaItemName`, `start`, `end`, `text`; tiền tố `QA-...`, `TR-...`; `video_id`, `frame_idx`, `pts_time`, `frame_ids`. |

Chỉ dịch câu hiển thị cho người dùng. Giữ nguyên enum, DOM ID, tên hàm/biến, route, khóa JSON/localStorage, marker SSE, mode tìm kiếm và tiền tố payload. Nếu dịch lỗi backend, dùng lớp hiển thị có kiểm soát; không thay thế chuỗi tiếng Anh theo regex trên payload. HTTP `2xx` mới là **đã gửi**, không có nghĩa **được chấp nhận**. Timeout/5xx sau POST là **chưa rõ kết quả**; cần kiểm tra DRES trước khi gửi lại vì request trước có thể đã được ghi nhận.

## UI hiện tại và phạm vi Việt hóa

Giao diện là một trang, chưa có framework i18n. HTML khai báo `<html lang="vi">`; title/header hiển thị “Hệ thống tìm kiếm video”. Tên hiển thị không kèm số phiên bản; API version không đổi.

1. **Header và câu đang thi:** trạng thái, nút mở Submission Builder, loại câu (giữ tên tiếng Anh trong cả hai menu: `Textual KIS`/`Video KIS` và `KIS (Text / Video)`), timer, mô tả ban đầu, clue, lịch sử và xác nhận reset.
2. **Tìm kiếm:** tab văn bản/ảnh/đổi thời gian/context/**camera giao thông**; giữ nguyên nhãn mode tiếng Anh `Smart Hybrid (Semantic + ASR)` (mặc định), `Semantic AI (CLIP only)`, `OCR (Exact Text)`, `ASR Transcript Search` theo yêu cầu người dùng. Tab camera tải các bộ lọc từ DB và trả track/event kèm frame gần thời điểm preview. Bộ lọc Video ID chỉ có ở tìm kiếm văn bản, tìm kiếm ảnh áp dụng trên toàn bộ dữ liệu. Đổi thời gian sang frame dùng thời gian và FPS nhập trực tiếp, không cần Video ID; kết quả nằm giữa hàng và nút chuyển đổi ở mép phải. Thông báo kết quả dài có thể xuống dòng trong cột riêng; telemetry API/ảnh giữ cùng hàng ở màn hình rộng. Số lượng, upload/drop/paste, trạng thái đang tìm, rỗng, lỗi và số kết quả bằng tiếng Việt. Form khoảng thời gian còn trong HTML nhưng không có tab mở.
3. **Kết quả/preview:** card, ghim/loại/khôi phục, shortlist, so sánh, gán event TRAKE, timestamp/frame/độ tương đồng, ảnh lỗi, filmstrip, bounding box, iframe, transcript ASR quanh frame và nhãn trợ năng. Filmstrip căn giữa frame ngay khi mở; nút trái/phải vẫn cuộn mượt, còn thao tác căn giữa không được kích hoạt nạp liên tiếp nhiều trang. Khi trang trước/sau không thêm frame mới, ngừng gọi tiếp ở đầu/cuối video.
4. **Submission Builder:** tạo/đổi/chọn/xóa query, thêm/sắp xếp dòng, nhập video/frame/answer/dãy TRAKE, lỗi tại trường, xuất ZIP và mở review DRES.
5. **DRES review:** summary/evidence/JSON, session, evaluation `ACTIVE`, submit, lịch sử attempt, cảnh báo payload trùng nhưng vẫn cho gửi lại, trạng thái Prepared/Sent/Accepted/Rejected/unknown, xác nhận gửi và lỗi mạng. Vùng này ưu tiên cao về độ chính xác ngữ nghĩa.

### Cập nhật luồng gửi trùng DRES (2026-09-25)

- Gửi lại cùng `query_id` và payload hợp lệ **được phép**. Backend không giữ fingerprint để chặn request và không trả HTTP 409 do duplicate; mỗi lần POST hợp lệ được chuyển tiếp tới DRES. Request sai schema vẫn bị validator local từ chối.
- UI so fingerprint với lịch sử gửi cùng query. Nếu thấy payload đã từng gửi, hiện thông báo cảnh báo rằng vẫn có thể gửi lại và lần gửi mới có thể được tính là một attempt khác. Cảnh báo không vô hiệu hóa nút. Nút chỉ khóa trong lúc request đang chạy hoặc khi thiếu session/evaluation/payload hợp lệ.
- Sửa payload tạo fingerprint khác và vẫn gửi được. Nếu sửa rồi khôi phục payload cũ, cảnh báo cũ hiện lại; gửi vẫn được phép.
- Mock/local verification sau thay đổi: `python -m unittest tools.dres_contract_checks` **15/15**, `python tools/benchmark_dres_submission.py` **16/16**, `.venv\\Scripts\\python.exe tools\\benchmark_dres_operator.py` **9/9**, frontend inline scripts **2/2** qua `node --check`, `git diff --check` sạch. Chưa gửi DRES thật.
- Ghi chú port 8000 chưa restart là trạng thái lịch sử ngày 2026-09-25; bản 2026-09-26 đã được khởi chạy riêng và dùng để smoke UI.

### Màu và thông báo trong Lịch sử nộp bài

- HTTP 200 có verdict `CORRECT`/`WRONG` hiển thị lần lượt **Đúng** màu xanh / **Sai** màu đỏ. HTTP 202 không có verdict hiển thị là đã gửi, chưa có kết luận.
- HTTP 412 hiển thị màu vàng: “Bạn vừa nộp trùng kết quả với lần nộp trước, hoặc thời gian làm bài của task đã hết.”
- HTTP 401 hiển thị màu vàng: “Session ID của bạn đã hết hạn, cần đăng nhập lại.” HTTP 404 hiển thị màu vàng: “Sai Evaluation ID.”
- Backend chuyển tiếp status 401/404 để UI phân loại; mock contract kiểm tra giữ nguyên hai mã này. Không suy luận đúng/sai chỉ từ HTTP 200 nếu response không có verdict.
- Reverification: route contract **15/15** (thêm xác nhận 401/404 được chuyển tiếp), serializer **16/16**, inline JavaScript **2/2** cú pháp hợp lệ.
6. **AI Assistant:** lời chào, prompt nhanh, gửi/dừng, trạng thái stream, Markdown và card gợi ý. Câu trả lời tự do của model và dữ liệu OCR/ASR không thuộc chuỗi UI cố định cần dịch.

Các thuật ngữ còn tiếng Anh như `Video ID`, `DRES`, `evaluation`, `frame ID`, `OCR`, `ASR`, `AI`, `API`, `JSON`, `ZIP` được giữ theo glossary vì là tên kỹ thuật hoặc giá trị cần đối chiếu. Nội dung người dùng nhập, kết quả OCR/ASR và câu trả lời tự do của trợ lý AI vẫn giữ nguyên nguồn gốc.

## Tình trạng và giới hạn xác minh

- **Kiểm tra build L/M/N/S 2026-09-26:** preflight trên `PORT=8004` 0 lỗi chặn/1 cảnh báo thiếu model dịch offline, manifest SHA-256 pass; dữ liệu DB/vector/ASR/metadata/camera/overlay pass. Test traffic/R2/ASR thêm 12/12, DRES contract 17/17, serializer 16/16, operator 9/9 (trước thay đổi), timing 6/6, chat workspace/timeout/hủy 10/10 (trước thay đổi), database config 2/2, runtime paths 2/2 và MCP HTTP (health, auth 401, đủ 10 tool, probe ảnh) pass. Startup thử độc lập `AGY_PREWARM_ON_STARTUP=false`/`true`: cả hai health ready; false không tạo Agy process trước chat, true prewarm flash/pro trong dưới 60 giây theo poll; semantic query khi warm trả 3 kết quả/382 ms. Working set lấy mẫu Python 1,84–1,85 GB và Agy khoảng 139/143 MB mỗi process; không đo peak RAM. Cập nhật 2026-09-26: bỏ deadline 120 giây khỏi route chat; mock chat/cancel pass 10 check. DRES KIS/Q&A export vẫn ưu tiên PTS nguồn, nhưng nếu frame chưa có trong index hoặc không có PTS thì ước lượng từ FPS cấu hình (mặc định 25) để cho phép tiếp tục nộp; UI cảnh báo frame chưa xác minh và mốc thời gian ước tính. Operator export benchmark sau thay đổi pass 10/10. Không gửi Assistant live hoặc DRES thật trong lượt sửa này. R2: mở được 4/4 ảnh mẫu L/M/N/S ở 512×288; Drive metadata cho 4/4, nhưng URL preview còn trạng thái loading và một file S báo lỗi tải, nên video playback/fallback chưa đạt. Browser lọc N001 trả 50 kết quả, ảnh preview `N001_V003/7750` từ R2 tải được 512 px; filmstrip sau sửa chỉ dựng 40 frame và giữ đúng frame active. Frame biên `N001_V001/0` hiển thị 20 thumbnail. Benchmark offline 57 case L cũ trên corpus mới: hybrid 5/57 case, R@50 6/63, p95 5,27 giây; semantic 1/57, ASR 6/57, OCR 0/57. Đây là tín hiệu chưa đạt gate accuracy/latency, xem `docs/plan.md`. Port 8000 do một process Python khác sử dụng (health ready); không dừng process này. Chưa chạy Assistant live hoặc DRES thi.
- Rerun `tools/benchmark.py --top-k 50 --tolerance-seconds 150` cache-only (direct `SQLiteSearchEngine.search`, semantic): 1/57 case, R@50 2/63, p95 1,416 ms; QA location 1/16 nhưng answer evidence 0/16, TRAKE 0/2. 57/57 video nhãn và frame mục tiêu đều nằm trong DB/dải frame. Không gộp metric này với phép benchmark semantic/OCR/ASR/hybrid khác; cả hai chỉ ra accuracy cần xử lý.
- Sau khi người dùng cho phép đúng một case Assistant live, lấy top-1 semantic local `L25_V085/18951/632.365s` cho `query-p3-1-kis`. Agy CLI trả `Authentication required`; không có câu trả lời/MCP tool call và không ghi nhận latency hay accuracy. Người dùng yêu cầu bỏ qua Agy trong terminal Codex vì không gọi được; không thử lại CLI.

- Workspace câu thi, timer, lưu nháp, shortlist, so sánh, TRAKE event mapping, validator tại trường, review payload và kết nối DRES đã có. Diễn tập local cho bốn dạng được ghi trong plan/changelog; chưa đủ xác nhận đáp án đúng hoặc hoàn thành trong deadline ngày thi.
- Serializer/contract DRES và vài luồng UI đã thử offline. Chưa có bằng chứng login/list/submit thật với evaluation do Ban tổ chức cấp; `start == end` của KIS và ý nghĩa response DRES cần xác nhận trong buổi tập huấn.
- Lỗi từ FastAPI/Pydantic/DRES có thể trở về qua `detail` tiếng Anh. Frontend ánh xạ các lỗi phổ biến của search, frame, validation và DRES sang câu tiếng Việt; lỗi chưa biết vẫn hiện kèm chi tiết máy chủ để hỗ trợ chẩn đoán.
- Form UI không còn lối vào, nhãn version chưa thống nhất và API base hard-code là việc riêng; không để chúng làm lệch phạm vi dịch chữ.
- Kiểm tra cú pháp 5 script inline bằng `node --check`, DRES serializer 16/16, DRES API/client contract 14/14, operator export/UI 9/9 và operator search 4/4 đã đạt. UI local ở viewport 811 px xác nhận cây trợ năng, Tab/Shift+Tab, nhập Unicode tiếng Việt, alert Context lỗi định dạng và kết quả Context rỗng; header đã có bố cục 2 hàng dưới breakpoint 640 px. Chưa kiểm tra trực tiếp viewport dưới 640 px hoặc IME composition; chưa gửi DRES thật.

## Khởi chạy và quy tắc cập nhật

Trên Windows với Python 3.12 x64, cài `requirements.txt`, chép `.env.example` thành `.env`, đặt dữ liệu cần thiết ở root, chạy `python tools/preflight.py`, sau đó `python tools/run_server.py`. Hai script định vị project theo chính file nên có thể chạy bằng đường dẫn tuyệt đối từ thư mục khác. Mặc định backend bind loopback; `.env` có thể ghi đè giá trị này. Health kiểm tra DB queryable, số frame, vector và model đã nạp; HTTP 200 một mình không đồng nghĩa semantic/image search sẵn sàng. Chatbot cần CLI `agy` và MCP `video-researcher` trỏ tới `mcp_server.py`. Chat POST nhận dạng câu `KIS_TEXT`, `KIS_VIDEO`, `QA`, `TRAKE`, mô tả, clue, thời gian còn lại và tối đa 20 frame ghim. `POST /api/v1/frames/validate` chỉ trả Video ID/Frame ID khớp chính xác index kèm PTS nguồn; UI chỉ tạo thẻ Assistant từ các frame đã xác minh. Dùng payload giả và mock/contract checks; không gửi DRES thật để thử bản dịch.

Khi đổi kiến trúc, API, dữ liệu, trạng thái UI hoặc workflow DRES, sửa trực tiếp file này. Cập nhật tiến độ cài đặt và tối ưu trên máy từng thành viên ở `docs/plan.md`, kết quả kiểm thử ở `docs/TEST_PLAN.md`. Luôn phân biệt **đã triển khai**, **đã thử cục bộ** và **đã xác nhận bằng DRES thật**.
