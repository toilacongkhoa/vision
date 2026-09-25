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

- `frontend/index.html` đã có tìm kiếm Smart Hybrid (mặc định)/Semantic/OCR/ASR, lưới kết quả, preview, filmstrip, context, AI chat, Submission Builder và lưu query trong `localStorage`.
- Có API xuất **JSON DRES cục bộ** cho một kết quả đang chọn. Serializer/validator offline đã có; chưa xác minh nộp thật lên DRES. Không hiển thị nút hoặc thông báo khiến người thi tưởng đã nộp khi mới tải JSON.
- Workspace câu đang thi, đồng hồ, lịch sử gợi ý, review payload và trạng thái nộp đã được thêm; diễn tập cục bộ vẫn chưa xác nhận đáp án đúng hoặc DRES thật. Nhãn ASR BM25 cũ đã đổi, nhưng nhiều chữ UI tĩnh/động vẫn là tiếng Anh. Phần 6 dưới đây là backlog hiện tại cho việc Việt hóa.

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
4. Hướng dẫn Chung kết nêu endpoint chuẩn DRES (`/api/v2/login`, `/api/v2/client/evaluation/list`, `/api/v2/submit/{evaluationID}`) nhưng cho phép BTC thay URL trong ngày thi. Dùng transport HTTPS với endpoint base cấu hình backend. Operator có thể nhập credentials trong review hoặc cấu hình `DRES_USERNAME`/`DRES_PASSWORD` trong `.env` bị Git ignore; nút đăng nhập cấu hình chỉ khả dụng từ cùng-origin localhost, secrets không trả về UI/log. Backend chỉ gửi credentials khi operator chọn đăng nhập; sessionId giữ ở RAM UI. Liệt kê/chọn evaluation `ACTIVE`, gửi payload đã review đúng evaluation. Đánh dấu `Sent` chỉ khi POST trả HTTP thành công; không tự ghi `Accepted` nếu chưa hiểu response contract. Timeout/lỗi mạng sau POST phải báo kết quả chưa rõ; kiểm tra DRES trước khi gửi lại vì yêu cầu trước có thể đã được ghi nhận.
5. Theo dõi fingerprint theo `query_id + payload` để cảnh báo khi payload đã từng gửi. Cảnh báo không khóa nút: operator vẫn có thể gửi lại cùng payload nếu cần; mỗi lần gửi có thể được tính thành một lần thử riêng theo quy tắc cuộc thi.

**Đạt P2 khi:** cả bốn dạng tạo được payload đúng từ lựa chọn trên UI; lỗi định dạng được chặn trước khi xuất/gửi; operator nhìn rõ mình đã gửi hay mới chuẩn bị; thao tác sửa đáp án không xóa lịch sử lần nộp.

### Đối chiếu HD-ChungKet-2026.pdf với UI/code

| Điều khoản trong PDF | Hiện trạng đối chiếu | Việc cần làm |
|---|---|---|
| Textual KIS/Q&A nhận mô tả lần lượt; Q&A có câu hỏi ngay từ đầu | Workspace có initial text và clue theo thời điểm; câu hỏi được giữ riêng cho Q&A | Giữ nguyên; đưa thứ tự thao tác này vào checklist/diễn tập |
| Video KIS clip tối đa 20 giây; không chụp/ghi bằng thiết bị để đưa vào công cụ | Workspace hiện cảnh báo khi loại câu là Video KIS; hướng dẫn text/phác họa và không nạp bản chụp/ghi từ clip | Đã triển khai trong `frontend/index.html` và checklist |
| TRAKE: một video, một semantic keyframe cho mỗi stage; retrieval rồi alignment | Event-to-candidate/serializer giữ video và thứ tự; checklist yêu cầu đúng một semantic keyframe cho mỗi stage | Đã thêm gate vận hành trong `docs/DRES_OPERATOR_CHECKLIST.md`; P3 vẫn cần rehearsal có kiểm soát |
| Deadline 4 phút Video KIS, 5 phút các dạng khác; full score 50–100 theo thời điểm và -10 mỗi lần sai; partial TRAKE chia đôi khi đạt 50%–<100% | Timer và hàm scoring offline đã có; checklist ghi đủ hạn từng dạng; chưa đo rehearsal có kiểm soát | Phần timer/scoring/checklist đã có; đo các mốc và xác nhận correctness vẫn thuộc P3 |
| Login lấy session; list evaluation và chọn ACTIVE; POST body KIS/QA/TRAKE; item name không extension; cảnh báo payload trùng | Serializer local và transport HTTPS đã có; UI review hỗ trợ login, chọn ACTIVE, cảnh báo payload cùng query đã gửi nhưng vẫn cho phép submit lại | Đã triển khai theo PDF, mock-contract đã qua; live endpoint/session/evaluation vẫn cần BTC để kiểm tra |
| DRES chấp nhận request/đáp án | Credential do người dùng cung cấp đã cấu hình trong `.env` bị Git ignore; endpoint BTC/evaluation thi và response contract thực tế vẫn chưa xác nhận. DRES có thể trả `sessionId` trực tiếp hoặc session cookie tùy phiên bản | Nút cấu hình lấy sessionId chỉ gửi credential khi operator bấm và chỉ qua localhost same-origin; chưa đăng nhập live. Chỉ ghi `Sent`, không suy ra Accepted; xác minh response và `start=end` trong buổi tập huấn |

**Thứ tự triển khai sau đối chiếu:** Các mục offline đã hoàn tất: backlog cập nhật, client/server routes DRES, UI login/evaluation/submit với cảnh báo payload trùng và trạng thái timeout, cảnh báo Video KIS, checklist và kiểm thử contract mock. Gửi thật/chạy xác nhận response chỉ làm trong buổi tập huấn sau khi BTC cấp endpoint, credential và evaluation.

**Kết quả thực hiện đối chiếu (2026-09-23, cập nhật 2026-09-24):** Đã triển khai HTTP client DRES v2 HTTPS với URL backend cấu hình qua `DRES_API_BASE_URL` (mặc định `https://eventretrieval.one`), các route login/list ACTIVE/submit, và UI review để operator nhập credential hoặc bấm **Get session from .env**, chọn evaluation và gửi sau xác nhận. Credential từ người dùng nằm trong `.env` bị Git ignore; endpoint chỉ đọc server values khi operator bấm, chặn cross-origin và chỉ trả sessionId cho trang. Client nhận `sessionId` JSON và session-cookie fallback. Session chỉ ở RAM trình duyệt và mất khi refresh. Thành công HTTP chỉ ghi `Sent`, không tự suy diễn `Accepted`; timeout/5xx là `outcome unknown`; HTTP 412 là `Rejected`; lịch sử lưu fingerprint để cảnh báo gửi lại payload trùng nhưng UI và backend vẫn chuyển tiếp lần gửi mới. Chưa gửi credential tới DRES live vì endpoint BTC chưa xác nhận; login/list evaluation, response semantics, `start=end` và submit thật vẫn chờ xác nhận trong buổi tập huấn; P2 chưa đạt cổng live.

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
- P2 history/trùng payload: attempt `Prepared locally` lưu payload/fingerprint/thời điểm trong localStorage. UI cảnh báo cùng payload/query đã từng gửi, nhưng luôn cho phép tạo lần thử mới; backend chuyển tiếp mọi payload hợp lệ. Các nút manual history vẫn có cho lần gửi bên ngoài; submit qua app cập nhật Sent khi nhận 2xx, không tự ghi Accepted. HTTP 412 được ghi Rejected. Rehearsal cũ đã kiểm tra trạng thái/note sau reload bằng dữ liệu TEST ONLY; chưa diễn tập bàn phím với kết nối/submit mới, nhánh Rejected thực tế, hay nhiều payload đã gửi/đính chính response. Contract mock route/client đã qua. Live DRES vẫn chưa xác nhận; P2 chưa đạt.
- P3 keyboard TRAKE/review: trước sửa, Tab từ nội dung chính phải đi qua toàn bộ shortlist trước khi tới nút Submission, và các query lưu là hàng `<div>` không chọn được bằng bàn phím. Nút Submission Build hiện mở thẳng tab Builder, đưa focus về query đang chọn; query dùng nút chọn riêng có nhãn/`aria-pressed`, focus được giữ sau khi chọn. Diễn tập trên origin 127.0.0.1: mở Builder → sửa dãy frame thành thứ tự sai (lỗi inline) → khôi phục dãy đúng → mở review với `6633 → 6695 → 6740 → 6820 → 6944`. Lượt này hộp review nhận focus khi mở, giữ Tab trong hộp, đóng bằng Escape và trả focus về nút Review. Note `TEST ONLY — keyboard rehearsal; not sent to DRES` được nhập và ghi trạng thái Sent; focus chuyển về trạng thái hiện tại, sau reload trạng thái/note còn nguyên và lần review lại cùng payload có cảnh báo trùng. TRAKE dùng dữ liệu tổng hợp; các lượt QA, Video KIS và KIS textual được ghi ở dưới. Chưa kiểm chứng correctness/thi có kiểm soát hoặc nhánh Accepted/Rejected từ modal. Chưa đạt P3.
- P3 keyboard Q&A: trên origin thử nghiệm `localhost:8000` riêng, tạo query QA, tìm `wooden spoon`, thêm candidate `L26_V424` frame `2992`; dùng Tab từ Video ID qua Frame index đến ô Q&A answer. Để trống hiển thị lỗi “Required: enter the Q&A answer.”; nhập lại `wooden spoon`, Tab đến Review và Enter. Preview tạo payload `QA-wooden spoon-L26_V424-119680` với timestamp nguồn `119680 ms`; Escape, reload và mở Builder xác nhận video/frame/answer còn nguyên. Chỉ kiểm tra một luồng QA tổng hợp và preview local; không ghi Sent, không gửi DRES, không chấm correctness/deadline. Còn cần kiểm tra các nhánh QA bổ sung và hoàn thành đủ dạng câu theo các điều kiện P3.
- P3 Video KIS: chọn loại câu bằng phím, timer UI bắt đầu từ 4:00; nhập mô tả, chuyển nội dung sang search, tìm candidate, tạo query KIS và dùng Tab từ Video ID/frame qua nút Review rồi Enter. Preview hiển thị `L26_V276` frame `2931`, timestamp nguồn `117240 ms`; khi mở preview timer hiện khoảng 3:12. Sau Escape/reload, loại câu, mô tả, trạng thái và query/frame vẫn còn. Đây là diễn tập cục bộ tổng hợp, không chấm correctness hoặc đo thời gian thi có kiểm soát; không gửi DRES.
- P3 KIS textual: chọn loại câu bằng phím, khởi động lại timer 5:00, nhập mô tả và chuyển sang search. Tìm kiếm trả 50 kết quả (badge API 445 ms); thêm `L26_V494` frame `2132` vào query riêng. Nhập frame `-1` cho thấy lỗi inline “Enter a whole, non-negative frame index.”; sửa lại `2132`, Tab đến Review và Enter. Preview ghi timestamp `85280 ms`; timer khi review khoảng `4:19`. Escape/reload khôi phục loại câu, mô tả và query/frame. Chỉ thử trên dữ liệu tổng hợp; badge API không phải thời gian end-to-end, không chấm correctness/thi có kiểm soát và không gửi DRES.
- Bao phủ hiện tại: đã có lượt cục bộ bằng dữ liệu tổng hợp cho TRAKE, QA, Video KIS và KIS textual; checklist ngày thi đã viết tại `docs/DRES_OPERATOR_CHECKLIST.md`. Đã bổ sung fallback ảnh lỗi và quan sát trực tiếp UI localhost. P3 còn cần diễn tập reset, biến thể rỗng/clue/ứng viên sai, tải file cuối và bàn phím sau cập nhật DRES, đo thời gian toàn luồng trong deadline và xác nhận correctness. Endpoint/session DRES thật chưa được cấp/kiểm tra; P3 chưa đạt.

## 6. Kế hoạch nhiệm vụ: Việt hóa toàn bộ UI

### 6.1. Mục tiêu, phạm vi và trạng thái

**Trạng thái 2026-09-24: đã Việt hóa UI và chạy kiểm tra contract offline; còn thiếu kiểm tra trực quan trên trình duyệt desktop/màn hình hẹp và diễn tập IME/lỗi UI.** Mục tiêu là người thao tác đọc được toàn bộ câu do ứng dụng kiểm soát bằng tiếng Việt tự nhiên, nhất quán, nhất là lúc chọn đáp án và gửi DRES. Phạm vi gồm text node HTML, `title`, `placeholder`, `alt`, `aria-label`, chú giải, hộp `alert/confirm`, lỗi tại trường, chuỗi template tạo qua JavaScript, trạng thái loading/rỗng/thành công/thất bại, văn bản trong modal và thông báo API do frontend hiển thị. Đã cập nhật `<html lang="vi">` và thời gian clue theo `vi-VN`, không đổi giá trị thời gian gửi DRES.

Không dịch văn bản do người thi nhập, câu trả lời tự do của AI Assistant, OCR/ASR trích từ video, tên video, tên evaluation do DRES trả về, dữ liệu JSON/CSV/ZIP xuất ra hoặc chi tiết kỹ thuật cần tra cứu. Không thay đổi search mode, API endpoint, khóa JSON, trạng thái nội bộ, ID DOM, tên hàm/biến, tiền tố payload hay marker SSE. Dịch truy vấn Việt–Anh trong `src/fast_translator.py` là chức năng retrieval riêng, không phải cách Việt hóa UI.

Tài liệu triển khai phải kiểm tra cả hai nguồn chữ trong cùng `frontend/index.html`: vùng HTML trước `<script>` và JavaScript inline (template literal, phép gán `textContent`/`innerHTML`, `alert`, `confirm`, `throw new Error`, nội dung tạo theo nhánh điều kiện). Rà thêm `src/main.py`, `src/dres_api.py`, `src/dres_client.py`, `src/dres_submission.py` cho các `detail` lỗi hiện thẳng lên trang. Không dịch tài liệu Swagger, log terminal hoặc MCP prompt trong lượt UI này.

### 6.2. Quy ước ngôn ngữ và các từ giữ nguyên

| Loại | Quyết định hiển thị | Lý do |
|---|---|---|
| Tên dạng câu | Giữ `KIS`, `TRAKE`, `Q&A`; danh sách dạng câu đang thi hiển thị `Textual KIS`, `Video KIS`, `Q&A`, `TRAKE`; menu loại query trong Submission Builder hiển thị `KIS (Text / Video)`, `Q&A`, `TRAKE`, theo yêu cầu người dùng. | Dùng đúng tên tiếng Anh của dạng câu để khớp cách gọi trong cuộc thi. |
| Công nghệ/tên riêng | Giữ `DRES`, `OCR`, `ASR`, `CLIP`, `AI`, `API`, `JSON`, `CSV`, `ZIP`, `Google Drive`, `Supabase`, `OpenCLIP`, `MCP`, `FPS`. | Tên giao thức, file, công nghệ hoặc chữ viết tắt quen thuộc. |
| Định danh/số đo | Giữ `Video ID`, `frame ID` khi nói tới định danh kỹ thuật; `Top K`, `ms`, `s`, `FPS` có thể giữ trên các nhãn ngắn. Giải thích `Video ID` là mã video, `frame index` là chỉ số khung hình. | Người thao tác phải đối chiếu giá trị nguồn và payload. |
| Thuật ngữ UI dịch | `Search` → `Tìm kiếm`; `Image Search` → `Tìm bằng ảnh`; `Frame Context` → `Khung hình lân cận`; `Preview` → `Xem trước`; `Submission Builder` → `Trình tạo đáp án`; `Review` → `Kiểm tra đáp án`; `Clue` → `Gợi ý`. | Ngắn, nhất quán, dễ quét trong thời gian thi. |
| Chế độ tìm | Giữ mã `smart`, `semantic`, `ocr`, `asr` trong request. Theo yêu cầu người dùng, giữ nguyên nhãn tiếng Anh theo thứ tự: `Smart Hybrid (Semantic + ASR)` (mặc định), `Semantic AI (CLIP only)`, `OCR (Exact Text)`, `ASR Transcript Search`; tooltip ASR cũng giữ nguyên tiếng Anh. Không dùng `BM25` vì runtime hiện không bảo đảm BM25. | Giữ đúng cách gọi quen thuộc trong giao diện này, không đổi giá trị request. |
| Frame và thời gian | Trong câu hiển thị: `frame` → `khung hình`, `frame index` → `chỉ số khung hình`, `timestamp` → `mốc thời gian`; luôn ghi đơn vị `ms`/`giây` và giữ số gốc. `semantic keyframe` có thể ghi `khung hình đại diện (semantic keyframe)` khi cần. | Tránh lấy frame index làm thời gian DRES. |
| Trạng thái gửi | `Prepared locally` → `Đã chuẩn bị trên máy`; `Sent to DRES` → `Đã gửi tới DRES`; `Accepted` → `Được chấp nhận` chỉ khi operator ghi nhận; `Rejected` → `Bị từ chối`; `outcome unknown` → `Chưa rõ kết quả gửi — kiểm tra DRES`. | Phân biệt tải file, gửi HTTP và chấm bài. |
| Chuỗi máy đọc | Giữ nguyên `KIS_TEXT`, `KIS_VIDEO`, `QA`, `TRAKE`, `prepared`, `submitted`, `accepted`, `rejected`, `outcome_unknown`, `answerSets`, `mediaItemName`, `QA-`, `TR-`, `vrs_submission_v2`, `[DONE]`, `[ERROR]`, `[TOOL]`. | Đây là dữ liệu/contract, không phải nhãn. |

Một thuật ngữ tiếng Anh được giữ khi là tên riêng, tên giao thức, viết tắt quen thuộc, giá trị cần đối chiếu nguyên dạng với DRES hoặc chữ nằm trong dữ liệu người dùng. Các câu chỉ dẫn và thông báo hành động vẫn viết bằng tiếng Việt, kể cả khi câu chứa các thuật ngữ đó. Không dịch nguyên văn cứng nhắc: ưu tiên câu ngắn, mô tả chính xác hành động và hậu quả.

### 6.3. Danh sách công việc theo thứ tự

Mỗi mục dưới đây chỉ đánh dấu xong khi nhãn thường, trạng thái động và thuộc tính trợ năng trong cùng vùng đã được kiểm tra. Vị trí dòng là mốc của `frontend/index.html` tại ngày lập plan; dùng ID/hàm để định vị khi file thay đổi.

| Mã | Vùng và vị trí hiện tại | Việc cần làm cụ thể | Điều kiện hoàn tất |
|---|---|---|---|
| V0 | Toàn trang: `<html lang="en">`, `<title>`, header, `statsBadge`, `loadStats()` | Chuyển `lang` sang `vi`; thống nhất tên sản phẩm/phiên bản hiển thị sau khi đối chiếu README/header; dịch trạng thái đang kiểm tra/online/offline. Giữ `API`, `DB`, số keyframe. | Tab trình duyệt, tiêu đề trang và trạng thái health đều đọc đúng tiếng Việt; không sửa API `version`. |
| V1 | `activeQuestionWorkspace`, `renderQuestionWorkspace()`, `questionTypeEl.onchange`, `resetQuestion` | Dịch tiêu đề câu thi, nhãn loại câu, đồng hồ, mô tả ban đầu, gợi ý, lịch sử rỗng, thêm/xóa gợi ý, reset và hai hộp xác nhận thay loại/reset. Giữ 4/5 phút, không thay `KIS_TEXT/KIS_VIDEO/QA/TRAKE`. | KIS/Q&A với gợi ý bổ sung, đổi loại và reset đều có câu rõ ràng; dữ liệu nháp còn sau refresh theo hành vi cũ. |
| V2 | `tabTextSearch`, `tabImageSearch`, `tabTimeConvert`, `tabContextSearch`, các form dòng đầu file và handlers `searchForm`/image/context/time | Dịch tab, label, nút, tooltip, placeholder hướng dẫn upload/drag/paste, bộ lọc và giới hạn; dịch trạng thái đang tìm/kết quả rỗng/lỗi API/kết nối và số lượng. Giữ giá trị option/request `semantic/smart/ocr/asr`, `top_k`, `video_id`. Form `videoSearchForm` không có tab mở: xác nhận còn được dùng trước khi quyết định dịch hoặc dọn code. | Cả bốn tab đang mở được đều có nhãn/thông báo tiếng Việt trong thành công, rỗng và lỗi; tìm kiếm vẫn gửi mode và filter như trước. |
| V3 | `renderResults()`, `renderFilmstrip()`, `openPreview()`, `navigatePreview()`, `drawBboxes()`, shortlist/TRAKE handlers | Dịch card, ghim/bỏ ghim, chọn đáp án, tìm ảnh tương tự, xem frame tiếp theo, so sánh, gán event, filmstrip, chi tiết ảnh/video, toggle OCR/object và fallback ảnh lỗi. Dịch `title`, `alt`, `aria-label` của nút chỉ có icon. Giữ video ID, frame ID, timestamp và điểm số. | Có thể hiểu mọi hành động trên card/preview bằng chuột và screen reader; ảnh lỗi vẫn cho biết video/frame/thời gian. |
| V4 | `submissionSidebar`, `renderSidebar()`, `validateDresItem()`, `addToActive()`, `btnExportZip` | Dịch tạo/đổi/chọn/xóa query, query rỗng, dòng đáp án, nhãn ô nhập, sắp xếp, lỗi video ID/frame/answer/TRAKE, nút xuất. Giữ tên query do người dùng đặt; tên mặc định mới nên là `Câu ...` nhưng phải xem tác động file CSV. Giữ `KIS/QA/TRAKE` và thứ tự frame. | Lỗi hiện ngay cạnh trường bằng tiếng Việt; payload/ZIP, `localStorage` và lựa chọn query không đổi khi reload. |
| V5 | `dresReviewModal`, `renderDresEvidenceFrames()`, `renderDresSubmissionHistory()`, `updateDresConnectionUi()`, `loadDresEvaluations()`, `loginToDres()`, `btnDresSubmit`, `btnExportDres` | Dịch summary/evidence/JSON, nút đóng/tải/submit, session/evaluation, trạng thái loading/lỗi, xác nhận gửi có cảnh báo mất điểm, cảnh báo trùng, kết quả chưa rõ, lịch sử attempt và 5 trạng thái nộp. Dịch các lỗi validation/API do app kiểm soát; giữ response kỹ thuật khi cần chẩn đoán. | Người thao tác phân biệt rõ `đã chuẩn bị`, `đã tải`, `đã gửi`, `được chấp nhận`, `bị từ chối`, `chưa rõ`; không có câu làm tưởng tải JSON là đã gửi. Duplicate guard và focus modal giữ nguyên. |
| V6 | AI chat: lời chào, prompt nhanh, `setChatGeneratingState()`, `renderCandidateCardsHtml()`, SSE error/status | Dịch nhãn do UI tạo, trạng thái tìm/đang suy nghĩ/dừng/lỗi, tooltip card, câu hướng dẫn. Giữ `AI`, `OCR`, `ASR`, `Context` nếu đó là tên tính năng đã được đội thống nhất; nếu không, dùng `khung hình lân cận`. Không tự dịch lời AI hoặc log tool. | Gửi/dừng/stream/lỗi bằng tiếng Việt; Enter + IME tiếng Việt vẫn không gửi nhầm lúc đang gõ. |
| V7 | `src/main.py`, `src/dres_api.py`, `src/dres_submission.py`, frontend hiển thị `data.detail` | Lập danh sách các lỗi backend xuất hiện trực tiếp ở UI; định nghĩa thông báo tiếng Việt theo trường hợp ổn định (validation, 401/403/409/412/422/504, network). Nếu cần giữ `detail`, đặt dưới nhãn `Chi tiết kỹ thuật` và escape trước khi render. Không đổi contract API chỉ để dịch câu. | Lỗi thường gặp có câu dễ hiểu; lỗi chưa biết vẫn có mã HTTP và chi tiết để xử lý, không làm rò credential. |
| V8 | Toàn bộ file sau khi triển khai | Quét lại text tĩnh/dynamic, `title`/`alt`/`aria-*`, hộp browser, trạng thái rỗng/lỗi; thống nhất dấu câu, cách xưng hô, đơn vị, viết hoa và chiều dài nút ở viewport nhỏ. Cập nhật `docs/PROJECT_CONTEXT.md`/`CHANGELOG.md`. | Không còn câu tiếng Anh do ứng dụng kiểm soát mà không có lý do ghi trong glossary; các thuật ngữ giữ nguyên có giải thích. |

**Thứ tự ưu tiên thực thi:** V5 và V4 trước vì liên quan gửi bài, xác nhận và lỗi nhập; tiếp theo V1, V2, V3 để operator tìm/chốt; sau đó V0, V6, V7, V8. Dù chia lượt, dùng một glossary chung và sửa cặp nhãn/trạng thái của cùng một hành động trong một lượt để tránh UI nửa Việt nửa Anh. V7 có thể làm song song với V5 nếu backend `detail` xuất hiện ở review.

### 6.4. Cách sửa để không phá hành vi

1. Chụp danh sách chuỗi hiện tại theo vùng: HTML text node; thuộc tính `title`, `placeholder`, `alt`, `aria-label`; chuỗi trong JS tạo bởi `textContent`, `innerHTML`, template literal, `alert/confirm`, các nhánh lỗi. Gắn mỗi chuỗi với ID/hàm và trạng thái UI tương ứng, không chỉ tìm từ `Search`/`Review` bằng regex vì một từ có thể là mã hoặc tên hàm.
2. Lưu glossary ở mục 6.2 làm nguồn thống nhất. Nếu tách thành object `UI_TEXT`/hàm render để giảm trùng lặp thì chỉ gom chuỗi hiển thị; không đổi dữ liệu lưu hoặc request. Nội dung đưa vào `innerHTML` phải được escape đúng, nhất là query do người dùng nhập và lỗi từ server.
3. Dịch theo ngữ cảnh: nút dùng động từ ngắn; trạng thái dùng câu kết quả; lỗi nói rõ việc cần sửa. Với confirmation DRES, nêu rõ đây là **gửi thật** và có thể mất điểm. `Accepted` chỉ được hiện khi người thao tác ghi nhận sau xác minh; `submitted` chỉ là HTTP thành công.
4. Không tự chuyển `toLocaleTimeString()` thành chuỗi cố định. Nếu đổi sang `vi-VN`, kiểm tra giờ của clue/attempt vẫn dễ đối chiếu, timer 4/5 phút không đổi, timestamp gửi DRES vẫn là ms từ payload.
5. Sau mỗi vùng, mở trang ở desktop và màn hình hẹp; kiểm tra chữ có dấu không cắt nút, đè đồng hồ, tràn sidebar, card hoặc modal. Kiểm tra Tab/Shift+Tab, Enter, Escape, focus, aria-live và nhập tiếng Việt bằng IME.

### 6.5. Bộ kiểm chứng và tiêu chí đóng nhiệm vụ

- **Kiểm tra tĩnh:** trích từng `<script>` inline chạy `node --check`; rà `rg` với các cụm tiếng Anh đã biết (`No results`, `Required:`, `Submit reviewed`, `Connection Error`, `Select as answer`, `aria-label`, `placeholder`, `confirm`, `alert`) rồi xem thủ công từng hit. Một hit ở tên hàm/contract không được tính là lỗi dịch.
- **Kiểm tra giao thức:** so trước/sau request `/api/v1/search` cho 4 mode, `/search/image`, `/search/context`, `/submission/dres/export`; payload KIS, QA, TRAKE vẫn có cùng schema/giá trị. Chạy `tools/benchmark_dres_submission.py`, `tools/dres_contract_checks.py`, `tools/benchmark_dres_operator.py` và `tools/benchmark_operator_search.py` nếu môi trường có dependency; không gửi DRES thật chỉ để thử chữ.
- **Diễn tập UI:** cho Textual KIS, Video KIS, Q&A và TRAKE, đi từ câu hỏi → tìm kiếm → candidate → preview → Builder → review. Ít nhất một trường hợp kết quả rỗng, ảnh lỗi, mạng lỗi, validation sai, duplicate payload, kết quả gửi chưa rõ và refresh. Kiểm tra trạng thái/answer/query còn nguyên sau refresh; không dùng đáp án thật hoặc thao tác gửi thật trong test bản dịch.
- **Trợ năng/ngôn ngữ:** thuộc tính `lang="vi"`; nút icon có tên tiếng Việt; thông báo lỗi đọc được bằng `aria-live`/focus; dấu tiếng Việt và số/đơn vị hiển thị đúng; prompt chat với Unikey/EVKey không submit giữa lúc IME đang ghép chữ.
- **Nghiệm thu:** 100% câu do ứng dụng kiểm soát trên các luồng đang dùng là tiếng Việt hoặc thuộc nhóm giữ nguyên ở mục 6.2; người thao tác hiểu được khác biệt giữa tải, gửi, chấp nhận, từ chối và chưa rõ; JS parse được; contract/request/payload không đổi; các luồng chính và nhánh lỗi không mất khả năng thao tác. Ghi từng vùng V0–V8 là xong/chưa xong cùng bằng chứng vào `CHANGELOG.md` sau khi triển khai, rồi cập nhật trạng thái ở đầu mục này.

### 6.6. Kết quả triển khai (2026-09-24)

| Mã | Trạng thái | Kết quả |
|---|---|---|
| V0 | Hoàn tất | `lang="vi"`; title/header và badge trạng thái hệ thống bằng tiếng Việt; tên hiển thị “Hệ thống tìm kiếm video” không kèm số phiên bản; không đổi API version. |
| V1 | Hoàn tất | Timer, mô tả, gợi ý, xóa gợi ý và xác nhận đổi loại/reset bằng tiếng Việt; vùng lịch sử để trống khi chưa có gợi ý. Danh sách loại câu giữ nguyên `Textual KIS`, `Video KIS`, `Q&A`, `TRAKE` theo yêu cầu người dùng. Thời gian clue định dạng `vi-VN`; enum và thời lượng không đổi. |
| V2 | Hoàn tất phần giao diện đang dùng | Tab/form và trạng thái tìm kiếm, số kết quả, kết nối, upload/paste, bộ lọc, đổi thời gian và context đã Việt hóa. Số kết quả mặc định là 50 ở UI/API cho tìm kiếm văn bản, ảnh, ảnh tương tự và tìm kiếm tổng hợp; tải lại UI không khôi phục số cũ từ `localStorage`. Bốn nhãn chế độ tìm và tooltip ASR giữ nguyên tiếng Anh theo yêu cầu; giá trị mode/request không đổi. Form tìm theo khoảng thời gian vẫn còn trong HTML nhưng không có tab mở. |
| V3 | Hoàn tất | Card, hành động ứng viên, preview, filmstrip, nhãn frame/mốc thời gian, OCR/object, ảnh fallback, nút điều hướng và trợ năng đã Việt hóa. |
| V4 | Hoàn tất | Tạo/đổi/chọn/xóa bộ đáp án, dòng dữ liệu, lỗi trường, trạng thái rỗng và nút xuất đã Việt hóa. Tên mặc định mới là `Câu` kèm giờ `vi-VN`; tên đã lưu cùng localStorage/ZIP/payload không bị chuyển đổi. |
| V5 | Hoàn tất | Review, summary/evidence, session/evaluation, xác nhận submit, tải JSON, trạng thái và lịch sử attempt được Việt hóa; lỗi API phổ biến ánh xạ qua `friendlyApiError()`, lỗi chưa nhận diện giữ chi tiết máy chủ. |
| V6 | Hoàn tất chuỗi do UI kiểm soát | Lời chào, prompt nhanh, nút/trạng thái chat, hành động candidate và thông báo lỗi đã Việt hóa; không dịch nội dung AI, OCR/ASR hay log tool. |
| V7 | Hoàn tất lớp hiển thị frontend | Đã đối chiếu `detail` ở `src/main.py`, `src/dres_api.py`, `src/dres_client.py`, `src/dres_submission.py`; dịch các nhóm lỗi ổn định trong frontend mà không sửa contract backend. Lỗi chưa nhận diện vẫn có chi tiết server để chẩn đoán. |
| V8 | Một phần — còn kiểm tra thiết bị | Đã rà chuỗi tĩnh/dynamic và thuộc tính trợ năng; mở UI local ở viewport 811 px, xác nhận nhãn/trạng thái, kiểm tra Tab/Shift+Tab và nhập Unicode tiếng Việt vào gợi ý rồi xóa để khôi phục. Alert khi nhập sai định dạng Context đã hiển thị đúng tiếng Việt; tìm Context với ID giả trả trạng thái rỗng đúng tiếng Việt. Đã thêm bố cục header hai hàng dưới 640 px để dành chỗ cho trạng thái/nút trên điện thoại. Chưa thể kiểm tra trực tiếp breakpoint dưới 640 px và composition event của IME trong browser automation hiện có. |

**Bằng chứng kiểm tra:** 5 script inline đều qua `node --check`; `tools/benchmark_dres_submission.py` 16/16; `tools/dres_contract_checks.py` 14/14; `tools/benchmark_dres_operator.py` 9/9 (assertion đã cập nhật để khớp câu tiếng Việt); `tools/benchmark_operator_search.py` 4/4. Browser localhost xác nhận form Context báo lỗi định dạng và kết quả rỗng bằng tiếng Việt; nhập Unicode/Tab/Shift+Tab hoạt động và dữ liệu câu thi/query được giữ nguyên. `git diff --check` đã được làm sạch. Không gửi request DRES thật. Thử screenshot Chrome headless ở 390 px không dùng làm bằng chứng vì môi trường đó không tải Tailwind CDN nên trang hiển thị không có CSS. Chưa đánh dấu nghiệm thu toàn bộ cho tới khi kiểm tra breakpoint dưới 640 px và IME trực tiếp.

## 7. Kế hoạch kiểm thử toàn bộ dự án

Kế hoạch test chi tiết, ma trận bao phủ từng thành phần, các ca POST DRES qua mock/local, diễn tập bốn dạng câu, cổng nghiệm thu và baseline ngày 2026-09-25 nằm tại [`docs/TEST_PLAN.md`](TEST_PLAN.md). Server local đang chạy tại `127.0.0.1:8000`; lượt này chỉ test mock/local theo yêu cầu, không gửi đáp án hợp lệ lên evaluation DRES thật.

Thực thi ngày 2026-09-25: test ban đầu lộ lỗi frame thiếu được export qua FPS fallback và POST trùng được gửi lại; code, UI, contract test và checklist đã được đồng bộ để chặn hai trường hợp này. Kết quả rerun sau sửa được ghi tại `docs/TEST_PLAN.md`. API local smoke đạt 17/22 route; năm route cần Supabase/Drive/Agy chưa chạy. UI E2E qua alias riêng bị lỗi kết nối, viewport dưới 640 px chưa xác minh. Retrieval benchmark chưa chạy vì thiếu `answerAndQuestion.jsonl`. DRES live chưa kiểm chứng theo lựa chọn chỉ test mock/local.
