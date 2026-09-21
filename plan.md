# Kế hoạch tự tối ưu hóa dự án Vision

## Mục tiêu

- Tăng tốc độ xử lý của toàn bộ hệ thống Vision.
- Tăng độ chính xác của kết quả trên toàn bộ hệ thống Vision.
- Phạm vi bao gồm mọi thành phần có ảnh hưởng đến hai mục tiêu trên, như pipeline retrieval, chatbot Agy, API, MCP, model, prompt, cache và logic xử lý.
- Không cần tiết kiệm token hoặc compute trong quá trình phát triển và vận hành thử nghiệm; ưu tiên chất lượng và tốc độ.
- Mọi kết luận phải dựa trên số liệu benchmark cụ thể, không dựa trên cảm tính.

## File hỗ trợ

- `PROJECT_CONTEXT.md`: mô tả kiến trúc, trạng thái và cách vận hành hiện tại; phải đọc trước mỗi vòng.
- `plan.md`: quy trình tự tối ưu hóa này.
- `CHANGELOG.md`: lịch sử các thay đổi, benchmark trước/sau và quyết định giữ hoặc rollback; bắt buộc tạo nếu chưa có.
- `answerAndQuestion.jsonl`: bộ câu hỏi và đáp án dùng cho đánh giá retrieval hoặc các trường hợp phù hợp.
- `benchmark.py` hoặc script tương đương: benchmark pipeline retrieval, phân biệt KIS/QA/TRAKE, đo độ chính xác và thời gian phản hồi.
- `benchmark_chatbot.py`: benchmark API `/api/v1/chat`, đo câu trả lời, VideoID/FrameIdx, thời gian, lỗi, token và chi phí nếu có.
- Mỗi thành phần mới phải có benchmark phù hợp trước khi được tối ưu. Không tối ưu thành phần nếu chưa có cách đo đáng tin cậy cho thành phần đó.

## File cấm sửa

Không được sửa, xóa hoặc ghi đè các file sau:

- `video_index_v2.db`
- `video_fps_map.json`
- `video_drive_metadata.json`
- `translation_cache.db`
- `frame_map_supabase.json`
- `answerAndQuestion.jsonl`
- `all_vectors.npy`
- `.env`

## Quy trình một vòng tối ưu

Mỗi vòng chỉ được thực hiện **MỘT thay đổi cụ thể** trong một phần của hệ thống. Không gộp nhiều thay đổi lớn trong cùng một vòng để có thể xác định chính xác nguyên nhân khi benchmark thay đổi.

1. **Đọc bối cảnh**
   - Đọc toàn bộ `PROJECT_CONTEXT.md` để nắm kiến trúc và trạng thái hiện tại.
   - Đọc toàn bộ `CHANGELOG.md` để biết các hướng đã thử, kết quả và các hướng đã rollback.
   - Không lặp lại hướng đã thất bại nhiều lần, trừ khi có cách tiếp cận khác hẳn.

2. **Xác định phạm vi thay đổi**
   - Chọn đúng một điểm có khả năng cải thiện tốc độ hoặc độ chính xác.
   - Ghi rõ thay đổi nằm ở đâu, mục tiêu là gì và kỳ vọng cải thiện nào.
   - Xác định benchmark phù hợp với chính phần sẽ sửa. Ví dụ: sửa retrieval thì dùng `benchmark.py`; sửa chatbot thì dùng `benchmark_chatbot.py`; sửa thành phần mới thì phải có benchmark tương ứng.

3. **Đo baseline**
   - Chạy benchmark phù hợp trước khi sửa.
   - Ghi lại đầy đủ các số liệu cần thiết: độ chính xác, thời gian phản hồi, tỉ lệ lỗi, VideoID/FrameIdx, token, chi phí hoặc các metric khác mà benchmark cung cấp.
   - Không dùng kết quả của benchmark khác để kết luận cho phần đang sửa.

4. **Tạo điểm rollback**
   - Bắt buộc chạy `git commit` để lưu trạng thái hiện tại trước khi sửa.
   - Không dùng các thao tác phá hủy dữ liệu hoặc làm mất thay đổi của người dùng.

5. **Thực hiện thay đổi**
   - Chỉ sửa đúng một thay đổi đã đề xuất.
   - Không sửa các file cấm.
   - Không tranh thủ chỉnh sửa thêm các vấn đề khác trong cùng vòng.

6. **Đo lại sau khi sửa**
   - Chạy lại đúng benchmark đã dùng ở bước baseline, với cùng dataset, cấu hình và tiêu chí so sánh.
   - Kiểm tra thành phần liên quan vẫn khởi động và phản hồi hợp lệ.
   - So sánh số liệu trước và sau một cách cụ thể.

7. **Giữ hoặc rollback**
   - Nếu tốc độ nhanh hơn và/hoặc độ chính xác cao hơn, không gây lỗi hay phá vỡ tính năng khác: giữ thay đổi.
   - Nếu kết quả tệ hơn, benchmark lỗi, hệ thống crash hoặc phát sinh hồi quy: rollback về commit ở bước 4.
   - Không tự đánh giá là tốt hơn nếu không có số liệu benchmark hỗ trợ.

8. **Ghi log**
   - Thêm một mục mới vào `CHANGELOG.md` cho mọi vòng, dù giữ hay rollback.
   - Mục log phải ghi: ngày/thời điểm, thay đổi gì, ở đâu, để làm gì, benchmark trước/sau với số liệu cụ thể, và quyết định giữ hay rollback.

9. **Cập nhật bối cảnh**
   - Cập nhật `PROJECT_CONTEXT.md` nếu thay đổi ảnh hưởng đến kiến trúc, tính năng, model, API, cách chạy hoặc quy trình benchmark.

## Quy tắc an toàn

- Mỗi vòng chỉ có một thay đổi cụ thể.
- Luôn đo baseline trước khi sửa và đo lại sau khi sửa.
- Luôn tạo git commit trước khi sửa.
- Không sửa, xóa hoặc ghi đè các file trong danh sách cấm.
- Không xóa hoặc ghi đè lịch sử trong `CHANGELOG.md`; chỉ được thêm mục mới.
- Nếu một hướng tối ưu đã bị rollback nhiều lần theo `CHANGELOG.md`, không thử lại hướng đó trừ khi cách tiếp cận mới khác hẳn và có lý do rõ ràng.
- Giữ nguyên các thay đổi có sẵn của người dùng; không dùng `git reset --hard` hoặc `git checkout --` nếu chưa được yêu cầu rõ ràng.
- Nếu gặp quyết định có thể phá vỡ toàn bộ hệ thống hoặc cần sửa file cấm, phải dừng và báo cáo thay vì tự ý tiếp tục.

## Yêu cầu báo cáo

Sau mỗi vòng, báo cáo ngắn gọn:

- Đã tối ưu thành phần nào.
- Đã thay đổi gì, ở đâu và để làm gì.
- Benchmark nào đã chạy.
- Kết quả trước và sau bằng số liệu cụ thể.
- Quyết định: giữ lại hay rollback.
- Có cập nhật `PROJECT_CONTEXT.md` hay không.
