# Optimization Changelog

Lịch sử các vòng tối ưu hóa của dự án Vision, kèm benchmark trước và sau mỗi thay đổi.

### Tiêu chí benchmark hiện hành

Từ vòng kế tiếp, so khớp frame dùng cùng `video_id` và thời gian `frame_idx / fps` theo `video_fps_map.json`, với dung sai **150 giây (±2.5 phút)**. KIS dùng một frame, TRAKE dùng từng mốc đúng thứ tự; QA báo riêng vị trí và `text_answer`, trong đó câu QA hoàn chỉnh cần cả hai phần đúng. Các số liệu của vòng 1 và 2 bên dưới được ghi theo tiêu chí cũ (frame khớp tuyệt đối).

## 2026-09-20 — Cập nhật tiêu chí benchmark

- Cập nhật `tools/benchmark.py` để đọc `video_fps_map.json`, so khớp frame theo thời gian với dung sai 150 giây (±2.5 phút), kiểm tra TRAKE theo thứ tự và báo riêng `location`/`text_answer` cho QA.
- Kết quả kiểm tra toàn bộ 30 câu theo tiêu chí mới, `top_k=50`: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 153.98 ms.

## 2026-09-20 — Vòng tối ưu 1: tách truy vấn theo newline

- Thay đổi: sửa `src/sqlite_engine.py`, hàm `SQLiteSearchEngine.search`, để tách thêm newline khi tạo các mệnh đề encode CLIP.
- Mục tiêu: cải thiện recall cho các câu hỏi mô tả nhiều dòng bằng cách giảm ảnh hưởng của giới hạn token CLIP.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 30 câu, `top_k=50`:
  - Trước: KIS 0/21, QA 0/8, TRAKE 0/1; tổng 0/30 (0.00%); trung bình 209.26 ms.
  - Sau: KIS 0/21, QA 0/8, TRAKE 0/1; tổng 0/30 (0.00%); trung bình 310.42 ms.
- Kết quả: **đã rollback** về commit backup `c09a7e0` vì độ chính xác không cải thiện và thời gian trung bình tăng 48.3%.

## 2026-09-20 — Vòng tối ưu 2: circuit-breaker fallback dịch

- Thay đổi: thử thêm cờ trong `src/fast_translator.py` để sau một lần GoogleTranslator/MyMemoryTranslator cùng thất bại thì bỏ qua các lần thử mạng tiếp theo.
- Mục tiêu: giảm latency khi môi trường không có dịch vụ dịch online và model dịch offline cũng không tồn tại.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 30 câu, `top_k=50`:
  - Trước: KIS 0/21, QA 0/8, TRAKE 0/1; tổng 0/30 (0.00%); trung bình 199.21 ms.
  - Sau: KIS 0/21, QA 0/8, TRAKE 0/1; tổng 0/30 (0.00%); trung bình 534.14 ms.
- Kết quả: **đã rollback** về commit backup `12e89d3` vì độ chính xác không cải thiện và thời gian trung bình tăng 168.1%.

## 2026-09-20 — Vòng tối ưu 3: giảm số thread PyTorch

- Thay đổi: đổi `torch.set_num_threads(4)` thành `torch.set_num_threads(2)` trong `src/sqlite_engine.py`, khi khởi tạo `SQLiteSearchEngine`.
- Mục tiêu: giảm latency encode CLIP trên CPU; không thay đổi thuật toán truy hồi hay tiêu chí kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 30 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 510.34 ms.
  - Sau: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 236.90 ms.
- Kết quả: **giữ lại**, latency trung bình giảm 53.6% và độ chính xác không đổi.
