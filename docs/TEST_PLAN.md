# Kế hoạch kiểm thử toàn bộ dự án Vision

**Ngày lập:** 2026-09-25. **Môi trường:** dữ liệu local, cấu hình DRES trong `.env`; backend local đã được dùng trên port riêng và dừng sau smoke. Kế hoạch này bao phủ runtime, giao diện, dữ liệu, trợ lý/MCP và đường đi nộp DRES. DRES dùng mock cho contract và đã có một POST duy nhất lên evaluation ACTIVE tên `AIC2026 - Textual KIS Test 2` theo yêu cầu người dùng; không POST lên evaluation thi. Chỉ tiếp tục DRES live khi có câu hỏi và đáp án mẫu đã xác minh cho test evaluation.

## 1. Phạm vi và nguyên tắc

- **Nguồn cần đối chiếu:** `README.md`, `requirements.txt`, `.env.example`, `frontend/index.html`, `src/*.py`, `mcp_server.py`, các script `tools/*.py`, `docs/DRES_OPERATOR_CHECKLIST.md` và `docs/plan.md`. Kiểm tra API thực tế qua `/openapi.json`; không coi tên test hoặc tài liệu cũ là contract nếu code đã đổi.
- **Dữ liệu:** giữ nguyên các file index, vector, metadata, FPS và cache gốc. Dùng query ID có tiền tố `TEST-`, trình duyệt profile riêng cho diễn tập `localStorage`, ảnh mẫu nhỏ và stub/mock cho lỗi mạng, Supabase, Drive, Agy, DRES. Không in `.env`, password hoặc session ID vào báo cáo.
- **Phân lớp:** (1) kiểm tra tĩnh/unit/contract, (2) API integration trên server đang chạy, (3) UI end-to-end với bốn loại câu, (4) diễn tập operator theo thời hạn cuộc thi bằng đồng hồ bên ngoài ứng dụng nếu cần, (5) DRES thật chỉ khi có evaluation test. Ứng dụng không có bộ đếm ngược. Mỗi lỗi lưu bước tái hiện, input đã che bí mật, expected/actual, HTTP status, thời gian, ảnh hoặc trace và commit/runtime được thử.
- Những ghi nhận timer trong nhật ký kiểm thử cũ mô tả phiên bản trước khi gỡ tính năng; ứng dụng hiện tại không hiển thị hoặc chạy đồng hồ đếm ngược.
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
| UI | `frontend/index.html` | Bốn tab, kết quả/card, preview/filmstrip, compare, workspace, lưu nháp, phím/IME, viewport hẹp, ngôn ngữ/trợ năng; xác nhận không có điều khiển ghim frame hoặc đồng hồ đếm ngược | Không mất nháp/answer; focus và thông báo rõ; dữ liệu không tràn modal. |
| EXPORT | `dres_submission.py`, `/submission/dres/export` | KIS/QA/TRAKE hợp lệ và sai; đúng một answer; PTS giây → ms; video không extension; frame thiếu/âm/trùng/đảo; Q&A rỗng; payload sau sửa draft; giao diện không còn chức năng tạo `submission.zip` | JSON đúng contract, validator từ chối input sai; tải JSON đã kiểm tra chỉ lưu file, không tạo trạng thái đã gửi. |
| DRES | `dres_client.py`, `dres_api.py`, UI modal | Login, session cookie fallback, list ACTIVE, chọn evaluation, POST submit mock và nhánh response/lỗi/trùng; nút tự nộp với 0/1/nhiều evaluation; kết quả gửi hiển thị query/evaluation/HTTP/verdict | Tự nộp chỉ khi có đúng một evaluation; 0 hoặc nhiều evaluation báo rõ và không gọi submit; không suy `Accepted` chỉ từ HTTP 2xx nếu DRES chưa có verdict. |
| OPS | `DRES_OPERATOR_CHECKLIST.md`, `tools/*` | Kịch bản 4 dạng đúng deadline, nguồn bằng chứng, readiness, đo click/thời gian và đối chiếu câu trả lời | Operator đọc được trạng thái chuẩn bị/gửi/verdict; hoàn thành từng bài trong 4/5 phút với đáp án đã kiểm chứng. |

## 3. Dữ liệu test và thứ tự chạy

### Gate cài đặt/preflight (2026-09-25)

- `tools/preflight.py` chạy được bằng Python 3.12.5 x64; dependency import được và `pip check` không có lỗi; SQLite schema/read-only query qua, có `177,321` frame và sample chứa Video ID/Frame ID/PTS; ma trận vector `(177321, 512)` float32 đọc bằng memory map.
- Cấu hình `.env` cục bộ đã đặt `HOST=127.0.0.1`. Preflight xác nhận OpenCLIP checkpoint trong Hugging Face cache đúng repo `timm/vit_base_patch32_clip_224.openai`. Baseline log có QuickGELU mismatch; model variant khớp tag đã so trên p2/p3, MRR tăng mà R@50 không giảm ở cửa sổ rộng. Sau đổi default, server trên port 8001 load QuickGELU không còn mismatch; health, semantic, context và KIS export đều pass. Port 8000 đang có Python listener nên không dừng. Model dịch offline thiếu nhưng là tùy chọn.
- `tools/data_manifest.py create` và `verify` chạy thành công trên dữ liệu local hiện có. `tools/run_server.py` định vị project từ đường dẫn script; chưa khởi chạy server qua script từ một thư mục làm việc khác. Nghiệm thu ba máy còn lại được bỏ khỏi phạm vi theo quyết định 2026-09-25.
- Đây là kiểm tra một máy; không suy ra baseline hiệu năng, accuracy hoặc mức RAM tối thiểu của đội.
- Smoke qua `tools/run_server.py`: health trả `healthy`, `search_ready=true`, 177,321 frame và đủ 5 mode; semantic query trả 3 candidate; context trả 5 frame; KIS export trả payload với `start=end=993240` ms từ PTS index. `python -m unittest tools.dres_contract_checks` đạt 15/15. Không gửi POST DRES thật; smoke query chỉ xác nhận đường đi kỹ thuật, không chấm độ chính xác.
- Retrieval baseline có nhãn sơ bộ: xem [`docs/ACCURACY_BASELINE_2026-09-25.md`](ACCURACY_BASELINE_2026-09-25.md). Đã chạy semantic exact/5 s; semantic/OCR/ASR/hybrid ở cửa sổ 150 s chỉ để chẩn đoán; ASR/hybrid thêm ở 5 s. Không bật dịch online, tolerance chưa được BTC xác nhận, không thay đổi thuật toán từ các số này.
- Tách hồi cứu p2/p3 theo ID rồi thử sentence split: `tools/benchmark_sentence_fusion.py` cho R@50 0/30 trên p2 và 0/33 trên p3 ở cả variant hiện tại lẫn candidate; latency p50 tăng nên candidate bị loại. p3 đã được xem qua trong thí nghiệm này và QuickGELU, không coi là holdout sạch cho thử nghiệm sau.
- QuickGELU comparison: `tools/benchmark.py --id-prefix query-p2-` và `query-p3-` với `CLIP_MODEL_NAME=ViT-B-32-quickgelu`, cửa sổ 150 s diagnostic. R@50 giữ nguyên, target rank 3→2 trên p2 và 6→3 trên p3; ở 5 s cả hai model 0 hit. Default đã đổi; API smoke trên port 8001 pass.

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
| D08 | Review KIS point `start == end`, QA `QA-<ANSWER>-<VIDEO_ID>-<TIME_MS>`, TRAKE `TR-<VIDEO_ID>-<FRAME_ID...>` | JSON, thứ tự và đơn vị đúng contract mock. Một payload KIS `start == end` được DRES Test 2 xử lý và chấm (HTTP 200, `WRONG`); chưa suy ra điểm đúng hoặc chấp nhận ở evaluation thi. |

**Cổng DRES live:** URL `https://eventretrieval.one`, credential và danh sách evaluation đã xác thực; một lần submit KIS được ghi ở mục 10. Không submit tiếp cho tới khi đọc được câu hiện tại và xác minh đáp án mẫu tương ứng. Evaluation thi đang tính điểm không dùng cho smoke test.

## 5. Kịch bản UI end-to-end và hiệu năng

| Loại | Chuỗi thao tác | Điểm kiểm chứng |
|---|---|---|
| Textual KIS | Nhập truy vấn → tìm kiếm → compare ứng viên → preview/filmstrip → chọn một frame → review/export | Video ID không extension; ms từ PTS; sai frame/ảnh lỗi/kết quả rỗng xử lý được. |
| Video KIS | Nhập mô tả/phác họa bằng lời → tìm kiếm → kiểm chứng → chốt/export | Không có luồng thu clip bằng thiết bị; không nhầm tải JSON với gửi DRES. |
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
| UI local | Trang khởi động và hiển thị trạng thái healthy; trên hostname `vision.localhost` riêng đã thao tác timer (tính năng cũ) và thêm hint `TEST` để tránh localStorage hiện có. Search báo không kết nối API và trang từ chối reload qua alias; không tính đây là E2E UI pass. `localhost` và `127.0.0.1` có nháp người dùng nên không sửa/refresh chúng. Kiểm tra viewport dưới 640 px chưa xác minh được: browser viewport override không đổi `innerWidth=811`; đã reset override. |
| DRES thật/tích hợp ngoài | Một lần đăng nhập/liệt kê evaluation và POST tới `AIC2026 - Textual KIS Test 2`; HTTP 200, verdict `WRONG`. Xác nhận tích hợp và xử lý point payload, không xác nhận đáp án hiện tại hoặc evaluation chấm điểm. |
| Retrieval quality | Có baseline sơ bộ trên 57 case; kết quả/giới hạn tại `docs/ACCURACY_BASELINE_2026-09-25.md`. Còn thiếu translator offline, nhãn phân loại Textual/Video KIS, Video KIS descriptions và TRAKE coverage rộng; chưa tune/holdout hoặc đo Assistant end-to-end. |

**Kết quả trước cập nhật yêu cầu:** contract `tools.dres_contract_checks` 14/14 và các benchmark nêu trên đã xác minh hành vi chặn duplicate cũ. Theo yêu cầu mới, đã kiểm tra lại hành vi gửi trùng; xem mục 8 để biết kết quả cập nhật. Smoke UI dùng backend local riêng; lần DRES Test 2 trực tiếp được ghi ở mục 10.

## 11. Diễn tập local bốn dạng và độ ổn định 20 phút — 2026-09-25

- Chạy server tại `127.0.0.1:8001` với `AGY_PREWARM_ON_STARTUP=false`; không chạm listener đang có trên port 8000. Health cuối cùng trả `healthy`, database/vector/QuickGELU sẵn sàng, 177,321 keyframe. Dừng server sau diễn tập; port 8001 hiện không còn listener.
- Bài stability chạy 20 phút, mỗi phút gọi `/api/v1/health` và tìm semantic tổng hợp đã warm cache: **20/20** mẫu health healthy, mỗi search trả 10 kết quả, **0 lỗi health/search**. Thời gian search từng mẫu 14–251 ms (trung vị 27 ms; truy vấn warm-cache tổng hợp, không đại diện truy vấn thi). Log xác nhận các request này đều HTTP 200.
- Ghi nhận UI lịch sử trước khi gỡ chức năng ghim: query/đáp án tổng hợp trên `127.0.0.1:8001` và `localhost:8001`; Textual KIS chọn `L26_V292/2945`, Q&A chọn `L23_V021/5583`, TRAKE tải thêm 30 frame từ `L23_V018` và ghim `5730,5847,5850`, Video KIS chọn `L24_V038/6992`. QA/TRAKE nháp còn sau refresh; phiên bản cũ đã được quan sát đếm ngược và hết giờ.
- Export local không gửi DRES: QA cho `QA-red-L23_V021-223320`; KIS cho `L23_V018` tại `229200 ms`; Video KIS cho `L24_V038` tại `233067 ms`; TRAKE cho `TR-L23_V018-5730,5847,5850`. KIS frame giả `L23_V018/99999999` trả 404. Đây là kiểm tra schema, thứ tự và PTS từ index, không xác minh độ đúng nội dung câu hỏi.
- Hạn chế quan sát được: ảnh chỉ tải một phần; server ghi bốn request tới Drive proxy trả HTTP 500 trên hai asset ID khi tải ảnh. Search, context frame, health và local export vẫn thành công. UI review Q&A không tải được Session ID mới nên không hiện payload trong modal. Không thực hiện DRES POST ở lượt này.
- Thử live Assistant→MCP một lần với prompt tổng hợp và `PORT=8001`: Agy ban đầu dừng trước khi gọi MCP vì không thấy phiên đăng nhập và log CLI bị chặn quyền ghi. Người dùng xác nhận lệnh in `READY` chạy thành công trong PowerShell của họ. Lần gọi MCP `inspect_vision_probe` headless đầu bị Agy từ chối do thiếu allow-rule; sau đó gọi được bằng Agy có `--dangerously-skip-permissions` (chỉ yêu cầu probe ảnh tổng hợp) và trả `MCP_OK`. Khi thử gọi retrieval thật qua Agy, auto-review chặn vì thao tác sẽ chuyển metadata kết quả tìm video trong DB cục bộ tới dịch vụ ngoài; không retry hay chuyển dữ liệu đó.
- Đã xóa answer set tổng hợp tạo trong hai origin kiểm thử cùng mô tả, clue, query và answer QA. Không thao tác origin port 8000. Không chạy trên ba máy còn lại theo quyết định phạm vi.

**Trạng thái sau diễn tập lúc ghi nhận:** stability health/search đạt 20 phút; P1 vẫn một phần do ảnh Drive lỗi, chưa nghiệm thu fallback offline, timeout 120 giây và nhánh force-kill. Bài ASGI timeout 120 giây và force-kill giả đã được chạy sau đó, xem mục “Timeout route 120 giây và force-kill escalation”. P4 khi đó vẫn một phần: có smoke tìm/chọn/export cho bốn dạng, nhưng chưa hoàn tất hai lượt độc lập có ground truth, thao tác trong deadline và UI review/export với DRES đăng nhập được. Không đánh giá accuracy qua các query tổng hợp.

### Đo route tìm ảnh cục bộ — 2026-09-25

- `tools/benchmark_image_cache.py --top-k 50 --json`: 2/2 kịch bản pass; ảnh lặp cho cùng thứ tự ID, kết quả top-50 bằng tiền tố top-500. Model/DB load khoảng 7.93 giây; lần direct-engine đầu 558 ms, warm 0.17 ms, truy vấn top-500 487 ms. Probe dùng JPEG màu tổng hợp 64×64, không có giá trị accuracy.
- Gửi 20 JPEG màu tổng hợp khác nhau tới backend warm đang chạy trên `127.0.0.1:8000`, mỗi request `top_k=50`: 20/20 trả 50 kết quả; p50 481 ms, p95 1,359 ms, max 2,595 ms. Health được poll đồng thời mỗi 10 ms: 179/179 trả HTTP 200, p95 84 ms. Đây là phép đo cục bộ cho route HTTP và khả năng event loop tiếp tục xử lý health trong lúc inference ảnh chạy; không gồm cold startup, tải ảnh Drive/R2, upload lớn hoặc chất lượng trên ảnh thật. Server có sẵn trên port 8000 được dùng cho request chỉ đọc.
- Kết luận giới hạn: số đo route ảnh tổng hợp nằm dưới ngưỡng thử nghiệm p95 8 giây trong cấu hình máy hiện tại; chưa chứng minh đường tải ảnh ngoài khỏe. Bốn HTTP 500 Drive ghi nhận ở mục trên và fallback offline vẫn là phần P1 còn mở.

### Dọn tiến trình Agy thật — 2026-09-25

- Chạy `AgySession` với prompt tổng hợp `Reply with exactly READY. Do not call tools, inspect files, or access the network.` và deadline nội bộ ép về 0 giây: nhận SSE timeout, session bị xóa, process Agy kết thúc (exit code 1); danh sách PID có tên Agy/Antigravity không tăng sau khi đóng.
- Chạy lần nữa, hủy stream ngay sau sự kiện `Model Router` (prompt đã được gửi): nhánh hủy gọi `session.close()`, session bị xóa, process thoát (exit code 0), không có PID Agy/Antigravity mới sót lại. Cùng `close()` được gọi bởi chat route khi client hủy; route timeout/hủy với session giả đã pass 2 check trước đó.
- Giới hạn: đây là bài process cleanup trên Agy thật với deadline tức thời/hủy chủ động, không chờ đủ 120 giây và không ép Agy treo quá 5 giây để đi vào nhánh `proc.kill()`. Không đưa query hay metadata video vào prompt.

## Rerun kiểm tra cục bộ — 2026-09-25

- `tools/preflight.py` với `PORT=8001`: **0 lỗi chặn, 1 cảnh báo** (thiếu offline translator); Python/dependency/pip, DB 177,321 row, vectors `(177321,512)`, OpenCLIP QuickGELU, Agy CLI, manifest và port pass. Ghi nhận 74.2 GiB disk free và 2.0 GiB RAM available/15.6 GiB. `pip check`: no broken requirements.
- Retrieval benchmark trên cùng 57 nhãn, local-only, top-k 50, cửa sổ chẩn đoán 150 giây: 4/4 chiến lược hoàn tất, 0 lỗi; kết quả đúng/recall không đổi so lượt trước. Lượt mới p95 semantic/OCR/ASR/hybrid là 1,805/4,621/5,900/3,520 ms; ASR vượt ngưỡng thử 5 giây. Xem bảng repeat ở `docs/ACCURACY_BASELINE_2026-09-25.md`.
- Rerun contracts/mocks: DRES route **15/15**, submission **16/16**, timing **6/6**, operator export **9/9**, operator search **4/4**, TRAKE sequence **3/3**, QA evidence **3/3**, chatbot stream **3/3**, Agy result stream **3/3**, structured chat workspace **10/10**, database config **2/2**, runtime paths **2/2**, VLM scorecard self-test **23/23** (synthetic). Các bài này không gửi DRES/Agy dữ liệu nhãn.
- Test chính xác handler `handleFrameImageError` từ `frontend/index.html` bằng DOM giả: lỗi ảnh chính lần lượt thử hai URL fallback; khi hết nguồn, ảnh được ẩn và placeholder được hiện. Thẻ kết quả vẫn có thông báo giữ Video ID/frame. Đây là kiểm tra logic fallback cục bộ, không xác minh R2/Drive ngoài mạng.
- Browser UI trên `localhost:8000` với nội dung đã có sẵn trong trang trả 50 kết quả; API 359 ms, ảnh đầu 710 ms, 6/50 ảnh hiển thị. Kết quả xác nhận luồng thật trong trình duyệt nhưng chưa đại diện độ sẵn sàng dịch vụ ảnh. Quan sát thấy telemetry ảnh không kết thúc đúng khi các URL đều lỗi; sửa để đếm riêng ảnh hiển thị và ảnh hết fallback, báo hoàn tất sau khi mọi ảnh có kết quả cuối. Kiểm tra trên mã nguồn mới: 2 script inline parse được; DOM giả thử hai fallback và lỗi cuối phát đúng một sự kiện; callback telemetry đếm một ảnh thành công và một lỗi cuối đúng một lần, nhãn hiển thị 1/2.
- DRES live: `POST /api/v1/dres/login` trên backend local trả HTTP 200/session; `POST /api/v1/dres/evaluations` trả HTTP 200 và 5 evaluation ACTIVE. UI review dùng cấu hình đăng nhập thành công, hiển thị evidence của frame đã chọn, PTS và JSON payload; không chọn evaluation, không gọi submit. Session ID không ghi vào báo cáo và được giữ trong bộ nhớ phiên trang.
- Kiểm tra dữ liệu lưu phía trình duyệt bằng Node trên mã nguồn hiện tại: **5/5** lời gọi `localStorage.setItem` ghi `appState`; không có luồng copy DRES session ID vào `appState`/localStorage. Session chat dùng `sessionStorage` riêng.
- Rerun suite contract/mocks: DRES route **15/15**, submission **16/16**, timing **6/6**, operator export **9/9**, operator search **4/4**, TRAKE sequence **3/3**, QA evidence **3/3**, chatbot stream **3/3**, Agy result stream **3/3**, structured chat workspace **10/10**, database config **2/2**, runtime paths **2/2**, VLM scorecard self-test **23/23** (synthetic). `pip check` sạch.
- Cổng còn mở: clean install không cache; độ sẵn sàng/fallback ảnh dịch vụ ngoài; dịch offline; ASR p95 dưới ngưỡng trong các lượt tải tương đương; holdout mới và nhãn tách Textual/Video KIS; hai diễn tập operator đủ bốn dạng có ground truth trong deadline; kiểm thử DRES submit với câu hỏi/đáp án đã xác minh; live Assistant qua Agy trên metadata video (auto-review chặn truyền kết quả DB ra dịch vụ ngoài); force-kill khi Agy thật bị treo. Ba máy còn lại không thuộc phạm vi.

### Timeout route 120 giây và force-kill escalation — 2026-09-25

- Gọi endpoint chat qua FastAPI ASGI transport với Agy giả cố tình treo, không gửi prompt ra ngoài: HTTP **200**, SSE timeout và `[DONE]` được phát sau **120.0 giây**, `close()` được gọi.
- Gắn process giả không thoát vào `AgySession.close()`: sau 5 giây `kill()` được gọi; process reference, readiness và session-pool entry được dọn. Bài này xác minh nhánh escalation trong mã, không mô phỏng tiến trình Agy thật bị treo.
- Agy thật đã được xác minh riêng ở timeout tức thời và hủy stream; còn thiếu tình huống Agy thật đứng im đủ 120 giây.

## Assistant workspace context và frame verification

- Ghi nhận contract chat lịch sử trước các lần gỡ trường mô tả/gợi ý, timer và frame ghim: request nhận `question_type` (`KIS_TEXT`, `KIS_VIDEO`, `QA`, `TRAKE`); TRAKE luôn dùng route model nặng. Prompt yêu cầu format ứng viên/bằng chứng/độ tin cậy/phần thiếu/thao tác tiếp theo.
- `POST /api/v1/frames/validate` tra chính xác cặp Video ID + Frame ID trong SQLite và trả PTS index. Thẻ ứng viên được trích từ câu trả lời Assistant chỉ render sau khi route xác nhận frame. Frame ghim từng được xác thực trước khi chuyển cho model; trường ghim đã bị xóa khỏi contract hiện tại.
- Smoke server QuickGELU trên port 8001: frame mẫu `L26_V183/5895` xác minh thành công với PTS `235.8`; cặp giả `NO_SUCH_VIDEO/42` bị loại. OpenAPI công bố đủ bốn loại câu; các script inline qua `node --check`, Python compile và DRES contract **15/15** pass.
- `python tools/benchmark_chat_workspace.py`: **10/10 pass** với Agy giả và DB local; xác nhận chuyển context, bỏ pin không hợp lệ, TRAKE/multi-event routing, chặn loại câu ngoài enum, và gọi cleanup khi timeout/hủy. Process thật cũng đã được kiểm tra đóng khi deadline nội bộ ép về 0 và khi hủy stream; bài route ASGI 120 giây và force-kill giả được ghi ở mục trên. Chưa kiểm tra Agy thật đứng im đủ 120 giây.
- `agy --version`/`agy mcp list` xác nhận CLI/MCP cài đặt. Người dùng chạy lệnh `agy --print-timeout 120s --output-format text --print="Reply with exactly READY."` từ PowerShell và nhận `READY`. Agy gọi thành công `video-researcher.inspect_vision_probe` trên ảnh tổng hợp với `--dangerously-skip-permissions`; chỉ yêu cầu tool probe này. Retrieval qua Agy với kết quả tìm từ DB local bị auto-review chặn do gửi metadata sang dịch vụ ngoài, nên không thực hiện. MCP stdio gọi trực tiếp tại máy xác nhận `search_semantic_video`, `search_ocr_video`, `search_asr_video`, `search_video_evidence` đều được đăng ký và không lỗi; ba search gọi backend `/api/v1/search` HTTP 200, evidence gọi `/api/v1/search/all` HTTP 200 và hoàn tất 9.988 giây. Đây là kiểm tra tích hợp MCP→backend trên query tổng hợp, không phải kiểm thử Assistant end-to-end, ground truth hay accuracy. Chưa đo ứng viên đầu tiên/correctness bốn dạng. P3 mới là triển khai một phần; nghiệm thu ba máy còn lại được loại khỏi phạm vi theo quyết định 2026-09-25.

## Kiểm tra lại máy hiện tại sau đăng nhập Agy

- Preflight với `PORT=8001`: **0 lỗi chặn**, DB/vector/OpenCLIP/dependency/manifest/port pass; cảnh báo duy nhất là model dịch offline chưa có. Ghi nhận đĩa trống 83.8 GiB và RAM khả dụng 2.7/15.6 GiB tại thời điểm chạy.
- `tools/benchmark_runtime_paths.py`: **2/2 pass**; `tools/benchmark_database_config.py`: **2/2 pass**; DRES contract: **15/15 pass**.
- Retrieval local-only trên 57 case, top-k 50 và cửa sổ 150 giây chỉ để chẩn đoán: semantic R@50 2/63, OCR 0/63, ASR 7/63, hybrid 8/63. p95 lần chạy được ghi lần lượt 442, 755, 870 và 1,952 ms. Xem `docs/ACCURACY_BASELINE_2026-09-25.md`; không xem dung sai này là luật thi.
- Khởi động Uvicorn trên 8001 với `AGY_PREWARM_ON_STARTUP=false`: log xác nhận hai phiên không prewarm; health healthy, semantic search trả 3 kết quả, frame validator giữ đúng frame `L26_V183/5895` với PTS 235.8 và loại frame giả. Đã dừng server sau smoke.
- Agy auth prompt tối giản trả `READY`, nhưng chưa gửi query benchmark hoặc chạy live Assistant→MCP. Ba máy khác được bỏ khỏi phạm vi theo yêu cầu.
- UI smoke local trên `127.0.0.1:8001` dùng câu và clue tổng hợp (không lấy từ nhãn thi): phiên bản cũ có timer bắt đầu và đếm lùi; Smart Hybrid trả 50 kết quả, API **1,662 ms**, ảnh đầu **2,046 ms**, chỉ **21/50** ảnh tải được. Metadata Video ID/Frame ID/PTS hiển thị; chọn được `L25_V024 / 29337` vào answer set và mở màn hình review. Lúc đó UI-local không lấy được Session ID (502 do egress bị chặn); sau đó xác thực và submit trực tiếp bằng đường mạng được cấp quyền, chi tiết ở mục 10.
- Đã xóa answer set khói thử và clue khói thử. Hộp xác nhận khi dọn phần còn lại bị kẹt trong browser automation; server đã dừng, nên chưa xác nhận việc mô tả/timer bị xóa khỏi localStorage của origin `127.0.0.1:8001`. Không sửa dữ liệu ở origin port 8000. Ảnh 29/50 chưa tải trong smoke, do vậy cần xử lý như nhánh ảnh lỗi khi diễn tập.
- P4 còn thiếu hai lượt diễn tập độc lập, đủ bốn dạng, có ground truth và hoàn thành trong hạn. Stability 20 phút đã đạt ở mục 11; không có kết quả nào được suy rộng sang ba máy đã loại khỏi phạm vi.

## 8. Kiểm tra lại DRES duplicate theo yêu cầu 2026-09-25

- Backend nhận và chuyển tiếp mọi lần POST có payload hợp lệ, kể cả cùng `query_id` và fingerprint; không trả 409 chỉ vì đã gửi trước đó.
- Mock route tests: `python -m unittest tools.dres_contract_checks` — **15/15 pass**. Bao gồm gửi lặp tuần tự, gửi lại sau kết quả chưa rõ, gửi lại sau HTTP 412, payload đã sửa, hai request đồng thời và giữ nguyên HTTP 401/404 từ DRES để UI phân loại; mỗi request hợp lệ đều được chuyển tới mock DRES.
- Serializer contract: `python tools/benchmark_dres_submission.py` — **16/16 pass**.
- Operator export: `.venv\\Scripts\\python.exe tools\\benchmark_dres_operator.py` — **9/9 pass**.
- Frontend inline scripts: **2/2** qua `node --check`; UI bỏ việc vô hiệu hóa nút theo fingerprint và vẫn hiển thị cảnh báo trước payload trùng.
- `git diff --check` sạch. Không gửi request lên evaluation thi; một lần gửi tới test evaluation có verdict `WRONG` và được mô tả ở mục 10.

## 9. Màu và thông báo trạng thái DRES

- HTTP 200 với verdict `CORRECT`/`WRONG` được ghi là Đúng màu xanh / Sai màu đỏ. HTTP 200 không có verdict không được suy luận là đúng.
- HTTP 412 được ghi màu vàng với nội dung trùng kết quả trước đó hoặc hết thời gian task; HTTP 401 màu vàng yêu cầu đăng nhập lại; HTTP 404 màu vàng báo sai Evaluation ID.
- Route mock xác nhận HTTP 401 và 404 được giữ nguyên tới giao diện; contract **15/15** và hai script inline qua `node --check`.

## DRES Builder — tăng/giảm Frame ID

- Nút ▲/▼ cạnh mỗi hàng tăng/giảm Frame ID một đơn vị; với KIS/Q&A chỉ cập nhật frame của hàng đó. Với TRAKE, dịch tất cả frame trong danh sách của hàng cùng một đơn vị để vẫn giữ thứ tự tăng dần.
- Không thay đổi dữ liệu nếu frame đang nhập sai định dạng, phép giảm tạo giá trị âm, hoặc kết quả vượt giới hạn số nguyên an toàn.
- Kiểm tra giao diện thủ công cần xác nhận giá trị hiển thị và payload sau ▲/▼, gồm frame `0`, một frame TRAKE và một dãy TRAKE; kiểm tra này chưa được chạy trong phiên sửa mã.

Kế hoạch toàn hệ thống vẫn còn mở: năm route phụ thuộc ngoài, retrieval ground truth và UI E2E/viewport cần môi trường tương ứng.

## 10. DRES Test 2 — một lần submit theo yêu cầu 2026-09-25

- Đăng nhập trực tiếp vào `https://eventretrieval.one`, liệt kê được bốn evaluation ACTIVE có tên `AIC2026 - Textual KIS Test 2`, `AIC2026 - TRAKE Test 2`, `AIC2026 - Video KIS Test 2`, `AIC2026 - QA Test 2`. Chỉ chọn evaluation Textual KIS Test 2.
- Payload lấy từ frame đã xác minh trong DB local: `L26_V183`, frame ID `5895`, PTS `235.8s`; JSON gửi là `{"answerSets":[{"answers":[{"mediaItemName":"L26_V183","start":"235800","end":"235800"}]}]}`. Không ghi query text, credential hoặc session ID vào báo cáo.
- DRES trả HTTP **200**, verdict **`WRONG`**, mô tả `Submission wrong, try again!`. Điều này xác nhận request được nhận và chấm; không chứng minh payload khớp câu đang hoạt động vì frame được lấy từ nhãn benchmark, chưa đối chiếu với prompt Test 2.
- Không retry và không gửi lên evaluation thi. Để xác minh verdict đúng, cần lấy câu hiện tại từ đúng evaluation Test 2 rồi đối chiếu đáp án có bằng chứng trước khi gửi thêm.

## 7. Tiêu chí đóng kế hoạch test

Mọi hàng P0/P1 trong ma trận có case và bằng chứng pass; contract tự động xanh; 22 route được smoke hoặc có lý do rõ nếu phụ thuộc dịch vụ ngoài; bốn luồng UI hoàn tất trong deadline với ground truth; không mất nháp, lộ bí mật hoặc đánh đồng `prepared/sent/accepted`; hai bất nhất ở mục 6 được giải quyết. Nếu chưa có evaluation test của BTC, ghi DRES live là **chưa kiểm chứng**, giữ cổng này mở thay vì suy từ mock rằng submit thật đã an toàn.
