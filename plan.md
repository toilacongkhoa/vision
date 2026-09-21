# Kế hoạch tự tối ưu hóa dự án Vision

## Mục tiêu

- Tăng tốc độ xử lý (thời gian phản hồi API search, AI Assistant, embedding...).
- Tăng độ chính xác kết quả tìm kiếm (đối chiếu với `answerAndQuestion.jsonl`).
- Không cần tiết kiệm token/compute khi phát triển và khi hệ thống chạy thi thật — ưu tiên chất lượng và tốc độ hơn chi phí.
- Mọi thay đổi phải được đo lường bằng số liệu cụ thể (benchmark), không dựa trên cảm tính "chắc là tốt hơn".

## Hai track tối ưu độc lập

Hệ thống Vision có hai tầng cần được đo và tối ưu riêng. Khi bắt đầu một vòng, phải ghi rõ đang chạy **Track A — Retrieval** hoặc **Track B — Chatbot (Agy)**. Một vòng chỉ được chạy trên **một** track; không gộp thay đổi, benchmark hoặc kết luận của hai track.

### Track A — Retrieval optimization

Track A bao phủ pipeline tìm kiếm trực tiếp:

`FastTranslator → OpenCLIP → NumPy → SQLiteSearchEngine`

Track này dùng `tools/benchmark.py` với `answerAndQuestion.jsonl`, phân biệt KIS/QA/TRAKE, đo độ chính xác và thời gian trung bình. So khớp `video_id` và `frame_idx` theo thời gian `frame_idx / fps` trong `video_fps_map.json`, với dung sai **±150 giây**. Đây là quy trình retrieval hiện hành và không đo chất lượng chatbot Agy.

### Track B — Chatbot (Agy) optimization

Track B bao phủ API `POST /api/v1/chat`, gồm model/prompt routing, Agy session, MCP orchestration và tổng hợp câu trả lời. Track này dùng benchmark riêng `tools/benchmark_chatbot.py`, không sửa `tools/benchmark.py` để gộp hai tầng.

Benchmark Track B cần ghi nhận:

- Độ chính xác câu trả lời so với đáp án mẫu; với bộ `answerAndQuestion.jsonl`, QA dùng `text_answer`, còn bộ hội thoại riêng có thể cung cấp `expected_answer`/`reference_answer`.
- Độ chính xác các cặp `VideoID, FrameIdx` chatbot tổng hợp qua MCP, dùng cùng dung sai **±150 giây** của Track A; TRAKE phải giữ đúng thứ tự chuỗi.
- Thời gian phản hồi trung bình của stream chatbot.
- Tỉ lệ lỗi gồm HTTP failure, timeout, stream `[ERROR]` và MCP/tool failure được chatbot báo ra.
- Token usage và chi phí ước tính nếu API/Agy trả usage; nếu không có usage, benchmark phải báo rõ là chưa xác định, không coi là 0.

`benchmark_chatbot.py` có thể dùng `answerAndQuestion.jsonl` như bộ smoke/evaluation grounding hiện tại hoặc nhận một JSONL hội thoại riêng qua `--dataset`; không được sửa `answerAndQuestion.jsonl`.

## File hỗ trợ

- `PROJECT_CONTEXT.md`: trạng thái/kiến trúc dự án hiện tại — đọc đầu mỗi vòng để nắm bối cảnh.
- `plan.md`: file này — quy trình thực hiện tối ưu, có thể chỉnh sửa nếu quy trình cần cải tiến.
- `CHANGELOG.md`: lịch sử từng thay đổi đã thực hiện, kèm kết quả benchmark trước/sau. **Bắt buộc tạo nếu chưa có.**
- `answerAndQuestion.jsonl`: dữ liệu câu hỏi — đáp án đúng, dùng làm bộ đánh giá độ chính xác.
- `benchmark.py` (hoặc script tương đương): script tự động chạy tất cả câu hỏi trong `answerAndQuestion.jsonl`, đo thời gian phản hồi và tính % kết quả đúng. **Bắt buộc tạo nếu chưa có**, đặt ở thư mục scripts/ hoặc tools/.
- `benchmark_chatbot.py`: benchmark riêng cho API `/api/v1/chat`, stream text SSE, cặp VideoID/FrameIdx, thời gian, lỗi, token và chi phí ước tính của Track B.

## Danh sách file KHÔNG được sửa/xóa/ghi đè

- `video_index_v2.db`
- `video_fps_map.json`
- `video_drive_metadata.json`
- `translation_cache.db`
- `frame_map_supabase.json`
- `answerAndQuestion.jsonl`
- `all_vectors.npy`
- `.env`

## Quy trình một vòng tối ưu

Mỗi vòng chỉ thực hiện **MỘT thay đổi cụ thể trên MỘT track**. Không gộp nhiều thay đổi lớn trong cùng một vòng — nếu benchmark thay đổi (tốt hoặc xấu), phải biết chính xác nguyên nhân do đâu.

### Chọn track và benchmark tương ứng

1. Ghi rõ ở đầu vòng: `Track A — Retrieval` hoặc `Track B — Chatbot (Agy)`.
2. Track A chạy `tools/benchmark.py` trên `answerAndQuestion.jsonl` và giữ ngưỡng frame ±150 giây.
3. Track B chạy `tools/benchmark_chatbot.py` trên API `/api/v1/chat`; không dùng kết quả Track A để kết luận chất lượng model/prompt Agy.
4. Nếu Track B cần bộ câu hội thoại có ngữ cảnh mà `answerAndQuestion.jsonl` không cung cấp, tạo một JSONL mới, chỉ đọc dataset cũ và không chỉnh sửa file bị cấm.

### Các bước chung của một vòng

1. **Đọc bối cảnh**
   - Đọc `PROJECT_CONTEXT.md` để nắm kiến trúc/trạng thái hiện tại.
   - Đọc `CHANGELOG.md` để biết các vòng trước đã thử gì, tránh lặp lại hướng đã thất bại hoặc đã áp dụng rồi.

2. **Đo baseline**
   - Track A: chạy `benchmark.py` trên `answerAndQuestion.jsonl`.
   - Track B: chạy `benchmark_chatbot.py` với API `/api/v1/chat` và bộ câu hỏi đã chọn.
   - Ghi lại toàn bộ metric của track đang chạy làm baseline để so sánh.
   - Nếu benchmark tương ứng chưa có, việc đầu tiên cần làm là tạo nó trước khi tối ưu bất cứ gì khác.

3. **Đề xuất một thay đổi**
   - Chọn một điểm tối ưu cụ thể (ví dụ: cache kết quả embedding, tối ưu index tìm kiếm, sửa prompt AI Assistant, giảm số lần gọi API không cần thiết, song song hóa xử lý...).
   - Nêu rõ mục tiêu của thay đổi này là cải thiện tốc độ hay độ chính xác, và kỳ vọng cải thiện ở đâu.

4. **Backup trước khi sửa**
   - Bắt buộc `git commit` (hoặc backup thủ công) trạng thái hiện tại trước khi sửa, để có thể rollback nếu cần.

5. **Thực hiện thay đổi**
   - Sửa code/thêm file theo đúng phạm vi đã đề xuất ở bước 3.
   - Không động vào các file bị cấm ở danh sách trên.

6. **Đo lại sau khi sửa**
   - Chạy lại benchmark của đúng track, so sánh với baseline ở bước 2.
   - Kiểm tra hệ thống vẫn chạy đúng (không lỗi crash, API vẫn phản hồi hợp lệ).

7. **Quyết định giữ hay rollback**
   - Nếu kết quả tốt hơn (nhanh hơn và/hoặc chính xác hơn, không phá vỡ tính năng khác): giữ thay đổi.
   - Nếu kết quả tệ hơn hoặc gây lỗi: rollback về bản backup ở bước 4.

8. **Ghi log**
   - Thêm một mục mới vào `CHANGELOG.md`, dù giữ hay rollback, gồm:
     - Ngày/thời điểm
     - Thay đổi gì, ở đâu (file/function)
     - Để làm gì (mục tiêu)
     - Kết quả: benchmark trước → sau (số liệu cụ thể)
     - Giữ lại hay đã rollback

9. **Cập nhật PROJECT_CONTEXT.md**
   - Nếu thay đổi ảnh hưởng đến kiến trúc, tính năng, hoặc cách chạy hệ thống, cập nhật lại `PROJECT_CONTEXT.md` cho khớp.

## Quy tắc an toàn

- Không tự ý gộp nhiều thay đổi trong một vòng.
- Không tối ưu mà không đo benchmark trước/sau.
- Không xóa hoặc ghi đè `CHANGELOG.md` của các vòng trước — chỉ thêm mới.
- Không sửa các file bị cấm trong danh sách trên, trong bất kỳ trường hợp nào.
- Nếu một hướng tối ưu đã thử và rollback 2 lần trong `CHANGELOG.md`, không thử lại hướng đó nữa trừ khi có cách tiếp cận khác hẳn.

## Yêu cầu báo cáo sau mỗi vòng

AI chỉ cần báo cáo ngắn gọn:
- Track đã chạy (A — Retrieval hoặc B — Chatbot/Agy).
- Đã thay đổi gì, ở đâu, để làm gì.
- Kết quả benchmark trước/sau của đúng track (số liệu).
- Đã giữ lại hay đã rollback.
