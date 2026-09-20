# Kế hoạch tự tối ưu hóa dự án Vision

## Mục tiêu

- Tăng tốc độ xử lý (thời gian phản hồi API search, AI Assistant, embedding...).
- Tăng độ chính xác kết quả tìm kiếm (đối chiếu với `answerAndQuestion.jsonl`).
- Không cần tiết kiệm token/compute khi phát triển và khi hệ thống chạy thi thật — ưu tiên chất lượng và tốc độ hơn chi phí.
- Mọi thay đổi phải được đo lường bằng số liệu cụ thể (benchmark), không dựa trên cảm tính "chắc là tốt hơn".

## File hỗ trợ

- `PROJECT_CONTEXT.md`: trạng thái/kiến trúc dự án hiện tại — đọc đầu mỗi vòng để nắm bối cảnh.
- `plan.md`: file này — quy trình thực hiện tối ưu, có thể chỉnh sửa nếu quy trình cần cải tiến.
- `CHANGELOG.md`: lịch sử từng thay đổi đã thực hiện, kèm kết quả benchmark trước/sau. **Bắt buộc tạo nếu chưa có.**
- `answerAndQuestion.jsonl`: dữ liệu câu hỏi — đáp án đúng, dùng làm bộ đánh giá độ chính xác.
- `benchmark.py` (hoặc script tương đương): script tự động chạy tất cả câu hỏi trong `answerAndQuestion.jsonl`, đo thời gian phản hồi và tính % kết quả đúng. **Bắt buộc tạo nếu chưa có**, đặt ở thư mục scripts/ hoặc tools/.

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

Mỗi vòng chỉ thực hiện **MỘT thay đổi cụ thể**. Không gộp nhiều thay đổi lớn trong cùng một vòng — nếu benchmark thay đổi (tốt hoặc xấu), phải biết chính xác nguyên nhân do đâu.

1. **Đọc bối cảnh**
   - Đọc `PROJECT_CONTEXT.md` để nắm kiến trúc/trạng thái hiện tại.
   - Đọc `CHANGELOG.md` để biết các vòng trước đã thử gì, tránh lặp lại hướng đã thất bại hoặc đã áp dụng rồi.

2. **Đo baseline**
   - Chạy `benchmark.py` (hoặc script benchmark hiện có) trên `answerAndQuestion.jsonl`.
   - Ghi lại: thời gian phản hồi trung bình, % câu trả lời đúng — đây là baseline để so sánh.
   - Nếu chưa có script benchmark, việc đầu tiên cần làm là tạo nó trước khi tối ưu bất cứ gì khác.

3. **Đề xuất một thay đổi**
   - Chọn một điểm tối ưu cụ thể (ví dụ: cache kết quả embedding, tối ưu index tìm kiếm, sửa prompt AI Assistant, giảm số lần gọi API không cần thiết, song song hóa xử lý...).
   - Nêu rõ mục tiêu của thay đổi này là cải thiện tốc độ hay độ chính xác, và kỳ vọng cải thiện ở đâu.

4. **Backup trước khi sửa**
   - Bắt buộc `git commit` (hoặc backup thủ công) trạng thái hiện tại trước khi sửa, để có thể rollback nếu cần.

5. **Thực hiện thay đổi**
   - Sửa code/thêm file theo đúng phạm vi đã đề xuất ở bước 3.
   - Không động vào các file bị cấm ở danh sách trên.

6. **Đo lại sau khi sửa**
   - Chạy lại `benchmark.py`, so sánh với baseline ở bước 2.
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
- Đã thay đổi gì, ở đâu, để làm gì.
- Kết quả benchmark trước/sau (số liệu).
- Đã giữ lại hay đã rollback.