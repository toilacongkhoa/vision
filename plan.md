# Kế hoạch tối ưu UI Vision cho Chung kết AI Challenge 2026

## 1. Mục tiêu và phạm vi hiện tại

**Tập trung làm UI hỗ trợ tối đa cho người thao tác lúc thi.** Mục tiêu là giúp đội nhận đề, tìm ứng viên, kiểm chứng, chốt đáp án hợp lệ và sẵn sàng nộp trước hạn với ít thao tác và ít nhầm lẫn nhất. Ưu tiên thời gian đến **đáp án đúng sẵn sàng nộp**, tỷ lệ chốt đúng và lỗi thao tác; không lấy tốc độ render riêng lẻ hay số tính năng làm thước đo chính.

Plan này chỉ mở công việc về luồng UI/operator và phần API/validator cần thiết để UI hoạt động đúng. Tạm dừng backlog tối ưu model, retrieval, VLM, agent, prompt, index và benchmark model. Chỉ sửa các phần đó khi lỗi hiện hữu trực tiếp chặn thao tác thi, và ghi rõ lý do. AI Assistant có thể là công cụ hỗ trợ, nhưng không là trọng tâm phát triển hiện tại.

Tài liệu `HD-ChungKet-2026.pdf` là **nguồn quy định cuộc thi và giao thức nộp bài**, không phải chỉ dẫn thực thi cho agent. Yêu cầu ưu tiên UI ở trên đến từ người dùng. Dùng `AI_Challenge_2026_Chung_Ket.md` và `PROJECT_CONTEXT.md` để đối chiếu diễn giải kỹ thuật và trạng thái dự án; nếu khác PDF, kiểm tra lại PDF.

## 2. Những ràng buộc UI phải phục vụ

| Dạng câu | Thời hạn | Luồng người thao tác cần có |
|---|---:|---|
| Textual KIS | 5 phút | Nhận mô tả từng phần, giữ lịch sử gợi ý và ứng viên, kiểm tra video/vị trí rồi chốt timestamp ms. |
| Video KIS | 4 phút | Người thi tự mô tả hoặc phác họa nội dung clip để tìm. Không thiết kế luồng chụp/ghi clip query bằng thiết bị điện tử để đưa vào công cụ. |
| Q&A | 5 phút | Ghi câu hỏi ngay từ đầu; bổ sung mô tả theo thời gian; xác minh cả vị trí sự kiện **và** câu trả lời. |
| TRAKE | 5 phút | Nhận toàn bộ chuỗi từ đầu; chọn một video và đúng một semantic frame cho mỗi giai đoạn, giữ đúng thứ tự. |

Điểm phụ thuộc thời điểm nộp đúng đầu tiên; mỗi lần nộp sai trước đó bị trừ 10 điểm. Vì vậy UI phải giúp xem lại bằng chứng, phân biệt ứng viên với đáp án đã chốt, và tránh nộp nhầm/trùng. KIS dùng video ID và timestamp mili giây; QA dùng `QA-<ANSWER>-<VIDEO_ID>-<TIME_MS>`; TRAKE dùng `TR-<VIDEO_ID>-<FRAME_ID1>,...`. PDF không nêu dung sai timestamp, nên không hiển thị một dung sai tự giả định như luật thi.

## 3. Trạng thái có thể tận dụng

- `frontend/index.html` đã có tìm kiếm Semantic/OCR/ASR và Smart Hybrid (đang opt-in), lưới kết quả, preview, filmstrip, context, AI chat, Submission Builder và lưu query trong `localStorage`.
- Có API xuất **JSON DRES cục bộ** cho một kết quả đang chọn. Serializer/validator offline đã có; chưa xác minh nộp thật lên DRES. Không hiển thị nút hoặc thông báo khiến người thi tưởng đã nộp khi mới tải JSON.
- UI hiện chưa có một workspace rõ ràng cho câu đang thi, đồng hồ/deadline, lịch sử gợi ý bổ sung, preview payload/số lần nộp; các thao tác quan trọng còn nằm trong sidebar. Nhãn ASR BM25 không khớp runtime hiện tại. Đây là điểm bắt đầu để kiểm tra bằng diễn tập, không phải kết luận từ benchmark UI đã đo.

## 4. Thứ tự làm UI

### P0 — Workspace cho câu đang thi

1. Có một **câu đang hoạt động** với loại câu, thời điểm bắt đầu, đồng hồ đếm ngược 4/5 phút và trạng thái nháp/đã chốt/đã nộp do người thao tác xác nhận. Không tự coi việc xuất file là đã nộp.
2. Giữ câu hỏi Q&A cố định và cho thêm từng gợi ý Textual KIS/Q&A theo thứ tự thời gian; có thể tìm lại sau mỗi gợi ý mà không mất query, ứng viên đã lưu, answer hay vị trí đang xem.
3. Đặt tìm kiếm, lưới ứng viên, preview và đáp án đang chọn trong cùng luồng nhìn trên màn hình thi; trạng thái loading, lỗi và kết quả rỗng phải rõ. Hỗ trợ bàn phím cho các thao tác lặp lại, tránh phím tắt làm mất dữ liệu khi đang gõ.
4. Tự lưu nháp và khôi phục sau refresh/crash; có nút reset câu rõ ràng với xác nhận. Không lưu session ID/mật khẩu DRES trong dữ liệu nháp hoặc log UI.

**Đạt P0 khi:** trong diễn tập, operator hoàn thành một câu KIS và một câu Q&A có gợi ý bổ sung mà không mất trạng thái; khôi phục được nháp sau refresh; đồng hồ và trạng thái nộp không gây hiểu sai.

### P1 — Tìm và kiểm chứng ứng viên nhanh

1. Làm rõ loại tìm kiếm, bộ lọc video, số kết quả và nguồn evidence; đổi nhãn sai. Cho so sánh ứng viên cạnh nhau hoặc chuyển ứng viên nhanh mà không mất vị trí cuộn/query.
2. Từ một thẻ kết quả mở ngay preview, frame lân cận/filmstrip, timestamp nguồn, OCR/ASR khi có và hành động **chọn làm đáp án**. Phân biệt frame index dùng duyệt với timestamp ms dùng KIS/QA và frame ID dùng TRAKE.
3. Cho ghim shortlist, đánh dấu đã loại và quay lại ứng viên; ở TRAKE, hiển thị các giai đoạn còn thiếu và thứ tự frame trong cùng video. Ở Q&A, đặt câu hỏi, evidence và ô answer cạnh vị trí video đang xác minh.
4. Chỉ tối ưu tải ảnh/preview khi diễn tập hoặc trace cho thấy ảnh chờ làm chậm việc kiểm chứng; giữ fallback hiển thị khi ảnh/video không tải được.

**Đạt P1 khi:** người thi có thể tìm lại, so sánh và chốt ứng viên qua chuột/bàn phím trong giới hạn thời gian của cả bốn dạng; không nhầm frame index với thời gian nộp.

### P2 — Chốt và nộp an toàn

1. Biến Submission Builder thành bước chốt **một đáp án hiện hành**: hiện video ID, frame, timestamp ms, answer hoặc chuỗi TRAKE và nguồn bằng chứng trước khi xuất. Cho sửa nhanh rồi xem lại payload.
2. Dùng validator hiện có để chặn thiếu/sai video ID, timestamp, answer, thiếu/trùng/đảo frame TRAKE hoặc nhiều video trong một chuỗi. Báo lỗi ngay tại trường cần sửa; không âm thầm tạo payload sai.
3. Hiển thị JSON DRES trước khi tải/copy; cảnh báo khi đáp án trùng với lần đã nộp do operator ghi nhận. Lưu lịch sử lần nộp và phản hồi DRES nếu có, tách rõ **đã chuẩn bị**, **đã gửi** và **được chấp nhận/từ chối**.
4. Hướng dẫn Chung kết nêu endpoint chuẩn DRES (`/api/v2/login`, `/api/v2/client/evaluation/list`, `/api/v2/submit/{evaluationID}`) nhưng cho phép BTC thay URL trong ngày thi. Dùng transport HTTPS với endpoint base cấu hình backend. Operator có thể nhập credentials trong review hoặc cấu hình `DRES_USERNAME`/`DRES_PASSWORD` trong `.env` bị Git ignore; nút đăng nhập cấu hình chỉ khả dụng từ cùng-origin localhost, secrets không trả về UI/log. Backend chỉ gửi credentials khi operator chọn đăng nhập; sessionId giữ ở RAM UI. Liệt kê/chọn evaluation `ACTIVE`, gửi payload đã review đúng evaluation. Đánh dấu `Sent` chỉ khi POST trả HTTP thành công; không tự ghi `Accepted` nếu chưa hiểu response contract. Timeout/lỗi mạng sau POST phải báo kết quả chưa rõ và chặn gửi trùng payload cho cùng query cho đến khi operator kiểm tra DRES.
5. Giữ duplicate guard theo `query_id + fingerprint`: cảnh báo hiện tại là chưa đủ để tuân thủ “không nộp trùng”; khi đã sent/accepted/rejected/unknown phải chặn gửi y hệt, nhưng cho phép payload đã sửa như hướng dẫn chấm phạt lần sai.

**Đạt P2 khi:** cả bốn dạng tạo được payload đúng từ lựa chọn trên UI; lỗi định dạng được chặn trước khi xuất/gửi; operator nhìn rõ mình đã gửi hay mới chuẩn bị; thao tác sửa đáp án không xóa lịch sử lần nộp.

### Đối chiếu HD-ChungKet-2026.pdf với UI/code

| Điều khoản trong PDF | Hiện trạng đối chiếu | Việc cần làm |
|---|---|---|
| Textual KIS/Q&A nhận mô tả lần lượt; Q&A có câu hỏi ngay từ đầu | Workspace có initial text và clue theo thời điểm; câu hỏi được giữ riêng cho Q&A | Giữ nguyên; đưa thứ tự thao tác này vào checklist/diễn tập |
| Video KIS clip tối đa 20 giây; không chụp/ghi bằng thiết bị để đưa vào công cụ | Workspace hiện cảnh báo khi loại câu là Video KIS; hướng dẫn text/phác họa và không nạp bản chụp/ghi từ clip | Đã triển khai trong `frontend/index.html` và checklist |
| TRAKE: một video, một semantic keyframe cho mỗi stage; retrieval rồi alignment | Event-to-candidate/serializer giữ video và thứ tự; checklist yêu cầu đúng một semantic keyframe cho mỗi stage | Đã thêm gate vận hành trong `docs/DRES_OPERATOR_CHECKLIST.md`; P3 vẫn cần rehearsal có kiểm soát |
| Deadline 4 phút Video KIS, 5 phút các dạng khác; full score 50–100 theo thời điểm và -10 mỗi lần sai; partial TRAKE chia đôi khi đạt 50%–<100% | Timer và hàm scoring offline đã có; checklist ghi đủ hạn từng dạng; chưa đo rehearsal có kiểm soát | Phần timer/scoring/checklist đã có; đo các mốc và xác nhận correctness vẫn thuộc P3 |
| Login lấy session; list evaluation và chọn ACTIVE; POST body KIS/QA/TRAKE; item name không extension; KIS ms; không gửi trùng | Serializer local và transport HTTPS đã có; UI review hỗ trợ login, chọn ACTIVE và submit sau xác nhận; payload cùng query sau sent/unknown bị khóa | Đã triển khai theo PDF, mock-contract đã qua; live endpoint/session/evaluation vẫn cần BTC để kiểm tra |
| DRES chấp nhận request/đáp án | Credential do người dùng cung cấp đã cấu hình trong `.env` bị Git ignore; endpoint BTC/evaluation thi và response contract thực tế vẫn chưa xác nhận. DRES có thể trả `sessionId` trực tiếp hoặc session cookie tùy phiên bản | Nút cấu hình lấy sessionId chỉ gửi credential khi operator bấm và chỉ qua localhost same-origin; chưa đăng nhập live. Chỉ ghi `Sent`, không suy ra Accepted; xác minh response và `start=end` trong buổi tập huấn |

**Thứ tự triển khai sau đối chiếu:** Các mục offline đã hoàn tất: backlog cập nhật, client/server routes DRES, UI login/evaluation/submit với duplicate/timeout guard, cảnh báo Video KIS, checklist và kiểm thử contract mock. Gửi thật/chạy xác nhận response chỉ làm trong buổi tập huấn sau khi BTC cấp endpoint, credential và evaluation.

**Kết quả thực hiện đối chiếu (2026-09-23, cập nhật 2026-09-24):** Đã triển khai HTTP client DRES v2 HTTPS với URL backend cấu hình qua `DRES_API_BASE_URL` (mặc định `https://eventretrieval.one`), các route login/list ACTIVE/submit, và UI review để operator nhập credential hoặc bấm **Get session from .env**, chọn evaluation và gửi sau xác nhận. Credential từ người dùng nằm trong `.env` bị Git ignore; endpoint chỉ đọc server values khi operator bấm, chặn cross-origin và chỉ trả sessionId cho trang. Client nhận `sessionId` JSON và session-cookie fallback. Session chỉ ở RAM trình duyệt và mất khi refresh. Thành công HTTP chỉ ghi `Sent`, không tự suy diễn `Accepted`; timeout/5xx là `outcome unknown`; HTTP 412 là `Rejected`; Sent/Rejected/unknown khóa cùng payload/query ở UI/backend trong tiến trình hiện tại. Health localhost healthy; test cross-origin nhận 403. Contract route/client/dedup 14/14, serializer 16/16, operator export/UI 9/9, operator search 4/4, TRAKE 3/3, Q&A evidence 3/3 và DRES timing 6/6 đã qua. Chưa gửi credential tới DRES live vì endpoint BTC chưa xác nhận; login/list evaluation, response semantics, `start=end` và submit thật vẫn chờ xác nhận trong buổi tập huấn; P2 chưa đạt cổng live.

### P3 — Diễn tập và làm cứng luồng thi

1. Diễn tập tối thiểu một kịch bản cho mỗi dạng trong đúng hạn 4/5 phút, gồm gợi ý bổ sung, ứng viên sai, kết quả rỗng, ảnh lỗi, refresh và sửa đáp án.
2. Đo từ lúc nhận đề đến: ứng viên đúng đầu tiên, đáp án hợp lệ sẵn sàng nộp, nộp được xác nhận. Ghi số click/phím, số lần chọn nhầm, payload sai, trùng nộp, mất nháp và lỗi/timeout theo từng kịch bản.
3. Sửa nút thắt UI lớn nhất từ diễn tập, rồi chạy lại cùng kịch bản. Ưu tiên lỗi làm mất đáp án hoặc quá hạn trước các chỉnh sửa thẩm mỹ.

**Đạt P3 khi:** operator hoàn thành cả bốn kịch bản trong deadline, không mất nháp/nhầm trạng thái, và có checklist ngắn để khởi động, kiểm tra dữ liệu, chọn evaluation, chốt/nộp trong ngày thi.

## 5. Cách thực hiện mỗi lượt

Chọn **một** nút thắt UI theo thứ tự P0 → P3; ghi thao tác hiện tại, thời gian hoặc lỗi quan sát được và tiêu chí hoàn tất. Sửa trong phạm vi luồng đó, diễn tập lại cùng dữ liệu, giữ nếu người thi thao tác nhanh hoặc chắc chắn hơn mà không làm hỏng dạng câu khác. Cập nhật `PROJECT_CONTEXT.md` khi workflow/API đổi và ghi kết quả ngắn trong `CHANGELOG.md`. Không cần mở vòng benchmark model hay ngưỡng thống kê của plan cũ cho thay đổi UI.

Không sửa các artifact dữ liệu gốc: `video_index_v2.db`, `video_fps_map.json`, `video_drive_metadata.json`, `translation_cache.db`, `frame_map_supabase.json`, `answerAndQuestion.jsonl`, `all_vectors.npy`, `.env`. Những kết quả benchmark retrieval/VLM trước đây chỉ là bối cảnh để hiểu chất lượng ứng viên hiện có; không biến chúng thành backlog đang chạy trong giai đoạn tập trung UI.

### Tiến độ thực hiện UI

- P0 workspace: đạt tiêu chí thao tác/lưu nháp qua diễn tập KIS và Q&A với clue bổ sung: tìm kiếm lặp lại trả candidate, candidate và answer Q&A còn nguyên sau refresh; timer 4/5 phút và trạng thái operator xác nhận đã kiểm tra. Nút reset có xác nhận đã triển khai nhưng chưa diễn tập. Chi tiết ở `CHANGELOG.md` ngày 2026-09-23.
- Giới hạn còn lại: diễn tập kiểm tra cơ chế thao tác bằng dữ liệu tổng hợp, không chấm correctness; refresh đã thử nhưng crash chưa thử. Chưa kiểm tra endpoint/response DRES thật. Không xem việc tải JSON là đã nộp.
- P1 search clarity: đã đổi nhãn sai `ASR BM25 (Exact Text)` thành `ASR Transcript Search`, có tooltip phân biệt đây là lời được nhận diện từ video. Runtime giữ nguyên exact phrase FTS/fuzzy substring fallback. Chi tiết ở `CHANGELOG.md` ngày 2026-09-23.
- P1 ảnh lỗi: candidate, shortlist, filmstrip, modal và evidence DRES sẽ thử URL ảnh dự phòng còn lại; nếu đều lỗi, hiện thông báo và giữ video/frame/timestamp để xác minh. JS syntax check đã qua; từng URL ngoài mạng chưa được kiểm tra.
- P1 shortlist/compare: đã tách shortlist/ứng viên bị loại khỏi Submission Builder; hai candidate có thumbnail/metadata đặt cạnh nhau. Diễn tập ghim → loại → khôi phục → preview → ghim candidate thứ hai → compare → refresh đã pass, query draft và cả hai candidate được giữ. Chưa diễn tập TRAKE shortlist, viewport khác hoặc chấm correctness/relevance. Chi tiết ở `CHANGELOG.md` ngày 2026-09-23.
- P1 TRAKE event order: mô tả ban đầu và clue thành các sự kiện có thể gán candidate; bảng hiển thị event thiếu/trùng, video và thời gian. Sequence hợp lệ đồng bộ thành một query TRAKE riêng với frame list theo thứ tự; diễn tập xác nhận cập nhật draft liên kết, giữ hai query khác và khôi phục sau refresh. Chưa chấm correctness/serializer DRES hoặc diễn tập bàn phím. Chi tiết ở `CHANGELOG.md` ngày 2026-09-23.
- P2 review-before-download: Submission Builder yêu cầu đúng một đáp án; serializer/validator local mở JSON cùng query/type, video, frame/sequence, câu trả lời Q&A, ảnh frame và evidence OCR/ASR/object. KIS/Q&A timestamp ms lấy từ payload đã serialize; tải file chỉ khả dụng sau khi chuẩn bị thành công và bị chặn nếu draft đổi sau review. UI phân biệt tải cục bộ với submit thật; hộp review nay có login/evaluation/submit DRES. Diễn tập trước đó mở review cho KIS (L26_V246/4495/179800 ms), Q&A (L30_V023/2722/“wooden spoon”/108880 ms) và TRAKE (L26_V113/5 frame tăng đúng thứ tự, ảnh/timestamp đủ). Còn thiếu diễn tập tải file cuối, Video KIS và response live DRES. Đây là tiến độ một phần P2; chưa đạt P2.
- P2 validation theo trường: lỗi Video ID (trống/path/extension), frame index (không nguyên/âm/ngoài vùng safe integer), Q&A answer rỗng và TRAKE frame IDs (rỗng, cú pháp sai, trùng/không tăng) hiện dưới ô tương ứng khi gõ; review chặn trước khi gọi API và gom lỗi còn lại. Giá trị frame/dãy chưa hợp lệ vẫn được giữ trong local draft để operator sửa. Diễn tập đã thấy lỗi extension dưới ô Video ID và dialog chặn review, lỗi answer Q&A rỗng, lỗi TRAKE đảo thứ tự; lượt bàn phím TRAKE xác nhận lỗi inline và review hợp lệ cho 5 frame. Chưa diễn tập mọi nhánh (thiếu frame, trùng frame, frame âm/phân số, path, frame index quá lớn). Serializer contract 16/16 và operator benchmark 9/9 đều pass với `.venv`.
- P2 history/trùng payload: attempt `Prepared locally` lưu payload/fingerprint/thời điểm trong localStorage. UI cảnh báo và khóa gửi cùng payload cho cùng query sau Sent/Accepted/Rejected/unknown; backend cũng khóa sau Sent/Rejected/unknown trong tiến trình hiện tại. Có thể sửa payload để tạo lần thử khác. Các nút manual history vẫn có cho lần gửi bên ngoài; submit qua app cập nhật Sent khi nhận 2xx, không tự ghi Accepted. HTTP 412 được ghi Rejected và khóa exact payload. Rehearsal cũ đã kiểm tra trạng thái/note sau reload bằng dữ liệu TEST ONLY; chưa diễn tập bàn phím với kết nối/submit mới, nhánh Rejected thực tế, hay nhiều payload đã gửi/đính chính response. Contract mock route/client/dedup hiện 14/14. Live DRES vẫn chưa xác nhận; P2 chưa đạt.
- P3 keyboard TRAKE/review: trước sửa, Tab từ nội dung chính phải đi qua toàn bộ shortlist trước khi tới nút Submission, và các query lưu là hàng `<div>` không chọn được bằng bàn phím. Nút Submission Build hiện mở thẳng tab Builder, đưa focus về query đang chọn; query dùng nút chọn riêng có nhãn/`aria-pressed`, focus được giữ sau khi chọn. Diễn tập trên origin 127.0.0.1: mở Builder → sửa dãy frame thành thứ tự sai (lỗi inline) → khôi phục dãy đúng → mở review với `6633 → 6695 → 6740 → 6820 → 6944`. Lượt này hộp review nhận focus khi mở, giữ Tab trong hộp, đóng bằng Escape và trả focus về nút Review. Note `TEST ONLY — keyboard rehearsal; not sent to DRES` được nhập và ghi trạng thái Sent; focus chuyển về trạng thái hiện tại, sau reload trạng thái/note còn nguyên và lần review lại cùng payload có cảnh báo trùng. TRAKE dùng dữ liệu tổng hợp; các lượt QA, Video KIS và KIS textual được ghi ở dưới. Chưa kiểm chứng correctness/thi có kiểm soát hoặc nhánh Accepted/Rejected từ modal. Chưa đạt P3.
- P3 keyboard Q&A: trên origin thử nghiệm `localhost:8000` riêng, tạo query QA, tìm `wooden spoon`, thêm candidate `L26_V424` frame `2992`; dùng Tab từ Video ID qua Frame index đến ô Q&A answer. Để trống hiển thị lỗi “Required: enter the Q&A answer.”; nhập lại `wooden spoon`, Tab đến Review và Enter. Preview tạo payload `QA-wooden spoon-L26_V424-119680` với timestamp nguồn `119680 ms`; Escape, reload và mở Builder xác nhận video/frame/answer còn nguyên. Chỉ kiểm tra một luồng QA tổng hợp và preview local; không ghi Sent, không gửi DRES, không chấm correctness/deadline. Còn cần kiểm tra các nhánh QA bổ sung và hoàn thành đủ dạng câu theo các điều kiện P3.
- P3 Video KIS: chọn loại câu bằng phím, timer UI bắt đầu từ 4:00; nhập mô tả, chuyển nội dung sang search, tìm candidate, tạo query KIS và dùng Tab từ Video ID/frame qua nút Review rồi Enter. Preview hiển thị `L26_V276` frame `2931`, timestamp nguồn `117240 ms`; khi mở preview timer hiện khoảng 3:12. Sau Escape/reload, loại câu, mô tả, trạng thái và query/frame vẫn còn. Đây là diễn tập cục bộ tổng hợp, không chấm correctness hoặc đo thời gian thi có kiểm soát; không gửi DRES.
- P3 KIS textual: chọn loại câu bằng phím, khởi động lại timer 5:00, nhập mô tả và chuyển sang search. Tìm kiếm trả 50 kết quả (badge API 445 ms); thêm `L26_V494` frame `2132` vào query riêng. Nhập frame `-1` cho thấy lỗi inline “Enter a whole, non-negative frame index.”; sửa lại `2132`, Tab đến Review và Enter. Preview ghi timestamp `85280 ms`; timer khi review khoảng `4:19`. Escape/reload khôi phục loại câu, mô tả và query/frame. Chỉ thử trên dữ liệu tổng hợp; badge API không phải thời gian end-to-end, không chấm correctness/thi có kiểm soát và không gửi DRES.
- Bao phủ hiện tại: đã có lượt cục bộ bằng dữ liệu tổng hợp cho TRAKE, QA, Video KIS và KIS textual; checklist ngày thi đã viết tại `docs/DRES_OPERATOR_CHECKLIST.md`. Đã bổ sung fallback ảnh lỗi và quan sát trực tiếp UI localhost. P3 còn cần diễn tập reset, biến thể rỗng/clue/ứng viên sai, tải file cuối và bàn phím sau cập nhật DRES, đo thời gian toàn luồng trong deadline và xác nhận correctness. Endpoint/session DRES thật chưa được cấp/kiểm tra; P3 chưa đạt.
