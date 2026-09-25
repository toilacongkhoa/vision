# Kế hoạch kiểm thử toàn bộ dự án Vision

**Ngày lập:** 2026-09-25. **Môi trường đang có:** backend tại `http://127.0.0.1:8000`, dữ liệu local và cấu hình DRES trong `.env`. Kế hoạch này bao phủ runtime, giao diện, dữ liệu, trợ lý/MCP và đường đi nộp DRES. Các bài DRES ở đây dùng mock hoặc request bị chặn ở validator local; không POST đáp án hợp lệ lên evaluation thật. Chỉ chuyển sang rehearsal DRES thật khi có evaluation tập huấn, đáp án mẫu và quy tắc tính điểm được xác nhận.

## 1. Phạm vi và nguyên tắc

- **Nguồn cần đối chiếu:** `README.md`, `requirements.txt`, `.env.example`, `frontend/index.html`, `src/*.py`, `mcp_server.py`, các script `tools/*.py`, `docs/DRES_OPERATOR_CHECKLIST.md` và `docs/plan.md`. Kiểm tra API thực tế qua `/openapi.json`; không coi tên test hoặc tài liệu cũ là contract nếu code đã đổi.
- **Dữ liệu:** giữ nguyên các file index, vector, metadata, FPS và cache gốc. Dùng query ID có tiền tố `TEST-`, trình duyệt profile riêng cho diễn tập `localStorage`, ảnh mẫu nhỏ và stub/mock cho lỗi mạng, Supabase, Drive, Agy, DRES. Không in `.env`, password hoặc session ID vào báo cáo.
- **Phân lớp:** (1) kiểm tra tĩnh/unit/contract, (2) API integration trên server đang chạy, (3) UI end-to-end với bốn loại câu, (4) diễn tập operator có đồng hồ, (5) DRES thật chỉ khi có evaluation test. Mỗi lỗi lưu bước tái hiện, input đã che bí mật, expected/actual, HTTP status, thời gian, ảnh hoặc trace và commit/runtime được thử.
- **Ưu tiên:** P0 là lỗi có thể nộp sai/trùng, mất đáp án, lộ credential hoặc không tìm được; P1 là sai dữ liệu/thời gian, lỗi luồng chính hoặc quá hạn; P2 là nhánh phụ, hiển thị/trợ năng và hiệu năng ngoài luồng chính.

## 2. Ma trận bao phủ

| Mã | Thành phần và file chính | Trường hợp phải thử | Điều kiện đạt |
|---|---|---|---|
| ENV | `config.py`, `.env.example`, `requirements.txt`, startup `main.py` | Python/dependency, đường dẫn tuyệt đối, file thiếu, restart sau đổi config, health, `/` và `/openapi.json` | Startup rõ lỗi; health phản ánh trạng thái thực, không ghi bí mật; chỉ một backend phục vụ port 8000. |
| DATA | `sqlite_engine.py`, DB/vectors/metadata/FPS | Số vector và metadata khớp; vector ID hợp lệ/vượt biên; video/frame tồn tại và không tồn tại; PTS/FPS; cache; SQLite FTS có/không có | Kết quả có `video_id`, `frame_idx`, `pts_time` đúng nguồn, thứ tự ổn định, không crash khi dữ liệu rỗng. |
| SEARCH | `/api/v1/search`, `/search/all`, `/search/similar`, `/search/image` | `smart`, `semantic`, `ocr`, `asr`; top_k 1/50/200 và ngoài biên; video filter; query rỗng/Unicode; ảnh hợp lệ/hỏng; vector ID sai; kết quả rỗng | Schema, mode, filter, số lượng và xếp hạng đúng; lỗi 4xx thay vì 500 cho input sai; không trộn kết quả giữa request. |
| BROWSE | `/search/context`, `/search/interval`, `/video/{id}`, `/video/{id}/frames`, `/filmstrip`, `/convert_time` | Context hai phía, range đảo chiều, phân trang trước/sau, limit, video thiếu, mốc đầu/cuối, FPS theo map | Frame và timestamp nhất quán; navigation không nhảy video hoặc bỏ sót frame. |
| MEDIA | `supabase_service.py`, `/supabase/*`, `/drive/proxy/*` | Config đủ/thiếu, 404, timeout, lỗi 403/5xx, giới hạn frame, MIME/ảnh hỏng, fallback URL | UI vẫn cho đối chiếu ID/frame/time khi ảnh lỗi; không lộ khóa Supabase hoặc thông tin nhạy cảm. |
| TRANSLATE | `fast_translator.py` | Query Việt/Anh, cache hit/miss, model offline/online fallback, lỗi dịch | Query gốc không mất; semantic dùng bản dịch đúng khi có; lỗi dịch không chặn tìm kiếm. |
| CHAT | `agy_session.py`, `/api/v1/chat`, `mcp_server.py` | Routing flash/pro, tách session, SSE `[TOOL]`/`[ERROR]`/`[DONE]`, timeout/cancel/reconnect, tool search/evidence/grid/sequence, dữ liệu sai | Không lẫn hội thoại; stream kết thúc hoặc báo lỗi rõ; candidate có thể kiểm tra lại bằng API/frame gốc. |
| UI | `frontend/index.html` | Bốn tab, kết quả/card, preview/filmstrip, shortlist/compare, workspace, timer, hint, refresh/reset, lưu nháp, phím/IME, viewport hẹp, ngôn ngữ/trợ năng | Không mất nháp/answer; focus và thông báo rõ; dữ liệu không tràn modal; timer đúng 4/5 phút. |
| EXPORT | `dres_submission.py`, `/submission/dres/export` | KIS/QA/TRAKE hợp lệ và sai; đúng một answer; PTS giây → ms; video không extension; frame thiếu/âm/trùng/đảo; Q&A rỗng; payload sau sửa draft | JSON đúng contract, validator từ chối input sai; download chỉ lưu file, không tạo trạng thái đã gửi. |
| DRES | `dres_client.py`, `dres_api.py`, UI modal | Login, session cookie fallback, list ACTIVE, chọn evaluation, POST submit mock và nhánh response/lỗi/trùng | Xem mục 4; không suy `Accepted` chỉ từ HTTP 2xx nếu DRES chưa có verdict. |
| OPS | `DRES_OPERATOR_CHECKLIST.md`, `tools/*` | Kịch bản 4 dạng đúng deadline, nguồn bằng chứng, readiness, đo click/thời gian và đối chiếu câu trả lời | Operator đọc được trạng thái chuẩn bị/gửi/verdict; hoàn thành từng bài trong 4/5 phút với đáp án đã kiểm chứng. |

## 3. Dữ liệu test và thứ tự chạy

1. **Ghi baseline:** `git status --short`, commit hiện tại, phiên bản Python, `/api/v1/health`, danh sách path trong `/openapi.json`, số vector/row và trạng thái Agy. Không đưa credential vào log. Server đang chạy thì dùng server đó; chỉ restart nếu code/config thay đổi và cần so phiên bản.
2. **Contract nhanh:** `\.venv\Scripts\python.exe -m unittest tools.dres_contract_checks`; `\.venv\Scripts\python.exe tools/benchmark_dres_submission.py`; `\.venv\Scripts\python.exe tools/benchmark_dres_operator.py`; `\.venv\Scripts\python.exe tools/benchmark_operator_search.py`; thêm `benchmark_trake_sequence.py`, `benchmark_qa_evidence.py`, `benchmark_dres_timing.py`, `benchmark_chatbot_stream.py`, `benchmark_chatbot_sessions.py`, `benchmark_agy_result_stream.py`, `benchmark_database_config.py`, `benchmark_runtime_paths.py` cho các khu vực tương ứng. Script benchmark hiệu năng/relevance (`benchmark.py`, `benchmark_multimodal.py`, `benchmark_chatbot.py`, `benchmark_vlm_selection.py`) chạy riêng với dataset/ground truth cố định; ghi cấu hình, seed, thời gian và kết quả, không lấy một smoke test làm chất lượng retrieval.
3. **API local:** thử `/`, health, video/context/filmstrip/convert_time; POST search ở bốn mode và image/similar; POST export KIS/QA/TRAKE; thử input không hợp lệ và status 4xx. So `pts_time` frame nguồn với `start/end` hoặc text đã xuất. Chạy trên `127.0.0.1:8000`, timeout ngắn, giới hạn `top_k` nhỏ để tránh tải lớn.
4. **UI:** dùng profile thử riêng, tạo câu và query `TEST-...`; làm các kịch bản ở mục 5. Sau mỗi thao tác sửa nháp, refresh và kiểm tra `localStorage`/UI. Tải JSON vào thư mục thử, đối chiếu nội dung với JSON review. Không dùng nút gửi thật.
5. **Mock DRES:** dùng `httpx.MockTransport`/ASGI như `tools/dres_contract_checks.py` để kiểm tra chính xác URL, method, query `session`, body, trạng thái UI/backend và số lần upstream được gọi. Không cần server BTC hoặc credential thật.

## 4. Ma trận POST DRES chi tiết

| Mã | Kịch bản | Expected |
|---|---|---|
| D01 | Login POST `/api/v1/dres/login`; mock `POST /api/v2/login` trả `sessionId` | Session chỉ trong RAM trang; body có username/password, không lộ password trong response/log. |
| D02 | Login trả cookie và `/api/v2/user/session`; configured login từ localhost same-origin; cross-origin/non-loopback | Fallback lấy session; configured chỉ hoạt động đúng origin local; trường hợp khác 403 và không gọi upstream. |
| D03 | POST `/api/v1/dres/evaluations`; mock list dạng array và `{evaluations:[...]}` | Chỉ evaluation `ACTIVE` có ID được chọn; rỗng/lỗi/mất session hiển thị rõ. |
| D04 | POST `/api/v1/dres/submit` với payload KIS/QA/TRAKE, mock upstream 200 `CORRECT`, 200 `WRONG`, 202 chưa có verdict, `INDETERMINATE` | Đúng `POST /api/v2/submit/{evaluationID}?session=...`; `CORRECT` accepted, `WRONG` rejected, 202 sent/chưa verdict, verdict khác không tự suy đoán. |
| D05 | Request sai schema, thiếu answer, sai query type/evaluation ID, timestamp/frame sai | Local 422 trước upstream; giữ dữ liệu để operator sửa; không tạo attempt đã gửi. |
| D06 | Mock 401/403/412, 408/5xx, timeout hoặc mất kết nối sau POST | 401/403 báo lỗi auth; 412 rejected; 408/5xx/timeout ghi outcome unknown và hướng dẫn kiểm tra DRES trước khi thử lại. |
| D07 | Bấm gửi hai lần, request đồng thời, refresh, server restart; gửi cùng fingerprint rồi payload đã sửa | Cùng payload luôn được chuyển tiếp lên DRES; UI cảnh báo nếu fingerprint/query đã có trong lịch sử nhưng vẫn cho phép gửi. Kiểm tra mỗi lần bấm tạo một request upstream và cảnh báo giữ nguyên với payload đã sửa lại đúng fingerprint cũ. |
| D08 | Review KIS point `start == end`, QA `QA-<ANSWER>-<VIDEO_ID>-<TIME_MS>`, TRAKE `TR-<VIDEO_ID>-<FRAME_ID...>` | JSON, thứ tự và đơn vị đúng contract mock. Việc DRES thật chấp nhận `start == end` còn cần rehearsal của BTC. |

**Cổng cho DRES thật (chưa chạy):** xác nhận URL BTC, credential thử, evaluation ID dành cho tập huấn, loại câu và đáp án mẫu được phép nộp; chụp trạng thái ACTIVE trước khi gửi; gửi đúng **một** request đã review; ghi HTTP status, body đã ẩn session, verdict và lịch sử; kiểm tra điểm/trạng thái trên DRES; dừng khi response chưa rõ, không tự retry. Evaluation thi đang tính điểm không dùng cho smoke test.

## 5. Kịch bản UI end-to-end và hiệu năng

| Loại | Chuỗi thao tác | Điểm kiểm chứng |
|---|---|---|
| Textual KIS | Bắt đầu 5:00 → mô tả → tìm kiếm → thêm 2 gợi ý → pin/compare ứng viên → preview/filmstrip → chọn một frame → review/export | Gợi ý và shortlist giữ sau refresh; video ID không extension; ms từ PTS; sai frame/ảnh lỗi/kết quả rỗng xử lý được. |
| Video KIS | Bắt đầu 4:00 → mô tả/phác họa bằng lời → tìm kiếm → kiểm chứng → chốt/export | Không có luồng thu clip bằng thiết bị; timer và loại câu đúng; không nhầm tải JSON với gửi DRES. |
| Q&A | Câu hỏi cố định từ đầu → thêm mô tả → tìm → xác minh thời điểm **và** câu trả lời → sửa answer → review/export | Answer rỗng bị chặn; Unicode/dấu/gạch nối được giữ; payload `QA-...-ms`; sửa draft làm review cũ hết hiệu lực. |
| TRAKE | Nhập toàn bộ event theo thứ tự → gán một semantic keyframe/event trong cùng video → thử thiếu/trùng/đảo → sửa → review/export | Thứ tự tăng đúng, một video, đủ event; không nhầm `frame_idx`, frame ID và timestamp; sequence giữ sau refresh. |

Mỗi loại chạy thêm ít nhất một nhánh: không có kết quả, ảnh/Drive lỗi, API chậm/lỗi, ứng viên sai, nhập Unicode bằng IME, bàn phím Tab/Shift+Tab/Enter/Escape, reset có xác nhận, viewport desktop và dưới 640 px. Ghi thời gian từ nhận đề đến candidate đúng đầu tiên, đáp án hợp lệ, và trạng thái gửi mock; số click/phím, lỗi validation, mất nháp và thao tác nhầm. Đạt khi operator hoàn thành trong hạn 4/5 phút với dữ liệu có ground truth và không tạo payload sai/trùng ngoài ý muốn.

## 6. Baseline đã quan sát ngày 2026-09-25

- `GET /api/v1/health`: HTTP 200, `healthy`, database/vector hiện diện, `total_keyframes=177321`; `/` trả HTML 200, `/openapi.json` 200 với 22 route đang công bố.
- Video `L26_V246`: metadata, context và filmstrip local 200; time conversion 200. `/api/v1/search` mode ASR với `wooden spoon` trả 3 kết quả, OCR trả 0 kết quả hợp lệ.
- POST local `/api/v1/submission/dres/export`: KIS `L26_V246` frame `4495` → `179800 ms`; QA cùng frame → `QA-test answer-L26_V246-179800`; TRAKE mẫu `10,20,30` → `TR-L26_V246-10,20,30`. POST `/api/v1/dres/submit` với envelope sai trả 422 tại local validator; không gửi DRES thật.
- `tools.dres_contract_checks`: 14/14 pass; `benchmark_dres_submission.py`: 16/16 pass; `benchmark_operator_search.py`: 4/4 pass.
- **Baseline trước thay đổi:** `benchmark_dres_operator.py` 8/9 vì export dùng FPS fallback cho frame thiếu; contract DRES cho phép gửi lại payload trùng.

### Kết quả thực thi ngày 2026-09-25

| Nhóm | Kết quả |
|---|---|
| DRES route/client mock | `tools.dres_contract_checks`: 14/14 pass; gồm login/session cookie, lọc ACTIVE, payload POST, lỗi, cross-origin, timeout/unknown và retry. |
| Serializer/operator/search | `benchmark_dres_submission.py` 16/16; `benchmark_operator_search.py` 4/4; `benchmark_dres_operator.py` 8/9 (lỗi fallback frame đã nêu ở trên). |
| TRAKE/Q&A/timing | `benchmark_trake_sequence.py` 3/3; `benchmark_qa_evidence.py` 3/3; `benchmark_dres_timing.py` 6/6. |
| Chatbot/Agy mocks | `benchmark_chatbot_stream.py` 3/3; `benchmark_chatbot_sessions.py` 3/3; `benchmark_agy_result_stream.py` 3/3. |
| Database/runtime | `benchmark_database_config.py` 2/2; `benchmark_runtime_paths.py` 2/2, gồm chạy từ thư mục dự án và thư mục ngoài. |
| VLM scorecard | `benchmark_vlm_selection.py --self-test`: 23/23 pass trên dữ liệu tổng hợp; không đo accuracy của VLM. |
| Static/dependencies | 5/5 inline script qua `node --check`; `pip check` không phát hiện dependency lỗi. |
| API local | 17/22 route path đã được gọi: root/health, video metadata, context/range/filmstrip/interval/time, bốn search mode, search all/similar, export KIS/QA/TRAKE, schema validation DRES và từ chối configured login cross-origin đều trả status mong đợi. Chưa gọi 3 route Supabase, Drive proxy và chat/Agy vì cần dịch vụ ngoài hoặc khởi chạy agent. |
| UI local | Trang khởi động và hiển thị trạng thái healthy; trên hostname `vision.localhost` riêng đã thao tác timer và thêm hint `TEST` để tránh localStorage hiện có. Search báo không kết nối API và trang từ chối reload qua alias; không tính đây là E2E UI pass. `localhost` và `127.0.0.1` có nháp người dùng nên không sửa/refresh chúng. Kiểm tra viewport dưới 640 px chưa xác minh được: browser viewport override không đổi `innerWidth=811`; đã reset override. |
| DRES thật/tích hợp ngoài | Không chạy theo lựa chọn hiện có. Mock/local không xác nhận credential, evaluation, verdict, điểm hoặc chấp nhận `start == end` trên máy BTC. |
| Retrieval quality | Chưa chạy `benchmark.py`, `benchmark_multimodal.py` hoặc `benchmark_chatbot.py`: dataset ground truth `answerAndQuestion.jsonl` không có trong workspace. |

**Kết quả trước cập nhật yêu cầu:** contract `tools.dres_contract_checks` 14/14 và các benchmark nêu trên đã xác minh hành vi chặn duplicate cũ. Theo yêu cầu mới, đã kiểm tra lại hành vi gửi trùng; xem mục 8 để biết kết quả cập nhật. Local backend ở port 8000 vẫn là process đã nạp code cũ; thay đổi mới được xác minh bằng ASGI/mock, không gửi DRES thật.

## 8. Kiểm tra lại DRES duplicate theo yêu cầu 2026-09-25

- Backend nhận và chuyển tiếp mọi lần POST có payload hợp lệ, kể cả cùng `query_id` và fingerprint; không trả 409 chỉ vì đã gửi trước đó.
- Mock route tests: `python -m unittest tools.dres_contract_checks` — **15/15 pass**. Bao gồm gửi lặp tuần tự, gửi lại sau kết quả chưa rõ, gửi lại sau HTTP 412, payload đã sửa, hai request đồng thời và giữ nguyên HTTP 401/404 từ DRES để UI phân loại; mỗi request hợp lệ đều được chuyển tới mock DRES.
- Serializer contract: `python tools/benchmark_dres_submission.py` — **16/16 pass**.
- Operator export: `.venv\\Scripts\\python.exe tools\\benchmark_dres_operator.py` — **9/9 pass**.
- Frontend inline scripts: **2/2** qua `node --check`; UI bỏ việc vô hiệu hóa nút theo fingerprint và vẫn hiển thị cảnh báo trước payload trùng.
- `git diff --check` sạch. Không gửi request tới DRES thật; cảnh báo không thể đảm bảo lần thử gửi lại sẽ không bị tính điểm/phạt.

## 9. Màu và thông báo trạng thái DRES

- HTTP 200 với verdict `CORRECT`/`WRONG` được ghi là Đúng màu xanh / Sai màu đỏ. HTTP 200 không có verdict không được suy luận là đúng.
- HTTP 412 được ghi màu vàng với nội dung trùng kết quả trước đó hoặc hết thời gian task; HTTP 401 màu vàng yêu cầu đăng nhập lại; HTTP 404 màu vàng báo sai Evaluation ID.
- Route mock xác nhận HTTP 401 và 404 được giữ nguyên tới giao diện; contract **15/15** và hai script inline qua `node --check`.

Kế hoạch toàn hệ thống vẫn còn mở: năm route phụ thuộc ngoài, retrieval ground truth và UI E2E/viewport cần môi trường tương ứng.

## 7. Tiêu chí đóng kế hoạch test

Mọi hàng P0/P1 trong ma trận có case và bằng chứng pass; contract tự động xanh; 22 route được smoke hoặc có lý do rõ nếu phụ thuộc dịch vụ ngoài; bốn luồng UI hoàn tất trong deadline với ground truth; không mất nháp, lộ bí mật hoặc đánh đồng `prepared/sent/accepted`; hai bất nhất ở mục 6 được giải quyết. Nếu chưa có evaluation test của BTC, ghi DRES live là **chưa kiểm chứng**, giữ cổng này mở thay vì suy từ mock rằng submit thật đã an toàn.
