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

## 2026-09-20 — Vòng tối ưu 4: bỏ qua fallback dịch trả nguyên văn

- Thay đổi: cập nhật `src/fast_translator.py` để nhận diện kết quả dịch giống hệt input là fallback không hiệu quả và bỏ qua các lần gọi mạng tiếp theo trong cùng process.
- Mục tiêu: giảm thời gian chờ khi Google/MyMemory không dịch được truy vấn; khác vòng 2 ở điều kiện kích hoạt, vòng này dựa trên kết quả nguyên văn chứ không chỉ exception.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 30 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 813.81 ms.
  - Sau: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 184.40 ms.
- Kết quả: **giữ lại**, latency trung bình giảm 77.3% và độ chính xác không đổi.

## 2026-09-20 — Thử lại vòng tối ưu 1: tách newline

- Thay đổi: bật lại tách newline trong `src/sqlite_engine.py` khi chia mệnh đề truy vấn cho CLIP.
- Benchmark trực tiếp, toàn bộ 30 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 0/21, QA hoàn chỉnh 1/8, TRAKE 0/1; tổng 1/30 (3.33%); trung bình 270.52 ms.
  - Sau: KIS 0/21, QA hoàn chỉnh 1/8, TRAKE 0/1; tổng 1/30 (3.33%); trung bình 212.14 ms.
- Kết quả: **giữ lại**, latency giảm 21.6%, độ chính xác không đổi.

## 2026-09-20 — Thử lại vòng tối ưu 2: circuit-breaker theo exception

- Thay đổi: thử lại biến thể cũ trong `src/fast_translator.py`, chỉ tắt fallback mạng khi cả hai translator ném exception; không dùng kết quả nguyên văn làm trigger.
- Benchmark trực tiếp, toàn bộ 30 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 0/21, QA hoàn chỉnh 1/8, TRAKE 0/1; tổng 1/30 (3.33%); trung bình 212.14 ms.
  - Sau: KIS 0/21, QA hoàn chỉnh 1/8, TRAKE 0/1; tổng 1/30 (3.33%); trung bình 213.59 ms.
- Kết quả: **đã rollback** về commit backup `4e1ff7d` vì latency tăng 0.7% và độ chính xác không đổi.

## 2026-09-20 — Vòng tối ưu 5: cache metadata kết quả truy hồi

- Thay đổi: thêm `_formatted_result_cache` trong `src/sqlite_engine.py`; các vector đã xuất hiện sẽ dùng lại metadata đã parse thay vì đọc SQLite và parse `raw_json` lại.
- Mục tiêu: giảm overhead metadata khi các truy vấn liên tiếp có candidate vector trùng nhau, không thay đổi ranking hoặc score.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 30 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 914.36 ms.
  - Sau: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 235.62 ms.
- Kết quả: **giữ lại**, latency giảm 74.2% và độ chính xác không đổi.

## 2026-09-20 — Vòng tối ưu 6: batch encode các mệnh đề CLIP

- Thay đổi: thêm `encode_text_batch()` trong `src/sqlite_engine.py` và dùng một lần `model.encode_text` cho toàn bộ các clause của truy vấn, sau đó vẫn lấy trung bình vector như trước.
- Mục tiêu: giảm overhead nhiều lần gọi OpenCLIP khi truy vấn đã được tách theo newline/dấu câu, không thay đổi ranking.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 30 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 300.11 ms.
  - Sau: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 182.53 ms.
- Kết quả: **giữ lại**, latency giảm 39.2% và độ chính xác không đổi.

## 2026-09-20 — Vòng tối ưu 7: tách theo dấu kết thúc câu

- Thay đổi: thử tách thêm truy vấn theo `.`, `!`, `?` trong `src/sqlite_engine.py` trước khi batch encode CLIP.
- Mục tiêu: cải thiện recall cho mô tả dài gồm nhiều câu.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 30 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 0/21, QA hoàn chỉnh 1/8, TRAKE 0/1; tổng 1/30 (3.33%); trung bình 206.54 ms.
  - Sau: KIS 0/21, QA hoàn chỉnh 1/8, TRAKE 0/1; tổng 1/30 (3.33%); trung bình 257.27 ms.
- Kết quả: **đã rollback** về commit backup `a152f32` vì latency tăng 24.6% và độ chính xác không đổi.

## 2026-09-20 — Vòng tối ưu 8: normalize native của OpenCLIP

- Thay đổi: thử dùng `model.encode_text(..., normalize=True)` thay cho encode rồi tự chuẩn hóa trong `src/sqlite_engine.py`.
- Mục tiêu: giảm overhead chuẩn hóa vector khi encode text đơn và batch.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 30 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 0/21, QA hoàn chỉnh 1/8, TRAKE 0/1; tổng 1/30 (3.33%); trung bình 189.13 ms.
  - Sau: KIS 0/21, QA hoàn chỉnh 1/8, TRAKE 0/1; tổng 1/30 (3.33%); trung bình 232.00 ms.
- Kết quả: **đã rollback** về commit backup `c6351fd` vì latency tăng 22.7% và độ chính xác không đổi.
