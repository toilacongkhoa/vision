# Kế hoạch tự tối ưu hóa Vision cho Chung kết AI Challenge 2026

## 1. Mục tiêu

Mục tiêu cao nhất là tăng khả năng trả lời đúng và nhanh bài toán Event Retrieval from Visual Data trong hai luồng:

1. Thi truyền thống: thành viên dùng UI để tìm, kiểm tra và submit.
2. Thi tự động thử nghiệm: trợ lý AI phân tích query, chọn tool, thu thập evidence và trả kết quả.

Mọi thay đổi phải phục vụ ít nhất một kết quả thi sau:

- Tăng tỷ lệ tìm đúng video/frame cho Textual KIS.
- Tăng tỷ lệ tìm đúng vị trí và trả đúng nội dung cho Q&A/VQA.
- Tăng tỷ lệ tìm đúng chuỗi sự kiện cùng video, đúng thứ tự cho TRAKE.
- Giảm thời gian từ khi nhận query đến khi thấy candidate đúng hoặc có output sẵn sàng submit.
- Tăng độ chính xác end-to-end của trợ lý tự động.
- Ngăn crash, timeout hoặc lỗi submission trong luồng thi thật.

Không tối ưu “toàn bộ dự án” một cách chung chung. Chỉ tối ưu phần có tác động đo được đến bài thi.

## 2. Phạm vi thông tin đã biết

Nguồn định hướng hiện tại là AI_Challenge_2026_Chung_Ket.md.

### Đã được xác nhận

- Nhóm 1 thi Event Retrieval from Visual Data.
- Bài toán nhấn mạnh truy xuất và phân tích multimedia quy mô lớn.
- Hệ thống cần hỗ trợ tiếng Việt, hình ảnh, âm thanh và văn bản.
- BTC khuyến khích VLM, AI tạo sinh và tương tác giữa nhiều module.
- Có luồng người điều khiển và định hướng thử nghiệm thi tự động giữa các trợ lý AI.

### Chưa được xác nhận chính thức cho Chung kết 2026

- Tổng số query và thời gian mỗi query.
- Công thức tính điểm, số lần submit và mức phạt submit sai.
- Giao thức/server submission.
- Danh sách chính xác các dạng query.
- Video KIS và các quy định về capture video query.

KIS, Q&A và TRAKE được dùng làm workload chuẩn bị vì đã xuất hiện trong tài liệu/dữ liệu tham khảo 2026. Khi BTC phát hành luật Chung kết riêng, phải cập nhật plan và benchmark theo luật mới trước khi tối ưu tiếp.

## 3. Luồng thi phải tối ưu

### 3.1. Textual KIS

    Mô tả sự kiện
      → hiểu query tiếng Việt
      → semantic/OCR/ASR/metadata retrieval
      → fusion/rerank
      → xem frame lân cận và timeline
      → video_id, frame_id

Ưu tiên recall cao trong top candidate nhỏ, candidate đúng xuất hiện sớm và UI cho phép xác minh nhanh.

### 3.2. Q&A/VQA

    Mô tả sự kiện + câu hỏi
      → locate event
      → thu thập frame/OCR/ASR lân cận
      → VLM/LLM reasoning
      → video_id, frame_id, answer

Phải đo riêng retrieval location và text answer. Chỉ coi câu Q&A hoàn chỉnh là đúng khi cả hai phần đúng.

### 3.3. TRAKE

    Chuỗi sự kiện
      → tách event
      → retrieve candidate cho từng event
      → gom theo cùng video
      → kiểm tra thứ tự thời gian
      → chọn chuỗi frame tốt nhất

Không coi việc tìm đúng từng frame rời rạc là đã giải được TRAKE.

### 3.4. Trợ lý tự động

    Query
      → router phân loại KIS/QA/TRAKE và modality
      → chọn tool
      → query decomposition/expansion
      → retrieve evidence
      → VLM/temporal verification
      → output có cấu trúc sẵn sàng submit

Chatbot hội thoại chung không phải mục tiêu. Agent chỉ có giá trị khi tăng tỷ lệ đúng hoặc giảm thời gian end-to-end trên query thi.

### 3.5. Video KIS

Chỉ duy trì khả năng chuẩn bị và workflow thủ công tối thiểu. Không đầu tư lớn vào capture/video-query pipeline cho đến khi BTC xác nhận có Video KIS và công bố các hành vi được phép.

## 4. Thứ tự ưu tiên phát triển

### P0 — Benchmark phản ánh đúng bài thi

- Chuẩn hóa cách chấm dataset KIS/QA/TRAKE hiện có mà không sửa file cấm.
- Báo Recall@1/@5/@10/@50, MRR hoặc rank của candidate đúng, không chỉ pass/fail top-50.
- Đo time-to-first-correct-candidate, p50/p95 latency và error/timeout rate.
- Q&A phải báo location accuracy, answer accuracy và full-answer accuracy.
- TRAKE phải kiểm tra cùng video, đủ event và đúng thứ tự.
- Benchmark tự động phải chấm output cuối, không chỉ việc agent gọi được tool.
- Đổi dung sai frame/thời gian theo luật chính thức ngay khi có; không mặc định ±150 giây là luật Chung kết.

### P1 — Retrieval accuracy và candidate quality

- Semantic retrieval cho tiếng Việt/tiếng Anh.
- Query decomposition cho mô tả nhiều sự kiện.
- OCR, ASR và metadata search.
- Hybrid fusion/reranking giữa semantic, OCR, ASR, metadata và object evidence.
- Query expansion chỉ khi benchmark chứng minh recall/rank tốt hơn.
- Ưu tiên accuracy/rank trước micro-optimization cache đã dưới ngưỡng cảm nhận.

### P2 — TRAKE và temporal retrieval

- Candidate theo từng event.
- Same-video aggregation.
- Thứ tự thời gian và khoảng cách hợp lý.
- Sequence/contact sheet để người hoặc VLM xác minh.
- Output đúng schema nhiều frame.

### P3 — Q&A/VLM reasoning

- Chỉ gọi VLM trên candidate đã retrieve tốt.
- Kết hợp frame, OCR, ASR và context lân cận.
- Giới hạn tool/model budget để tránh timeout.
- Đo hallucination, answer format và khả năng trích dẫn video/frame.

### P4 — Agent router và chế độ tự động

- Phân biệt query semantic, OCR, ASR, QA và temporal.
- Chọn ít tool nhất nhưng đủ evidence.
- Tự động query decomposition và reranking.
- Trả output cấu trúc, không phụ thuộc parse văn xuôi mong manh.
- Có timeout, fallback và kết quả tốt nhất hiện có khi model/tool lỗi.

### P5 — UI thao tác thi và submission

- Candidate grid hiển thị nhanh, dễ so sánh.
- Timeline, context, filmstrip và preview video nhanh.
- Hiển thị OCR/ASR/metadata ngay tại candidate.
- Phím tắt, bookmark, lịch sử query và copy video/frame.
- Builder KIS/QA/TRAKE và format submission đúng.
- Khi BTC công bố server chấm, thêm integration test cho submit/response/retry.

### P6 — Độ ổn định phục vụ giờ thi

- Startup/health của model, DB, vector, MCP và agent.
- Chạy được từ môi trường thi dự kiến.
- Không crash, memory leak hoặc cache tăng không giới hạn trong một phiên thi.
- Có smoke test/offline fallback cho phụ thuộc mạng.
- Chỉ xử lý bảo mật, config và technical debt khi chúng có thể gián đoạn bài thi, làm sai output hoặc vi phạm quy định.

## 5. Những hướng không tự động theo đuổi

Không mở vòng tối ưu riêng cho các nội dung sau, trừ khi có bằng chứng chúng ảnh hưởng luồng thi:

- Micro-optimization cho cache hit đã dưới vài mili-giây.
- Tối ưu repeated query/identical upload nếu không có trace cho thấy workload thi lặp như vậy.
- Refactor, formatting, lint, type checking hoặc technical debt không liên quan lỗi thi.
- Security hardening chung như auth/rate limit/CORS/SSRF nếu hệ thống chỉ chạy local và rủi ro đó không xuất hiện trong môi trường thi. Vẫn phải sửa nếu quy định triển khai hoặc luồng tự động yêu cầu.
- Endpoint Supabase/Drive hoặc tính năng frontend không được dùng khi thi.
- Chatbot conversation, persona hoặc Markdown presentation không tăng accuracy query thi.
- Tính năng dựa trên luật 2025 nhưng chưa được xác nhận cho 2026.
- Thay model/index tốn kém khi chưa có thử nghiệm nhỏ chứng minh tiềm năng accuracy.

Benchmark cache/path/config vẫn được giữ làm regression guardrail, nhưng không được dùng để biện minh cho một vòng tối ưu mới nếu metric thi chính không đổi.

## 6. Benchmark và vai trò

### Benchmark quyết định giữ/rollback

- tools/benchmark.py: KIS/QA/TRAKE retrieval. Cần nâng cấp thêm rank/Recall@K và temporal metrics.
- tools/benchmark_chatbot.py: end-to-end API chat, candidate, answer, latency, error, token/cost. Chỉ dùng để kết luận khi Agy/MCP/model sẵn sàng và không có lỗi môi trường.
- Benchmark UI/operator hoặc submission phải được tạo trước khi tối ưu các luồng này.

### Regression guardrail

- tools/benchmark_semantic_cache.py: cache semantic và consistency ranking.
- tools/benchmark_similar.py: similar-by-vector, invalid ID và prefix cache.
- tools/benchmark_fuzzy_cache.py: fallback OCR/ASR, cache và video filter.
- tools/benchmark_image_cache.py: repeated/mixed-top-K image search.
- tools/benchmark_runtime_paths.py: metadata không phụ thuộc launch CWD.
- tools/benchmark_database_config.py: engine/MCP tôn trọng DB_PATH.
- compileall, smoke test, profiler: bảo vệ syntax/runtime và xác định bottleneck.

Guardrail phải pass sau thay đổi liên quan, nhưng giảm latency của guardrail không tự động có nghĩa kết quả thi tốt hơn.

## 7. Cổng tác động cuộc thi

Trước mỗi vòng phải trả lời rõ:

1. Thay đổi phục vụ KIS, Q&A, TRAKE, agent tự động hay UI/submission nào?
2. Nó cải thiện accuracy, rank, time-to-first-correct hay độ ổn định nào?
3. Benchmark nào đo đúng tác động đó?
4. Workload có khả năng xuất hiện ở Chung kết 2026 hay chỉ là tính năng chung?
5. Nếu không làm, rủi ro mất điểm hoặc mất thời gian thi là gì?

Nếu không trả lời được, không bắt đầu vòng.

## 8. File hỗ trợ

- AI_Challenge_2026_Chung_Ket.md: phạm vi cuộc thi và mức độ xác nhận của thông tin.
- PROJECT_CONTEXT.md: kiến trúc, trạng thái và cách chạy hiện tại.
- CHANGELOG.md: lịch sử thay đổi, benchmark và rollback.
- answerAndQuestion.jsonl: dataset đánh giá hiện tại, chỉ đọc.
- Các benchmark trong mục 6.

Mỗi thành phần mới phải có cách đo phù hợp trước khi tối ưu logic của thành phần đó.

## 9. File cấm sửa

Không được sửa, xóa hoặc ghi đè:

- video_index_v2.db
- video_fps_map.json
- video_drive_metadata.json
- translation_cache.db
- frame_map_supabase.json
- answerAndQuestion.jsonl
- all_vectors.npy
- .env

Có thể tạo script builder/migration hoặc artifact dẫn xuất mới nếu cần cho cuộc thi, nhưng không được ghi đè các file trên. Phải benchmark artifact mới và ghi rõ cách tái tạo.

## 10. Quy trình một vòng tối ưu

Mỗi vòng chỉ có một ý định thay đổi, nhưng có thể sửa nhiều file nếu cùng phục vụ ý định đó.

### Bước 1 — Đọc bối cảnh

- Đọc AI_Challenge_2026_Chung_Ket.md, PROJECT_CONTEXT.md và toàn bộ CHANGELOG.md.
- Xác định thông tin nào là chính thức, tham khảo hoặc chưa xác nhận.
- Không lặp hướng đã thất bại nhiều lần nếu không có cách tiếp cận khác hẳn.

### Bước 2 — Qua cổng tác động cuộc thi

- Trả lời năm câu trong mục 7.
- Xác định query type, luồng manual/automatic, metric chính và benchmark.
- Nêu kỳ vọng cải thiện cụ thể.

### Bước 3 — Khám phá sơ bộ

- Chỉ thực hiện khi có nhiều hướng cùng mục tiêu.
- Dùng thử nghiệm nhỏ, profiler hoặc ablation để loại hướng yếu.
- Không sửa file cấm và không coi kết quả thăm dò là kết luận chính thức.

### Bước 4 — Đo baseline

- Chạy benchmark quyết định phù hợp với query thi.
- Ghi accuracy/rank/time-to-first-correct/end-to-end latency/error.
- Chạy guardrail liên quan; không cần chạy mọi benchmark.
- Dùng cùng dataset, config, model, top-K và tiêu chí chấm trước/sau.

### Bước 5 — Tạo checkpoint

- Bắt buộc tạo git commit checkpoint trước thay đổi chính thức.
- Không stage hoặc ghi đè thay đổi có sẵn của người dùng ngoài phạm vi.

### Bước 6 — Thực hiện thay đổi

- Chỉ sửa file cần cho một ý định đã công bố.
- Không tiện tay refactor, hardening hoặc tối ưu phần không liên quan.
- Lỗi phụ có ảnh hưởng hành vi phải tách sang vòng khác và qua lại cổng tác động cuộc thi.

### Bước 7 — Đo lại

- Chạy lại đúng benchmark và config baseline.
- Kiểm tra ID/frame/answer/sequence, không chỉ latency.
- Chạy smoke/compile/guardrail liên quan.

### Bước 8 — Giữ hoặc rollback

Chỉ giữ khi:

- Metric thi chính tốt hơn rõ ràng; hoặc
- Một lỗi có thể phá luồng thi được sửa và benchmark chuyển fail → pass;
- Accuracy/output và guardrail liên quan không hồi quy.

Ngưỡng để coi metric thi chính tốt hơn rõ ràng:

- Retrieval KIS/Q&A/TRAKE trên dataset cố định: accuracy hoặc Recall@K tổng tăng ít nhất **2 điểm phần trăm** (với bộ hiện tại 57 case/63 target, tương đương ít nhất 2 case/target đúng thêm), không mất case đúng cũ và không giảm metric của query type khác. Nếu dùng rank làm metric quyết định, MRR phải tăng ít nhất **0,02** và rank candidate đúng cải thiện trên ít nhất 2 case độc lập; không dùng một case đơn lẻ để kết luận. Với thay đổi chỉ nhắm tốc độ, latency end-to-end hoặc TTFC trên cùng tập case phải giảm ít nhất **10%**, accuracy/rank/output giữ nguyên; đo ít nhất 3 lượt baseline và 3 lượt sau với cùng config, so median giữa các lượt và yêu cầu p95 không tăng quá **5%**. Không dùng riêng cache micro-benchmark để đạt ngưỡng latency.
- Agent/VLM và phép đo stochastic: chạy ít nhất **5 lượt độc lập cho mỗi cấu hình**, session tách biệt, báo trung bình và độ lệch chuẩn theo lượt. Chỉ kết luận tốt hơn khi chênh lệch metric chính vượt **2 lần độ lệch chuẩn của baseline** và khoảng tin cậy 95% của chênh lệch không chứa 0; nếu mục tiêu là latency thì còn phải đạt mức giảm ít nhất 10% end-to-end hoặc TTFC. Kiểm tra theo case để tránh một vài case che hồi quy của các case khác.
- Nếu không phân biệt chắc chênh lệch thật với nhiễu, **chưa đủ bằng chứng để giữ**: chạy thêm lượt độc lập để xác nhận; nếu vẫn chưa đạt ngưỡng thì rollback thay đổi thử nghiệm. Ngoại lệ fail → pass cho lỗi phá luồng thi vẫn cần benchmark tái lập và guardrail không hồi quy.

Rollback về checkpoint của chính vòng khi accuracy/rank xấu hơn, latency thi xấu rõ ràng, output sai, benchmark không đáng tin cậy hoặc hệ thống crash.

Không giữ thay đổi chỉ vì cache micro-benchmark nhanh hơn nếu workload thi chính không hưởng lợi.

### Bước 9 — Ghi log

Thêm vào CHANGELOG.md:

- Query type/luồng thi được nhắm tới.
- Thay đổi, vị trí và mục đích.
- Benchmark/config.
- Số liệu trước/sau.
- Guardrail.
- Quyết định giữ/rollback và checkpoint.
- Sửa phụ nếu có.

### Bước 10 — Cập nhật bối cảnh

Cập nhật PROJECT_CONTEXT.md nếu kiến trúc, model, API, workflow thi, benchmark hoặc cách chạy thay đổi.

## 11. Điều kiện dừng

Dừng chuỗi và báo cáo khi:

- Đạt số vòng người dùng yêu cầu.
- Tổng thời gian chạy liên tục của chuỗi đạt **4 giờ** kể từ lúc bắt đầu chuẩn bị, trừ khi người dùng chỉ định giới hạn khác; hoàn tất quyết định giữ/rollback và ghi log cho vòng đang chạy rồi dừng, không mở vòng mới.
- Ba vòng liên tiếp không cải thiện metric thi chính.
- Không còn mục tiêu P0–P6 có bằng chứng tác động đến cuộc thi **sau khi rà toàn bộ mục 14**; không được kết luận hết hướng nếu vẫn có ít nhất một đề xuất ở trạng thái `đủ điều kiện mở vòng`. Liệt kê các đề xuất còn ở trạng thái `ý tưởng cần kiểm chứng` hoặc `đang bị chặn` trong báo cáo tổng kết.
- Benchmark thi chính không đủ tin cậy; vòng kế tiếp chỉ được sửa benchmark, không tối ưu runtime.
- Cần sửa file cấm, cần luật chính thức hoặc cần quyết định có thể phá vỡ toàn hệ thống.

Cứ sau **mỗi 5 vòng** đã hoàn tất, tạm dừng để chạy một lượt kiểm tra end-to-end toàn hệ thống trên các luồng thi thủ công và tự động đang triển khai (query → retrieval → UI/agent → output ID/frame/answer/sequence sẵn sàng submit cho KIS/Q&A/TRAKE), ngoài benchmark từng phần. Chỉ mở vòng tiếp theo khi kiểm tra pass; nếu fail hoặc không thể xác minh, dừng và báo cáo.

Không tiếp tục tạo vòng chỉ để tăng coverage của thành phần không nằm trong luồng thi.

## 12. Yêu cầu báo cáo

Sau mỗi vòng báo cáo:

- Query type/luồng thi được tối ưu.
- Tác động dự kiến đến điểm hoặc thời gian thi.
- Thay đổi chính và sửa phụ.
- Benchmark/config đã chạy.
- Accuracy/rank/time-to-first-correct/end-to-end latency/error trước và sau.
- Guardrail và output correctness.
- Quyết định giữ hay rollback; checkpoint/commit.
- Có cập nhật PROJECT_CONTEXT.md hay không.
- Số vòng giữ/rollback/không triển khai và lý do dừng nếu kết thúc chuỗi.

## 13. Nguyên tắc cuối cùng

Khi phải chọn giữa:

    benchmark cache đẹp hơn

và:

    candidate đúng xếp hạng cao hơn,
    người thi xác minh nhanh hơn,
    hoặc agent trả đúng output nhiều hơn

luôn ưu tiên nhóm thứ hai.

## 14. Backlog đề xuất tăng độ chính xác và tốc độ

Các mục dưới đây là hướng phát triển tiềm năng, không phải thay đổi được phép triển khai ngay. Mỗi mục vẫn phải qua cổng tác động cuộc thi, có baseline, checkpoint và benchmark trước/sau theo mục 10. Thực hiện theo thứ tự ưu tiên; nếu benchmark tiền đề chưa đạt thì không chuyển sang sửa runtime.

### 14.1. P0 — Benchmark riêng cho VLM chọn candidate

- Trạng thái: **đủ điều kiện mở vòng P0 benchmark; đang bị chặn tối ưu runtime**; xem vòng 96–99 trong `CHANGELOG.md`. Cổng 5 lượt, so sánh CI và chấm full answer Q&A đã có; còn thiếu tập case model thật đa dạng, đủ lượt độc lập và xác minh session.
- Tạo tập candidate cố định gồm frame đúng và các hard negative gần giống từ cùng chủ đề/video khác; không để retrieval hoặc lịch sử Agy làm thay đổi đầu vào giữa các lượt.
- Chấm Top-1 accuracy, Recall@3/@5, MRR, tỷ lệ chọn sai nhưng tự tin cao, latency p50/p95 và chi phí nếu có.
- Bao phủ ít nhất: cảnh nấu ăn gần giống nhau, đám đông/trường học, OCR, ASR, Q&A và chuỗi nhiều sự kiện.
- Dùng benchmark này để quyết định mọi thay đổi prompt VLM, contact-sheet layout, model hoặc visual reranker. Không dùng `tools/benchmark_chatbot.py` một mình để kết luận khi chưa tách được lỗi retrieval và lỗi VLM chọn candidate.
- Ưu tiên cao nhất hiện tại; xem vòng 91 trong `CHANGELOG.md` để biết bằng chứng.

### 14.2. P0 — Benchmark agent phân tầng và có lặp lại

- Trạng thái: **đủ điều kiện mở vòng P0 benchmark; đang bị chặn tối ưu runtime**; xem vòng 95 trong `CHANGELOG.md`. Benchmark agent nhiều lượt độc lập, session được xác minh và đại diện nhiều query type vẫn chưa hoàn thành.
- Tạo tập đánh giá nhỏ nhưng đại diện cho KIS đơn sự kiện, KIS nhiều sự kiện, OCR, ASR, Q&A và TRAKE; sau khi ổn định mới mở rộng toàn bộ dataset.
- Mỗi cấu hình agent chạy nhiều lượt độc lập với session namespace khác nhau để đo trung bình, độ lệch và tỷ lệ thắng theo case; không kết luận từ một lượt stochastic duy nhất.
- Báo riêng primary candidate Top-1, candidate rank/Recall@K, full-answer accuracy, TTFC, end-to-end latency, timeout/error và số tool call.
- Output cuối phải phân biệt rõ `primary_submission` với candidate tham khảo; chỉ primary candidate được tính Top-1 sẵn sàng submit.
- Chỉ tối ưu prompt/router/model sau khi benchmark này phân biệt được thay đổi thật với dao động Agy.

### 14.3. P1/P6 — Artifact FTS dẫn xuất cho OCR/ASR

- Trạng thái: **đủ điều kiện mở vòng benchmark/artifact dẫn xuất**; DB hiện thiếu FTS và fallback cold chậm (vòng 66, 79–83). Chưa đủ điều kiện thay runtime khi artifact mới chưa được benchmark end-to-end.
- Tạo builder tái lập được để sinh một database FTS dẫn xuất mới từ `video_index_v2.db` ở chế độ chỉ đọc; tuyệt đối không ghi vào hoặc thay thế file cấm.
- Artifact mới phải có version, schema, checksum nguồn, lệnh tái tạo và đường dẫn cấu hình riêng; runtime phải fallback an toàn về artifact hiện tại nếu thiếu.
- Benchmark trước khi nối production: Recall@K/MRR của OCR, ASR và `search_video_evidence`; p50/p95/TTFC; correctness của video filter; startup và kích thước artifact.
- Chỉ giữ nếu evidence/candidate rank không giảm và latency fallback scan giảm rõ ràng trên workload đa term. Không giữ chỉ vì truy vấn SQL nhanh hơn nhưng output agent không hưởng lợi.

### 14.4. P1 — Ablation retrieval đa ngôn ngữ nhỏ trước khi đổi model/index

- Trạng thái: **đang bị chặn** bởi thiếu model dịch offline/model đa ngôn ngữ local và quyết định dữ liệu/nguồn ngoài; xem vòng 76. Chỉ mở thăm dò nhỏ khi có tài nguyên hợp lệ.
- Dùng một tập query Việt–Anh đại diện và artifact embedding dẫn xuất nhỏ để so OpenCLIP hiện tại với model đa ngôn ngữ hoặc phương án dịch offline; chưa rebuild toàn bộ 177.321 vector ở bước thăm dò.
- Đo Recall@1/@5/@10/@50, MRR, TTFC, latency encode, RAM và mức bảo toàn toàn bộ semantic hit hiện có.
- Kiểm tra riêng query tiếng Việt không dấu, câu dài nhiều mệnh đề và query chứa tên riêng/chữ trên màn hình.
- Chỉ cho phép build index đầy đủ khi ablation tăng accuracy/rank rõ ràng và có kế hoạch tái tạo artifact; nếu chỉ nhanh hơn hoặc chỉ tốt trên vài case cherry-pick thì dừng.

### 14.5. P1 — Reranker candidate-level có hard negative

- Trạng thái: **đang bị chặn** bởi thiếu manifest VLM nhiều loại case, hard negative được xác minh và validation tách biệt; xem 14.1.
- Sau khi có benchmark VLM/retrieval cố định, thử rerank top candidate bằng đặc trưng semantic, OCR, ASR, object, độ phủ mệnh đề và temporal consistency; không thay retrieval gốc trong cùng vòng.
- Tập validation phải tách khỏi tập dùng chọn trọng số, đặc biệt với các video nấu ăn gần giống nhau để tránh overfit `answerAndQuestion.jsonl`.
- Metric quyết định là Top-1/MRR/time-to-first-correct; Recall@50 của retrieval gốc là guardrail bắt buộc.
- Có thể thử cross-encoder/VLM reranker trên top-N nhỏ, nhưng phải đo latency/cost và có fallback deterministic khi model lỗi.

### 14.6. P1/P5 — Đa dạng hóa candidate theo video và thời gian

- Trạng thái: **ý tưởng cần kiểm chứng**; chưa có benchmark thời gian operator/VLM nhìn thấy candidate đúng trên grid đa dạng.
- Thử giới hạn frame gần trùng nhau trong cùng video và dành quota cho nhiều video/mốc thời gian trong top candidate hoặc contact sheet.
- Mục tiêu là tăng số hard candidate khác nhau mà operator/VLM có thể kiểm tra trong một màn hình, không chỉ làm danh sách trông đa dạng hơn.
- Benchmark phải báo correct rank, Recall@K, số video đúng/khác nhau trong top-K, thời gian người/VLM thấy candidate đúng và latency dựng grid.
- Rollback nếu diversification đẩy frame đúng xuống rank thấp hơn hoặc làm mất chuỗi frame cần cho TRAKE.

### 14.7. P2 — Temporal reranker cho TRAKE

- Trạng thái: **ý tưởng cần kiểm chứng**; regression ordered sequence đã có, nhưng chưa có benchmark candidate sequence cố định với metric rank/TTFC cho reranker.
- Tạo benchmark candidate sequence cố định trước khi sửa logic: đủ event, cùng video, frame tăng nghiêm ngặt, khoảng cách thời gian và hard negative đảo thứ tự/dùng trùng frame.
- Thử dynamic programming hoặc beam search trên candidate từng event, có giới hạn khoảng cách mềm thay vì ghép độc lập.
- Đo sequence accuracy, event coverage, sequence MRR, TTFC và latency; không coi event-rank riêng là thành công.
- Chỉ mở rộng contact/sequence sheet sau khi sequence reranker chứng minh có candidate tốt hơn cho người hoặc VLM kiểm tra.

### 14.8. P3 — Q&A evidence pack cố định

- Trạng thái: **đang bị chặn** bởi thiếu tập Q&A candidate đã locate đúng và nhãn answer model thật; scorecard Q&A full answer mới được khóa ở vòng 99.
- Với mỗi candidate location, dựng gói evidence có frame trung tâm, frame lân cận, OCR, ASR và timestamp; giới hạn kích thước/budget cố định.
- Benchmark tách location accuracy, answer accuracy khi location đã đúng, full-answer accuracy, hallucination và format output.
- So sánh single-frame với multi-frame/VLM chỉ trên candidate đã retrieve đúng; không dùng VLM lớn để che lỗi retrieval.
- Giữ thay đổi khi full-answer accuracy tăng và latency vẫn nằm trong budget thi dự kiến.

### 14.9. P4 — Output có cấu trúc sẵn sàng submit

- Trạng thái: **đang bị chặn** bởi benchmark agent nhiều lượt/primary output chưa đủ coverage theo 14.2; chưa có schema submission chính thức 2026.
- Định nghĩa schema riêng cho KIS, Q&A và TRAKE gồm primary candidate, answer/sequence, confidence và candidate dự phòng; không parse văn xuôi để xác định đáp án chính.
- Backend phải validate ID/frame/order và stream được best-so-far hợp lệ khi agent timeout.
- Benchmark schema validity, primary Top-1/full-answer accuracy, tỷ lệ fallback hợp lệ, latency đến primary candidate và lỗi parse.
- Không tăng số candidate trong output chỉ để làm benchmark any-hit đẹp hơn; primary candidate vẫn là metric quyết định.

### 14.10. P5 — Benchmark thao tác operator và submission

- Trạng thái: **ý tưởng cần kiểm chứng**; benchmark mode smart hiện 4/4 contract nhưng chưa đo thao tác/timing operator hay giao thức submit chính thức.
- Mở rộng benchmark UI hiện tại để đo thời gian từ nhập query đến candidate đúng đầu tiên, số click/keystroke để preview và copy/submit KIS, Q&A, TRAKE.
- Thử shortcut, bookmark, compare view, evidence overlay và prefetch filmstrip chỉ khi scenario benchmark tương ứng tồn tại.
- Khi BTC công bố giao thức server, thêm integration test format request/response, retry, duplicate submission, timeout và thông báo lỗi trước khi tối ưu submission.
- Metric quyết định là time-to-first-correct/ready-to-submit và tỷ lệ output hợp lệ, không phải thời gian render một component riêng lẻ.

### 14.11. P6 — Fast path có ảnh hưởng trực tiếp giờ thi

- Trạng thái: **ý tưởng cần kiểm chứng**; thiếu trace cold/warm end-to-end để xác định bottleneck có ý nghĩa giờ thi.
- Đo trace cold/warm cho startup model, translation, semantic retrieval, OCR/ASR evidence, tải ảnh contact sheet, VLM và stream output; chỉ tối ưu nút chiếm tỷ trọng end-to-end đáng kể.
- Ưu tiên translation offline/prewarm, batch/parallel retrieval có giới hạn, thumbnail/contact-sheet cache theo nội dung và local fallback cho ảnh khi trace chứng minh đây là bottleneck.
- Thêm readiness check thực cho DB/vector/model/Agy/MCP và một smoke query có output ID/frame hợp lệ; health không được chỉ kiểm tra file tồn tại.
- Benchmark p50/p95/timeout và accuracy/output trước/sau; cache hit nhanh hơn không đủ để giữ nếu TTFC/end-to-end không đổi.

### 14.12. Thứ tự thực hiện đề xuất

1. Benchmark VLM candidate selection.
2. Benchmark agent phân tầng, lặp độc lập và primary output.
3. Artifact FTS dẫn xuất cho OCR/ASR.
4. Ablation retrieval đa ngôn ngữ nhỏ.
5. Candidate reranker và diversification.
6. Temporal reranker TRAKE và Q&A evidence pack.
7. Structured output, operator/submission benchmark và fast path theo trace.

Không mở lại heuristic chọn term evidence hoặc rule prompt nếu không có benchmark candidate-level mới hoặc cách tiếp cận khác hẳn; xem các vòng 91–92 trong `CHANGELOG.md` để biết lịch sử. Không thay model/index đầy đủ, rebuild artifact lớn hoặc tối ưu cache trước khi bước ablation/trace tương ứng chứng minh tiềm năng.

### 14.13. Quy tắc ghi nhận đề xuất cho session sau

- Mỗi session phải đọc toàn bộ mục 14 trước khi chọn vòng tối ưu mới; đối chiếu `CHANGELOG.md` để biết đề xuất nào đã thử, đã giữ, đã rollback hoặc không còn phù hợp.
- Nếu trong quá trình phân tích, benchmark, profiler, ablation hoặc triển khai phát hiện thêm một đề xuất có khả năng tăng accuracy, rank, time-to-first-correct, tốc độ end-to-end hoặc độ ổn định giờ thi, phải ghi đề xuất đó trực tiếp vào mục 14 trước khi kết thúc session, kể cả khi chưa đủ điều kiện triển khai ngay.
- Mỗi đề xuất mới phải ghi rõ: query type/luồng thi được phục vụ, vấn đề hoặc bằng chứng quan sát được, tác động kỳ vọng, benchmark cần có, metric quyết định, điều kiện bắt đầu và rủi ro/điều kiện rollback.
- Phân biệt rõ `ý tưởng cần kiểm chứng`, `đã có bằng chứng sơ bộ`, `đủ điều kiện mở vòng`, `đang bị chặn`, `đã triển khai`, `đã rollback` và `loại bỏ`; không trình bày giả thuyết như kết luận đã xác nhận.
- Cập nhật đề xuất hiện có thay vì tạo mục trùng lặp. Khi trạng thái thay đổi, ghi số vòng/commit liên quan trong `CHANGELOG.md`; không xóa lịch sử hướng đã thất bại.
- Đề xuất từ session trước không tự động được phép triển khai. Session sau vẫn phải qua cổng tác động cuộc thi ở mục 7 và quy trình 10 bước ở mục 10.
- Trước khi dừng vì “không còn hướng”, session phải rà lại mục 14. Chỉ kết luận không còn hướng khi không có đề xuất nào ở trạng thái `đủ điều kiện mở vòng`; các mục `ý tưởng cần kiểm chứng` hoặc `đang bị chặn` phải được báo rõ trong tổng kết.
