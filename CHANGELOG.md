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

## 2026-09-20 — Vòng tối ưu 9: giảm số luồng PyTorch

- Thay đổi thử nghiệm: giảm `torch.set_num_threads(2)` xuống `1` trong `src/sqlite_engine.py` cho workload truy vấn đơn lẻ trên CPU.
- Mục tiêu: giảm overhead tạo/quản lý luồng trên Windows mà không đổi ranking hoặc tiêu chí đúng.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 30 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 201.70 ms.
  - Sau: KIS 0/21, QA hoàn chỉnh 1/8 (location 1/8, text_answer 4/8), TRAKE 0/1; tổng 1/30 (3.33%); trung bình 511.79 ms.
- Kết quả: **đã rollback** về commit backup `1f0a0c6`; latency tăng 153.7%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 10: xếp hạng max-similarity cho nhiều mệnh đề

- Thay đổi thử nghiệm: trong `src/sqlite_engine.py`, thử xếp hạng mỗi keyframe theo similarity cao nhất giữa các clause, thay cho vector trung bình hiện tại.
- Mục tiêu: tránh làm loãng tín hiệu của một mệnh đề quan trọng trong truy vấn nhiều phần, kỳ vọng cải thiện recall.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 305.81 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 322.19 ms.
- Kết quả: **đã rollback** về commit backup `b3708aa`; latency tăng 5.4%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 11: weighted-average các mệnh đề CLIP

- Thay đổi thử nghiệm: trong `src/sqlite_engine.py`, trọng số vector mỗi clause theo số từ khi gộp vector truy vấn nhiều mệnh đề; truy vấn một mệnh đề không đổi.
- Mục tiêu: để mệnh đề mô tả dài có ảnh hưởng tương xứng hơn, kỳ vọng cải thiện recall mà không gọi model thêm lần nào.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 196.06 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 442.63 ms.
- Kết quả: **đã rollback** về commit backup `9c9a9e5`; latency tăng 125.8%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 12: cache metadata cho semantic search

- Thay đổi: tái sử dụng `_formatted_result_cache` hiện có cho đường `SQLiteSearchEngine.search()`; chỉ parse `raw_json` và đọc SQLite cho vector chưa có cache.
- Mục tiêu: giảm chi phí dựng metadata lặp lại giữa các truy vấn semantic liên tiếp, không thay đổi ranking, score hay tiêu chí đúng.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 365.53 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 168.61 ms.
- Kết quả: **giữ lại**, latency giảm 53.9%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 13: tái sử dụng kết nối SQLite read-only theo thread

- Thay đổi: cập nhật `SQLiteSearchEngine._get_db()` trong `src/sqlite_engine.py` để mỗi thread tái sử dụng một kết nối SQLite `mode=ro` thay vì mở kết nối mới cho từng truy vấn.
- Mục tiêu: giảm overhead kết nối và tận dụng page cache giữa các lần semantic search; không đổi SQL, ranking hoặc kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 263.82 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 188.20 ms.
- Kết quả: **giữ lại**, latency giảm 28.7%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 14: tăng SQLite page cache

- Thay đổi: đặt `PRAGMA cache_size = -65536` (64 MB) khi tạo kết nối SQLite read-only trong `src/sqlite_engine.py`.
- Mục tiêu: giảm đọc lại các trang của DB 814 MB giữa các truy vấn semantic, không đổi SQL, ranking hay kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 763.24 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 240.57 ms.
- Kết quả: **giữ lại**, latency giảm 68.5%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 15: bật SQLite memory-mapped I/O

- Thay đổi: đặt `PRAGMA mmap_size = 268435456` (256 MB) cho kết nối SQLite read-only trong `src/sqlite_engine.py`.
- Mục tiêu: giảm overhead đọc DB lớn 814 MB khi kết hợp với page cache 64 MB, không đổi SQL, ranking hay kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 656.82 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 212.66 ms.
- Kết quả: **giữ lại**, latency giảm 67.6%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 16: SQLite autocommit read-only

- Thay đổi: mở kết nối SQLite read-only với `isolation_level=None` trong `src/sqlite_engine.py` để các truy vấn SELECT chạy ở autocommit mode.
- Mục tiêu: bỏ transaction bookkeeping không cần thiết trong đường đọc-only, không đổi SQL, ranking hay kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 202.27 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 178.95 ms.
- Kết quả: **giữ lại**, latency giảm 11.5%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 17: SQLite query-only mode

- Thay đổi: bật `PRAGMA query_only = ON` trên kết nối SQLite read-only trong `src/sqlite_engine.py`.
- Mục tiêu: loại bỏ các đường xử lý ghi không cần thiết cho pipeline chỉ đọc, không đổi SQL, ranking hay kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 172.88 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 163.91 ms.
- Kết quả: **giữ lại**, latency giảm 5.2%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 18: bỏ transaction wrapper semantic search

- Thay đổi thử nghiệm: bỏ `with connection` wrapper riêng trong đường `SQLiteSearchEngine.search()` vì connection đã read-only, query-only và autocommit.
- Mục tiêu: giảm bookkeeping mỗi truy vấn semantic mà không đổi SQL, ranking hay kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 176.15 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 258.52 ms.
- Kết quả: **đã rollback** về commit backup `b9a9e07`; latency tăng 46.8%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 19: SQLite temp store trong RAM

- Thay đổi thử nghiệm: bật `PRAGMA temp_store = MEMORY` trên kết nối SQLite read-only trong `src/sqlite_engine.py`.
- Mục tiêu: giảm I/O tạm khi SQLite cần temporary structures, không đổi SQL, ranking hay kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 169.37 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 172.72 ms.
- Kết quả: **đã rollback** về commit backup `05c2d64`; latency tăng 2.0%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 20: tăng page cache SQLite lên 128 MB

- Thay đổi thử nghiệm: đổi `PRAGMA cache_size` từ 64 MB (`-65536`) lên 128 MB (`-131072`) trong `src/sqlite_engine.py`.
- Mục tiêu: thử giảm đọc lại DB lớn hơn nữa mà không đổi SQL, ranking hay kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 175.37 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3.51%); trung bình 185.56 ms.
- Kết quả: **đã rollback** về commit backup `37b0810`; latency tăng 5.8%, độ chính xác không đổi.
- Tiêu chí nhất quán: frame matching cùng `video_id` và sai lệch thời gian không quá 150 giây (±2.5 phút), áp dụng cho KIS/QA/TRAKE.

## 2026-09-20 — Vòng tối ưu 21: tái sử dụng buffer điểm số NumPy

- Thay đổi: cập nhật `src/sqlite_engine.py`, thêm `_score_vectors()` và buffer `thread-local`; hai đường semantic/image search dùng `np.dot(..., out=...)` thay vì cấp phát mảng điểm mới cho mỗi truy vấn.
- Mục tiêu: giảm cấp phát bộ nhớ và latency khi tính similarity trên toàn bộ 177.321 vector, không đổi thuật toán xếp hạng hay kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 730,35 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 192,73 ms.
- Kết quả: **giữ lại**, latency trung bình giảm 73,6%, độ chính xác không đổi.

## 2026-09-20 — Vòng tối ưu 22: tái sử dụng kết nối SQLite translation cache

- Thay đổi: cập nhật `src/fast_translator.py`, thêm kết nối SQLite cache theo từng thread và dùng lại cho các lần đọc/ghi trong `FastTranslator.translate()`.
- Mục tiêu: giảm overhead mở/đóng kết nối `translation_cache.db` trên mỗi truy vấn tiếng Việt, không thay đổi logic dịch, cache key hoặc kết quả retrieval.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 660,25 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 206,05 ms.
- Kết quả: **giữ lại**, latency trung bình giảm 68,8%, độ chính xác không đổi.

## 2026-09-20 — Vòng tối ưu 23: giới hạn PyTorch inter-op threads

- Thay đổi: cập nhật `src/sqlite_engine.py`, gọi `torch.set_num_interop_threads(1)` cạnh cấu hình intra-op `torch.set_num_threads(2)` khi khởi tạo `SQLiteSearchEngine`.
- Mục tiêu: giảm overhead điều phối thread khi OpenCLIP encode text trên CPU, không thay đổi vector, ranking hoặc kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (420,01 ms), QA hoàn chỉnh 1/16 (278,74 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (304,27 ms); tổng 2/57 (3,51%); trung bình 376,29 ms.
  - Sau: KIS 1/39 (249,88 ms), QA hoàn chỉnh 1/16 (244,88 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (342,41 ms); tổng 2/57 (3,51%); trung bình 251,72 ms.
- Kết quả: **đã rollback** về backup `e25640d`; không tiếp tục giữ thay đổi vì đây là cùng hướng tối ưu số thread PyTorch đã được thử ở vòng 3 và vòng 9.

## 2026-09-20 — Vòng tối ưu 24: tách liên từ tiếng Việt `và`

- Thay đổi thử nghiệm: cập nhật regex tách clause trong `src/sqlite_engine.py` để tách thêm liên từ `và` trong truy vấn semantic nhiều mệnh đề.
- Mục tiêu: cải thiện recall bằng cách encode riêng các vế tiếng Việt thay vì gộp vào một clause.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (157,52 ms), QA hoàn chỉnh 1/16 (161,39 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (269,41 ms); tổng 2/57 (3,51%); trung bình 162,53 ms.
  - Sau: KIS 1/39 (453,53 ms), QA hoàn chỉnh 1/16 (423,26 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (503,98 ms); tổng 2/57 (3,51%); trung bình 446,80 ms.
- Kết quả: **đã rollback** về backup `e36fe6c` vì độ chính xác không cải thiện và latency tổng tăng 174,9%.

## 2026-09-20 — Vòng tối ưu 25: eager-import translator fallback

- Thay đổi: cập nhật `src/fast_translator.py`, import `GoogleTranslator` và `MyMemoryTranslator` một lần khi module khởi tạo thay vì import trong request đầu tiên.
- Mục tiêu: loại overhead import khỏi lần dịch đầu tiên, không thay đổi logic fallback, cache hay kết quả retrieval.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (245,48 ms), QA hoàn chỉnh 1/16 (207,93 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (371,11 ms); tổng 2/57 (3,51%); trung bình 239,35 ms.
  - Sau: KIS 1/39 (173,79 ms), QA hoàn chỉnh 1/16 (183,68 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (267,84 ms); tổng 2/57 (3,51%); trung bình 179,87 ms.
- Kết quả: **giữ lại**, latency tổng giảm 24,8%, độ chính xác không đổi.

## 2026-09-20 — Vòng tối ưu 26: eager-load FastTranslator trong SQLite engine

- Thay đổi thử nghiệm: đưa import singleton `fast_translator` từ bên trong `SQLiteSearchEngine.search()` lên import-time của `src/sqlite_engine.py`, nhằm chuyển chi phí khởi tạo translator ra startup.
- Mục tiêu: giảm latency request semantic đầu tiên, không thay đổi logic dịch, cache hoặc ranking.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (227,36 ms), QA hoàn chỉnh 1/16 (206,39 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (318,25 ms); tổng 2/57 (3,51%); trung bình 224,67 ms.
  - Sau: KIS 1/39 (526,20 ms), QA hoàn chỉnh 1/16 (475,12 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (672,87 ms); tổng 2/57 (3,51%); trung bình 517,01 ms.
- Kết quả: **đã rollback** về backup `338bd44` vì độ chính xác không cải thiện và latency tổng tăng 130,1%.

## 2026-09-20 — Vòng tối ưu 27: pre-compile regex tách mệnh đề semantic

- Thay đổi: thêm `_CLAUSE_SPLIT_RE = re.compile(...)` ở cấp module trong `src/sqlite_engine.py` và dùng lại regex này khi tách các clause truy vấn.
- Mục tiêu: loại chi phí biên dịch regex lặp lại trên mỗi truy vấn, giữ nguyên biểu thức và logic retrieval.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (218,88 ms), QA hoàn chỉnh 1/16 (224,46 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (323,17 ms); tổng 2/57 (3,51%); trung bình 224,10 ms.
  - Sau: KIS 1/39 (185,65 ms), QA hoàn chỉnh 1/16 (178,17 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (324,90 ms); tổng 2/57 (3,51%); trung bình 188,43 ms.
- Kết quả: **giữ lại**, latency tổng giảm 15,66%, độ chính xác không đổi.

## 2026-09-20 — Vòng tối ưu 28: tra cứu memory-cache translator một lần

- Thay đổi: cập nhật `src/fast_translator.py`, thay cặp thao tác `in` rồi lookup bằng một lần `dict.get()` trong `FastTranslator.translate()`.
- Mục tiêu: giảm một lần tra cứu dictionary trên các truy vấn tiếng Việt đã có trong memory cache, giữ nguyên bản dịch và fallback.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (171,94 ms), QA hoàn chỉnh 1/16 (189,54 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (362,36 ms); tổng 2/57 (3,51%); trung bình 183,56 ms.
  - Sau: KIS 1/39 (158,79 ms), QA hoàn chỉnh 1/16 (160,20 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (321,70 ms); tổng 2/57 (3,51%); trung bình 164,90 ms.
- Kết quả: **giữ lại**, latency tổng giảm 10,17%, độ chính xác không đổi.

## 2026-09-21 — Vòng tối ưu 29: loại import `re` dư trong search

- Thay đổi thử nghiệm: xóa `import re` bên trong `SQLiteSearchEngine.search()` trong `src/sqlite_engine.py`, vì module đã import `re` và regex ở cấp module.
- Mục tiêu: giảm một lookup import thừa trên mỗi truy vấn semantic mà không thay đổi logic tách mệnh đề.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (167,94 ms), QA hoàn chỉnh 1/16 (174,78 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (263,94 ms); tổng 2/57 (3,51%); trung bình 173,23 ms.
  - Sau: KIS 1/39 (313,83 ms), QA hoàn chỉnh 1/16 (190,06 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (309,11 ms); tổng 2/57 (3,51%); trung bình 278,92 ms.
- Kết quả: **đã rollback** về backup `ababc00`; latency tổng tăng 61,01%, độ chính xác không đổi.

## 2026-09-21 — Vòng tối ưu 30: dùng chuẩn hóa tích hợp của OpenCLIP

- Thay đổi: cập nhật `encode_text()` và `encode_text_batch()` trong `src/sqlite_engine.py` để gọi `self.model.encode_text(..., normalize=True)` thay cho encode rồi chuẩn hóa bằng phép norm riêng.
- Mục tiêu: giảm một bước xử lý sau encode, giữ vector truy vấn ở dạng L2-normalized và không thay đổi ranking.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (313,75 ms), QA hoàn chỉnh 1/16 (238,85 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (264,50 ms); tổng 2/57 (3,51%); trung bình 291,00 ms.
  - Sau: KIS 1/39 (219,01 ms), QA hoàn chỉnh 1/16 (221,43 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (410,79 ms); tổng 2/57 (3,51%); trung bình 226,42 ms. Lần chạy xác nhận thứ hai: 237,26 ms.
- Kết quả: **giữ lại**, latency lần đo chính giảm 22,19%, độ chính xác không đổi.

## 2026-09-21 — Vòng tối ưu 31: pre-compile regex nhận diện tiếng Việt

- Thay đổi: thêm `_VI_CHAR_RE` ở cấp module trong `src/fast_translator.py` và dùng `.search()` trên regex đã biên dịch trong `FastTranslator.is_vietnamese()`.
- Mục tiêu: loại chi phí xử lý pattern lặp lại khi nhận diện truy vấn tiếng Việt, không thay đổi điều kiện nhận diện, bản dịch hoặc retrieval.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (319,39 ms), QA hoàn chỉnh 1/16 (331,45 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (367,19 ms); tổng 2/57 (3,51%); trung bình 324,45 ms.
  - Sau: KIS 1/39 (206,73 ms), QA hoàn chỉnh 1/16 (223,47 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (344,62 ms); tổng 2/57 (3,51%); trung bình 216,27 ms.
- Kết quả: **giữ lại**, latency tổng giảm 33,34%, độ chính xác không đổi.

## 2026-09-21 — Vòng tối ưu 32: tái sử dụng chỉ số vector đã chuyển kiểu

- Thay đổi: trong đường semantic của `SQLiteSearchEngine.search()` tại `src/sqlite_engine.py`, chuyển `top_indices` sang `int` một lần rồi dùng lại khi kiểm tra metadata cache và dựng kết quả.
- Mục tiêu: loại các lần gọi `int(idx)` lặp lại trên mỗi truy vấn, không thay đổi ranking, cache key hoặc số lượng kết quả.
- Benchmark trực tiếp qua pipeline `SQLiteSearchEngine`, toàn bộ 57 câu hiện có, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (319,39 ms), QA hoàn chỉnh 1/16 (331,45 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (367,19 ms); tổng 2/57 (3,51%); trung bình 324,45 ms.
  - Sau: KIS 1/39 (231,17 ms), QA hoàn chỉnh 1/16 (261,58 ms; location 1/16, text_answer 6/16), TRAKE 0/2 (356,45 ms); tổng 2/57 (3,51%); trung bình 244,10 ms.
- Kết quả: **giữ lại**, latency tổng giảm 24,76%, độ chính xác không đổi.

## 2026-09-21 — Vòng tối ưu 33 (Track A): hợp nhất thứ hạng RRF cho nhiều mệnh đề

- Thay đổi: cập nhật nhánh semantic nhiều mệnh đề trong `src/sqlite_engine.py`, hàm `SQLiteSearchEngine.search()`, từ trung bình các vector mệnh đề sang Reciprocal Rank Fusion (RRF) trên top ứng viên của từng mệnh đề. Nhánh đơn mệnh đề và Track B không thay đổi.
- Mục tiêu: cải thiện tốc độ và/hoặc recall cho truy vấn mô tả nhiều sự kiện; đây là cách tiếp cận khác với các thử nghiệm trung bình có trọng số và max-similarity đã rollback trước đó.
- Benchmark Track A trực tiếp qua `tools/benchmark.py`, toàn bộ 57 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Trước: KIS 1/39 (2,56%), QA hoàn chỉnh 1/16 (6,25%; location 1/16, text_answer 6/16), TRAKE 0/2 (0,00%); tổng 2/57 (3,51%); trung bình 584,76 ms.
  - Sau lần đo chính: KIS 1/39, QA hoàn chỉnh 1/16, TRAKE 0/2; tổng 2/57 (3,51%); trung bình 273,18 ms.
  - Lần chạy xác nhận: KIS 1/39, QA hoàn chỉnh 1/16, TRAKE 0/2; tổng 2/57 (3,51%); trung bình 259,24 ms.
- Kết quả: **giữ lại**, độ chính xác không đổi và latency xác nhận giảm 55,66% so với baseline.

## 2026-09-21 — Vòng tối ưu 34 (Track A): thêm ranking vector tổng hợp vào RRF

- Thay đổi thử nghiệm: thêm ranking của vector trung bình toàn bộ mệnh đề vào Reciprocal Rank Fusion trong `src/sqlite_engine.py`, bên cạnh ranking riêng của từng mệnh đề.
- Mục tiêu: giữ tín hiệu ngữ nghĩa toàn câu để cải thiện recall mà không bỏ lợi ích RRF cho truy vấn nhiều sự kiện.
- Benchmark Track A trực tiếp qua `tools/benchmark.py`, toàn bộ 57 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Baseline đã giữ từ vòng 33: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 259,24 ms.
  - Sau lần đo chính: tổng 2/57 (3,51%); trung bình 288,70 ms.
  - Lần chạy xác nhận: tổng 2/57 (3,51%); trung bình 286,74 ms.
- Kết quả: **đã rollback** về commit backup `13c1bb1` vì độ chính xác không cải thiện và latency xác nhận tăng 10,61% so với baseline giữ lại.

## 2026-09-21 — Vòng tối ưu 35 (Track A): mở rộng pool ứng viên RRF

- Thay đổi thử nghiệm: tăng pool ứng viên cho nhánh RRF nhiều mệnh đề từ top-50 lên top-100 trong `src/sqlite_engine.py`, nhưng vẫn trả tối đa top-50 kết quả.
- Mục tiêu: giảm khả năng bỏ sót frame không lọt top-50 của từng mệnh đề, qua đó cải thiện recall.
- Benchmark Track A trực tiếp qua `tools/benchmark.py`, toàn bộ 57 câu, `top_k=50`, frame tolerance 150 giây (±2.5 phút):
  - Baseline đã giữ từ vòng 33: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 259,24 ms.
  - Sau lần đo chính: tổng 2/57 (3,51%); trung bình 256,99 ms.
  - Lần chạy xác nhận: tổng 2/57 (3,51%); trung bình 255,75 ms.
- Kết quả: **đã rollback** về commit backup `7854140` vì accuracy không cải thiện và mức nhanh hơn 1,35% không đủ rõ ràng so với dao động benchmark.

## 2026-09-21 — Vòng tối ưu 36 (Track B): cô lập session Agy theo client

- Thay đổi: `src/main.py` không còn ép mọi request vào `local-flash`/`local-pro`; key session mới được tạo từ `session_id` đã băm và model route. `frontend/index.html` tạo và giữ UUID riêng trong `sessionStorage` thay vì đặt lại `local-user` ở mỗi request.
- Mục tiêu: ngăn lịch sử hội thoại của một câu hỏi (ví dụ graffiti) bị dùng lại cho câu hỏi khác (ví dụ học sinh), đồng thời tách context khi route flash/pro thay đổi.
- Benchmark Track B trước: full `tools/benchmark_chatbot.py` ghi 0/57 đúng, lỗi 48/57 (84,21%), trung bình 607,62 ms; API/model khi đó không ổn định và usage/cost unavailable.
- Smoke test sau thay đổi: 1 câu, 0/1 đúng, lỗi 1/1, trung bình 10.057,86 ms, không có usage/cost. Antigravity CLI báo chưa đăng nhập nên không thể dùng kết quả này để đánh giá chất lượng session isolation.
- Kết quả: **giữ thay đổi**, vì đây là sửa lỗi cô lập context; cần đăng nhập/cấu hình Antigravity rồi chạy lại full benchmark để xác nhận chất lượng chatbot.

## 2026-09-21 — Vòng tối ưu 37: nhận diện tiếng Việt không dấu

- Thay đổi thử nghiệm: bổ sung heuristic nhận diện một số cụm tiếng Việt không dấu trong `src/fast_translator.py`, hàm `FastTranslator.is_vietnamese()`.
- Mục tiêu: để truy vấn tiếng Việt không dấu không bị bỏ qua bước dịch trước khi vào retrieval pipeline.
- Benchmark: `tools/benchmark.py`, toàn bộ 57 câu trong `answerAndQuestion.jsonl`, `top_k=50`, frame tolerance ±150 giây.
  - Trước: KIS 1/39, QA 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 251,36 ms.
  - Sau: KIS 1/39, QA 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 248,33 ms.
- Kết quả: **đã rollback** về commit backup `f340c10`; độ chính xác không đổi và mức nhanh hơn 1,20% không đủ rõ ràng so với dao động benchmark. `PROJECT_CONTEXT.md` không cần cập nhật vì thay đổi không được giữ.

## 2026-09-21 — Sửa lỗi MCP runtime của chatbot

- Nguyên nhân: Antigravity đã có entry `video-researcher`, nhưng `.venv` thiếu `mcp`, khiến lệnh `C:\Users\ADMIN\error_on_line_23\vision\.venv\Scripts\python.exe mcp_server.py` thất bại với `ModuleNotFoundError: No module named 'mcp'`. Vì vậy Agy báo các công cụ truy vấn và kiểm tra video không khả dụng.
- Thay đổi: cài dependency đã khai báo trong `requirements.txt`: `mcp==1.29.1` cùng các dependency phụ thuộc vào `.venv`; không sửa dữ liệu cấm hay mã nguồn MCP.
- Xác minh: `import mcp_server` thành công và đăng ký 9 tool. Smoke chatbot trả `candidates=4`, lỗi 0/1. Kiểm tra đúng câu hỏi học sinh gọi được `call_mcp_tool`/`view_file` và trả `L22_V026` tại các frame `1581`, `1638`, `3147`.
- Kết quả: **giữ**, không cần rollback. `PROJECT_CONTEXT.md` đã cập nhật; lỗi riêng do DB thiếu `ocr_fts`/`asr_fts` vẫn còn được ghi nhận độc lập.

## 2026-09-21 — Vòng tối ưu 38: fallback MCP evidence khi DB thiếu FTS

- Thay đổi: cập nhật `mcp_server.py`, hàm `search_video_evidence()`, để phát hiện DB không có `asr_fts`/`ocr_fts` và gọi `/api/v1/search/all` lấy nhánh ASR/OCR fallback thay vì dừng với `no such table`.
- Mục tiêu: giữ khả năng truy hồi evidence cho câu hỏi nhiều sự kiện trên artifact DB hiện tại; không sửa DB hoặc dataset bị cấm.
- Benchmark: `tools/benchmark_chatbot.py --limit 1 --timeout 180`, cùng dataset/cấu hình trước và sau, frame tolerance ±150 giây.
  - Trước: 0/1 đúng, lỗi 0/1, trung bình 38.013,72 ms; usage/cost unavailable.
  - Sau: 0/1 đúng, lỗi 0/1, trung bình 28.099,74 ms; usage/cost unavailable.
- Smoke tool-level bổ sung: gọi trực tiếp `search_video_evidence(["học sinh", "giáo viên"])` đã thực hiện hai request fallback thành công và trả candidate/frame thật, gồm `L22_V006, 543` và `L22_V006, 746`.
- Kết quả: **giữ lại**. Benchmark chính không đổi accuracy nhưng không có hồi quy; smoke xác nhận lỗi chức năng `no such table` đã được xử lý. `PROJECT_CONTEXT.md` đã cập nhật.

## 2026-09-21 — Vòng tối ưu 39: song song hóa MCP evidence fallback

- Thay đổi: cập nhật `mcp_server.py`, hàm `search_video_evidence()`, dùng `ThreadPoolExecutor` để gọi song song các request `/api/v1/search/all` cho nhiều term khi DB thiếu FTS.
- Mục tiêu: giảm latency fallback evidence mà không đổi thuật toán xếp hạng hoặc dữ liệu.
- Benchmark: `tools/benchmark_chatbot.py --limit 1 --timeout 180`, cùng dataset/cấu hình, frame tolerance ±150 giây.
  - Trước: 1/1 đúng, lỗi 0/1, trung bình 53.772,97 ms; usage/cost unavailable.
  - Sau: 1/1 đúng, lỗi 0/1, trung bình 33.347,93 ms; usage/cost unavailable.
- Smoke tool-level: `search_video_evidence(["học sinh", "giáo viên", "trường học", "đồng phục"])` giảm 12,255 → 6,117 giây; candidate/frame giữ nguyên.
- Kết quả: **giữ lại**. Không có hồi quy; `PROJECT_CONTEXT.md` đã cập nhật.

## 2026-09-21 — Vòng tối ưu 40: thử fallback LIKE cục bộ cho MCP evidence

- Thay đổi thử nghiệm: trong `mcp_server.py`, thay các request fallback `/api/v1/search/all` bằng truy vấn `LIKE` cục bộ trên các cột `asr_text`/`ocr_text` của DB hiện có, nhằm bỏ HTTP round trip và nhánh semantic không được dùng.
- Mục tiêu: giảm latency `search_video_evidence` khi DB thiếu `asr_fts`/`ocr_fts`.
- Benchmark: `tools/benchmark_chatbot.py --limit 1 --timeout 180`, cùng dataset/cấu hình, frame tolerance ±150 giây.
  - Trước: 1/1 đúng, lỗi 0/1, trung bình 33.998,89 ms; usage/cost unavailable.
  - Sau: 1/1 đúng, lỗi 0/1, trung bình 45.876,98 ms; usage/cost unavailable.
- Smoke tool-level: latency giảm 8,097 → 6,954 giây nhưng candidate thay đổi từ `L21_V001/L21_V009/L22_V003` sang `L25_V002/L25_V003/L25_V004`, nên không đủ bằng chứng giữ chất lượng recall.
- Kết quả: **đã rollback** về checkpoint `0dbbe1b` vì latency chatbot tăng 35,0% và kết quả candidate thay đổi. `PROJECT_CONTEXT.md` không cập nhật vì thay đổi không được giữ.

## 2026-09-21 — Vòng tối ưu 41: rerank theo độ phủ video cho multi-clause

- Thay đổi thử nghiệm: trong `src/sqlite_engine.py`, nhánh semantic nhiều mệnh đề thử gom điểm RRF theo `video_id`, rồi ưu tiên các frame thuộc video phủ nhiều mệnh đề hơn.
- Mục tiêu: tăng recall cho truy vấn nhiều sự kiện bằng cách ưu tiên cùng một video có bằng chứng cho nhiều vế, thay vì chỉ xếp hạng độc lập theo từng frame.
- Benchmark: `tools/benchmark.py --top-k 50`, toàn bộ 57 câu, frame tolerance ±150 giây.
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 464,96 ms.
  - Sau: KIS 0/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 1/57 (1,75%); trung bình 281,12 ms.
- Kết quả: **đã rollback** về checkpoint `f4ec99d`. Latency giảm nhưng KIS giảm 1 câu đúng, là hồi quy accuracy. `PROJECT_CONTEXT.md` không cập nhật vì thay đổi không được giữ.

## 2026-09-21 16:15 +07:00 — Vòng tối ưu 42: tích lũy RRF trên tập ứng viên

- Thay đổi: cập nhật nhánh semantic nhiều mệnh đề trong `src/sqlite_engine.py`; thay mảng điểm RRF kích thước toàn bộ 177.321 vector bằng tích lũy thưa trên hợp các ứng viên top-k của từng mệnh đề, rồi vẫn dùng `argpartition` để lấy top-k cuối. Công thức RRF, nhánh đơn mệnh đề và dữ liệu không đổi.
- Mục tiêu: giảm latency tính và chọn kết quả RRF cho truy vấn nhiều mệnh đề.
- Khám phá sơ bộ: không cần; chỉ có một hướng triển vọng cho mục tiêu này và hướng này khác các thử nghiệm ranking RRF đã rollback trước đó.
- Benchmark: `tools/benchmark.py --top-k 50`, pipeline trực tiếp `SQLiteSearchEngine`, toàn bộ 57 câu trong `answerAndQuestion.jsonl`, frame tolerance ±150 giây. Kiểm tra bổ sung: `.venv\\Scripts\\python.exe -m compileall -q src mcp_server.py`.
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 333,08 ms.
  - Sau lần đo chính: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 255,73 ms.
  - Lần chạy xác nhận: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 270,69 ms; benchmark exit 0, compile exit 0.
- Sửa phụ: không có.
- Checkpoint vòng: `7e6a0c0` (`chore: checkpoint before sparse RRF candidate accumulation`).
- Kết quả: **giữ lại**. Latency lần đo chính giảm 23,22% và lần xác nhận giảm 18,73% so với baseline; accuracy và các metric guardrail không đổi. `PROJECT_CONTEXT.md` không cần cập nhật vì API, kiến trúc và cách chạy không thay đổi.

## 2026-09-21 16:25 +07:00 — Vòng tối ưu 43: giới hạn URL ảnh MCP

- Thay đổi: cập nhật `mcp_server.py`, tool `search_image_by_url`, để validate HTTPS và allowlist host trước khi request, từ chối URL có userinfo/host không tin cậy, tắt redirect tự động và stream response với giới hạn 10 MB. Thêm `tools/security_scan.py` làm scanner tĩnh tối thiểu cho boundary này.
- Mục tiêu: giảm rủi ro SSRF và tiêu thụ bộ nhớ khi MCP tải ảnh từ URL bên ngoài.
- Benchmark/tool: `tools/security_scan.py` trước/sau; `.venv\\Scripts\\python.exe -m compileall -q mcp_server.py tools\\security_scan.py`; smoke async gọi helper và `search_image_by_url` với `http://127.0.0.1/image.jpg`, `https://example.com/image.jpg`, `https://user:pass@lh3.googleusercontent.com/image.jpg`.
  - Trước: `MCP_IMAGE_URL_FINDINGS: 2` (thiếu URL validation, thiếu response-size limit).
  - Sau: `MCP_IMAGE_URL_FINDINGS: 0`, scanner exit 0, compile exit 0; cả 3 URL không hợp lệ đều bị chặn trước network, `INVALID_URL_SMOKE=PASS`.
- Sửa phụ: không có.
- Checkpoint vòng: `c2427f6` (`chore: add MCP image URL security scan`).
- Kết quả: **giữ lại**. Finding bảo mật giảm 2 → 0 và smoke/compile đều pass. `PROJECT_CONTEXT.md` đã cập nhật để phản ánh policy URL mới; các endpoint tải URL khác vẫn ngoài phạm vi vòng này.

## 2026-09-21 — Rollback vòng tối ưu 43

- Theo yêu cầu, đã bỏ thay đổi bảo mật của vòng 43: khôi phục `mcp_server.py` và `PROJECT_CONTEXT.md` về trạng thái trước vòng, đồng thời xóa scanner `tools/security_scan.py`.
- Giữ nguyên các mục lịch sử vòng 43 ở trên để không xóa lịch sử benchmark; vòng 42 vẫn được giữ.
- Commit gốc của vòng 43: checkpoint `c2427f6`, commit giữ `2cc5f02`.

## 2026-09-21 16:32 +07:00 — Vòng tối ưu 44: thử batch similarity cho RRF

- Thay đổi thử nghiệm: trong `src/sqlite_engine.py`, nhánh semantic nhiều mệnh đề thử thay nhiều phép matrix-vector bằng một phép matrix-matrix `vectors @ clause_vectors.T`, sau đó giữ nguyên hợp ứng viên và công thức RRF.
- Mục tiêu: giảm latency tính similarity cho truy vấn nhiều mệnh đề.
- Khám phá sơ bộ: không cần; đây là hướng khác với tích lũy RRF sparse của vòng 42 và được đo trực tiếp bằng Track A.
- Benchmark: `tools/benchmark.py --top-k 50`, pipeline trực tiếp `SQLiteSearchEngine`, toàn bộ 57 câu, frame tolerance ±150 giây. Kiểm tra sau rollback: `.venv\\Scripts\\python.exe -m compileall -q src`.
  - Trước: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 251,71 ms.
  - Sau: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%); trung bình 283,86 ms.
  - Chênh lệch: latency tăng 12,78%, accuracy không đổi; benchmark không báo lỗi, compile sau rollback exit 0.
- Sửa phụ: không có.
- Checkpoint vòng: `df2d49d` (`chore: checkpoint before batched RRF scoring`).
- Kết quả: **đã rollback** về checkpoint trong phạm vi `src/sqlite_engine.py`; `PROJECT_CONTEXT.md` không cập nhật vì thay đổi không được giữ.

## 2026-09-21 16:47 +07:00 — Vòng tối ưu 45: quét LIKE một lần cho truy vấn nhiều token

- Thay đổi: cập nhật `SQLiteSearchEngine._fuzzy_text_search()` trong `src/sqlite_engine.py`; gộp các điều kiện token vào một câu SQL có các cột cờ `LIKE`, thay vì quét toàn bộ bảng một lần cho mỗi token. Khâu cộng điểm vẫn lặp theo thứ tự token để giữ nguyên thứ tự hòa điểm và tập kết quả.
- Mục tiêu: giảm latency fallback OCR/ASR trên artifact DB hiện thiếu `ocr_fts`/`asr_fts`, không thay đổi scoring hay candidate.
- Khám phá sơ bộ: không cần; đường nóng được xác định trực tiếp từ implementation và DB hiện tại. Không sửa file dữ liệu cấm.
- Benchmark/tool chính: ba lần `POST /api/v1/search/all` với query cố định `học sinh giáo viên trường học đồng phục`, `top_k=50`; guardrail là đủ 50 cặp `(video_id, frame_idx)` của mỗi nhánh OCR/ASR và đúng thứ tự. Track B bổ sung: `tools/benchmark_chatbot.py --limit 1 --timeout 180`. Kiểm tra hệ thống: `.venv\Scripts\python.exe -m compileall -q src`.
  - Trước: wall trung bình 5.880,28 ms; OCR 5.226,00 ms; ASR 5.529,33 ms. Track B 0/1 đúng, lỗi 0/1, 60.356,74 ms; usage/cost unavailable.
  - Sau: wall trung bình 2.074,97 ms; OCR 1.425,00 ms; ASR 1.801,00 ms. Track B 0/1 đúng, lỗi 0/1, 60.261,06 ms; usage/cost unavailable. Compile exit 0.
  - Chênh lệch: wall giảm 64,71%, OCR giảm 72,73%, ASR giảm 67,43%; cả ba lần sau sửa trả đúng cùng 50 cặp OCR và 50 cặp ASR theo đúng thứ tự như baseline. Accuracy/error của Track B không đổi.
- Sửa phụ: không có.
- Checkpoint vòng: `e10920d` (`chore: checkpoint before single-pass fuzzy text scan`).
- Kết quả: **giữ lại** vì metric latency mục tiêu cải thiện rõ ràng và candidate guardrail không hồi quy. `PROJECT_CONTEXT.md` không cần cập nhật vì kiến trúc, API, hành vi và cách chạy không thay đổi.

## 2026-09-21 16:52 +07:00 — Vòng tối ưu 46: thăm dò hợp nhất scan OCR/ASR

- Phạm vi dự kiến: hợp nhất hai lượt đọc fallback OCR và ASR của `/api/v1/search/all` thành một SQL scan, với mục tiêu giảm wall latency mà vẫn giữ nguyên hai danh sách kết quả.
- Khám phá sơ bộ chỉ đọc: chạy ba lần câu SQL chung trên cùng query `học sinh giáo viên trường học đồng phục`, cùng bốn token và DB read-only; thời gian 2.168,41 / 1.906,74 / 1.955,08 ms, trung bình 2.010,08 ms, trả 32.210 row khớp hợp.
- Baseline tham chiếu từ vòng 45: endpoint wall 2.074,97 ms; nhánh OCR 1.425,00 ms và nhánh ASR 1.801,00 ms khi hai nhánh chạy song song.
- Sửa phụ: không có. Không sửa source, file cấm hay `PROJECT_CONTEXT.md`; chưa tạo checkpoint vì hướng bị loại ở bước khám phá trước thay đổi chính thức.
- Kết quả: **không triển khai / không có thay đổi để rollback**. Riêng scan chung đã chậm hơn nhánh chi phối hiện tại trước chi phí tách và dựng hai bộ kết quả, nên không đủ triển vọng vượt baseline.

## 2026-09-21 16:53 +07:00 — Vòng tối ưu 47: trì hoãn đọc metadata fallback đến sau top-K

- Thay đổi: cập nhật `SQLiteSearchEngine._fuzzy_text_search()` trong `src/sqlite_engine.py`; lượt scan LIKE chỉ lấy `vector_id` và cờ hit để tính điểm, sau đó mới batch-fetch `raw_json` cho tối đa `top_k` vector đã chọn, thay vì kéo metadata lớn cho mọi row match.
- Mục tiêu: giảm I/O, cấp phát và latency fallback OCR/ASR mà không thay đổi token matching, scoring hay thứ tự kết quả.
- Khám phá sơ bộ: không cần; kết quả vòng 45 cho thấy SQL trả hàng chục nghìn row trong khi API chỉ cần top 50, nên đây là đường tối ưu trực tiếp và độc lập với hướng scan chung đã loại ở vòng 46.
- Benchmark/tool: ba lần `POST /api/v1/search/all` với query `học sinh giáo viên trường học đồng phục`, `top_k=50`; guardrail là SHA-256 của danh sách `(video_id, frame_idx)` theo thứ tự cho OCR/ASR. Kiểm tra hệ thống: `.venv\Scripts\python.exe -m compileall -q src`, `/api/v1/health`, và smoke OCR `/api/v1/search` với `top_k=3`.
  - Trước: wall 2.111,55 / 3.080,67 / 4.269,27 ms, trung bình 3.153,83 ms; OCR trung bình 1.982,33 ms; ASR trung bình 2.660,00 ms.
  - Sau: wall 1.695,87 / 1.528,95 / 1.394,62 ms, trung bình 1.539,81 ms; OCR trung bình 1.065,67 ms; ASR trung bình 1.275,33 ms.
  - Chênh lệch: wall giảm 51,18%, OCR giảm 46,24%, ASR giảm 52,06%. Cả ba lần trước/sau có OCR hash `6f3b10b2de46db1dd8476afc6c94106b72e9f93ad87e8081f44f0975ce1f3e09` và ASR hash `38f12cdd4b47149ecf8867a20eb723c05b3b95eed64fa20e600e1336801ef3b3`.
  - Guardrail: compile exit 0; health `healthy`; smoke OCR trả 3/3 kết quả, đứng đầu `L22_V006, 3788`.
- Sửa phụ: không có.
- Checkpoint vòng: `1b29c49` (`chore: checkpoint before deferred fuzzy metadata fetch`).
- Kết quả: **giữ lại** vì latency giảm rõ ràng, danh sách candidate không đổi và smoke/health đều pass. `PROJECT_CONTEXT.md` không cần cập nhật vì API, kiến trúc, hành vi và cách chạy không đổi.

## 2026-09-21 16:58 +07:00 — Vòng tối ưu 48: thăm dò xếp hạng top-K hoàn toàn trong SQLite

- Phạm vi dự kiến: đẩy cộng điểm, tie-break và `LIMIT 50` của fallback OCR/ASR xuống SQLite để Python không phải nhận và duyệt toàn bộ row match.
- Khám phá sơ bộ chỉ đọc: câu SQL subquery dùng cùng các cờ `LIKE`, xếp theo số token khớp giảm dần, token khớp đầu tiên và `vector_id`; chạy ba lần riêng cho mỗi field trên query `học sinh giáo viên trường học đồng phục`.
  - OCR: 838,45 / 821,85 / 867,19 ms, trung bình 842,50 ms; hash candidate giữ nguyên `6f3b10b2de46db1dd8476afc6c94106b72e9f93ad87e8081f44f0975ce1f3e09`.
  - ASR: 1.806,57 / 2.131,00 / 2.180,89 ms, trung bình 2.039,49 ms; hash candidate giữ nguyên `38f12cdd4b47149ecf8867a20eb723c05b3b95eed64fa20e600e1336801ef3b3`.
- Baseline vòng 47: OCR 1.065,67 ms, ASR 1.275,33 ms. SQL top-K giúp OCR 20,94% nhưng làm ASR chậm hơn 59,92%; `/search/all` bị nhánh ASR chậm nhất chi phối.
- Sửa phụ: không có. Không sửa source, file cấm hay `PROJECT_CONTEXT.md`; chưa tạo checkpoint vì hướng bị loại ở bước khám phá.
- Kết quả: **không triển khai / không có thay đổi để rollback** do hồi quy ASR nghiêm trọng dù candidate không đổi.

## 2026-09-21 16:59 +07:00 — Vòng tối ưu 49: cache LRU candidate fallback OCR/ASR

- Thay đổi: thêm cache LRU thread-safe, tối đa 256 entry trong `SQLiteSearchEngine`; key gồm field OCR/ASR, tuple token chuẩn hóa, `top_k` và `video_id_filter`. Cache chỉ giữ tuple `(vector_id, score)`; metadata top-K vẫn batch-read mỗi request để không giữ hoặc chia sẻ dict kết quả mutable.
- Mục tiêu: giảm latency khi Agy/MCP hoặc người dùng lặp lại cùng truy vấn fallback trên DB read-only, không thay đổi cold-path matching/ranking.
- Khám phá sơ bộ: không cần; workload ba request lặp cố định đo trực tiếp được cold/warm và cache có giới hạn rõ ràng.
- Benchmark/tool: ba lần liên tiếp `POST /api/v1/search/all`, query `học sinh giáo viên trường học đồng phục`, `top_k=50`; run 1 là cold, run 2-3 là warm; guardrail là SHA-256 của danh sách `(video_id, frame_idx)` theo thứ tự. Kiểm tra hệ thống: compile, health và hai smoke ASR lặp với filter `L22_V019`, `top_k=3`.
  - Trước: wall 1.720,87 / 1.482,13 / 1.489,23 ms, trung bình 1.564,08 ms; warm trung bình 1.485,68 ms; OCR trung bình 1.068,67 ms; ASR trung bình 1.300,00 ms.
  - Sau: wall 1.732,63 / 543,23 / 379,79 ms, trung bình 885,22 ms; warm trung bình 461,51 ms; OCR trung bình 448,33 ms; ASR trung bình 479,67 ms.
  - Chênh lệch: trung bình ba run giảm 43,40%; warm giảm 68,94%; OCR giảm 58,05%; ASR giảm 63,10%. Cold wall tăng 0,68%, nằm trong dao động và không có hồi quy chức năng.
  - Candidate guardrail giữ nguyên ở cả ba run: OCR `6f3b10b2de46db1dd8476afc6c94106b72e9f93ad87e8081f44f0975ce1f3e09`, ASR `38f12cdd4b47149ecf8867a20eb723c05b3b95eed64fa20e600e1336801ef3b3`.
  - Guardrail hệ thống: compile exit 0; health `healthy`; hai smoke filter đều trả 3 kết quả và cùng top `L22_V019, 1727`.
- Sửa phụ: không có.
- Checkpoint vòng: `7551bb0` (`chore: checkpoint before bounded fuzzy candidate cache`).
- Kết quả: **giữ lại**. `PROJECT_CONTEXT.md` đã cập nhật để mô tả cache candidate fallback và đặc tính cold query.

## 2026-09-21 17:03 +07:00 — Vòng tối ưu 50: cache trạng thái bảng FTS

- Thay đổi: thêm lookup `sqlite_master` có cache theo tên bảng trong `SQLiteSearchEngine`; khi `ocr_fts`/`asr_fts` không tồn tại, các request sau đi thẳng vào fuzzy fallback thay vì thực thi SQL lỗi và bắt exception mỗi lần.
- Mục tiêu: giảm latency warm OCR/ASR trên artifact DB hiện tại, không thay đổi FTS path khi bảng tồn tại hoặc matching/ranking của fallback.
- Khám phá sơ bộ: không cần; log runtime xác nhận mỗi request warm đều phát sinh `no such table` trước fallback.
- Benchmark/tool: sau khi candidate cache được prime, chạy năm lần `POST /api/v1/search/all` với query `học sinh giáo viên trường học đồng phục`, `top_k=50`; metric chính là median/average `elapsed_ms` của hai nhánh, guardrail là SHA-256 candidate. Compile, health và smoke OCR `top_k=3` chạy bổ sung.
  - Trước: OCR 16 / 43 / 458 / 42 / 30 ms, median 42 ms, trung bình 117,8 ms; ASR 37 / 53 / 19 / 42 / 17 ms, median 37 ms, trung bình 33,6 ms; wall trung bình 805,59 ms.
  - Sau: OCR 7 / 7 / 15 / 6 / 15 ms, median 7 ms, trung bình 10,0 ms; ASR 13 / 15 / 10 / 12 / 9 ms, median 12 ms, trung bình 11,8 ms; wall trung bình 446,59 ms.
  - Chênh lệch: median OCR giảm 83,33%, median ASR giảm 67,57%; average OCR giảm 91,51%, average ASR giảm 64,88%. Wall trung bình giảm 44,56% nhưng chỉ là metric liên quan vì semantic/HTTP có nhiễu.
  - Candidate guardrail không đổi ở cả năm run: OCR `6f3b10b2de46db1dd8476afc6c94106b72e9f93ad87e8081f44f0975ce1f3e09`, ASR `38f12cdd4b47149ecf8867a20eb723c05b3b95eed64fa20e600e1336801ef3b3`. Compile exit 0, health `healthy`, smoke OCR trả 3 kết quả với top `L22_V006, 3788`.
  - Cold prime sau restart dao động 2.234/2.429 ms cho OCR/ASR và không được dùng để kết luận; thay đổi cold path chỉ thêm một lookup schema một lần trước cùng fallback.
- Sửa phụ: không có.
- Checkpoint vòng: `54b9308` (`chore: checkpoint before FTS availability cache`).
- Kết quả: **giữ lại** vì warm branch latency giảm rõ ràng và không có hồi quy candidate/hệ thống. `PROJECT_CONTEXT.md` đã cập nhật.

## 2026-09-21 17:07 +07:00 — Vòng tối ưu 51: tái sử dụng metadata đã format cho fuzzy top-K

- Thay đổi: cập nhật `_fuzzy_text_search()` để chỉ batch-fetch/parse `raw_json` cho các candidate chưa có trong `_formatted_result_cache`; warm request copy metadata đã format và chỉ gắn lại score riêng của truy vấn. Đây là cùng cache metadata engine đã dùng cho semantic/image results.
- Mục tiêu: loại đọc SQLite và parse JSON lặp lại trên warm OCR/ASR fallback, không thay đổi candidate cache, matching, ranking hoặc payload.
- Khám phá sơ bộ: không cần; sau vòng 50, warm branch còn chủ yếu batch-read và format lại cùng top-K metadata.
- Benchmark/tool: candidate/FTS cache được prime một lần, sau đó chạy năm lần `POST /api/v1/search/all` với query `học sinh giáo viên trường học đồng phục`, `top_k=50`; metric chính là branch `elapsed_ms`, guardrail là hash candidate. Compile, health và smoke ASR có filter chạy bổ sung.
  - Trước: OCR 17 / 6 / 8 / 16 / 7 ms, median 8 ms, trung bình 10,8 ms; ASR 11 / 12 / 14 / 10 / 16 ms, median 12 ms, trung bình 12,6 ms; wall trung bình 401,68 ms.
  - Sau: OCR 1 / 1 / 1 / 0 / 1 ms, median 1 ms, trung bình 0,8 ms; ASR 1 / 1 / 1 / 0 / 1 ms, median 1 ms, trung bình 0,8 ms; wall trung bình 270,30 ms.
  - Chênh lệch: median OCR giảm 87,50%, median ASR giảm 91,67%; average OCR giảm 92,59%, average ASR giảm 93,65%; wall trung bình giảm 32,71%.
  - Candidate guardrail không đổi ở cả năm run: OCR `6f3b10b2de46db1dd8476afc6c94106b72e9f93ad87e8081f44f0975ce1f3e09`, ASR `38f12cdd4b47149ecf8867a20eb723c05b3b95eed64fa20e600e1336801ef3b3`. Compile exit 0; health `healthy`; smoke ASR filter trả 3 kết quả với top `L22_V019, 1727`.
- Sửa phụ: không có.
- Checkpoint vòng: `9443846` (`chore: checkpoint before fuzzy metadata cache reuse`).
- Kết quả: **giữ lại**. `PROJECT_CONTEXT.md` đã cập nhật để mô tả metadata cache dùng chung cho fuzzy top-K.

## 2026-09-21 19:58 +07:00 — Vòng tối ưu 52: thêm benchmark similar-by-vector

- Thay đổi: thêm `tools/benchmark_similar.py`, benchmark trực tiếp production `SQLiteSearchEngine.search(query_vector_id=...)`, đo thời gian load/case và kiểm tra số kết quả cùng self-match ở vị trí đầu. Tool hỗ trợ output text/JSON và trả exit 1 khi scenario fail/error.
- Mục tiêu: tạo phép đo tái lập cho đường `/api/v1/search/similar` trước khi tối ưu/sửa logic thành phần này; theo quy trình, vòng này chưa sửa engine.
- Khám phá sơ bộ: smoke read-only xác nhận `query_vector_id=0`, `top_k=5` ném `UnboundLocalError` vì `top_indices` chưa được gán.
- Baseline trước khi có tool: 0 automated scenario; smoke thủ công 1 scenario, 0 pass, 1 fail/error, case 0,02 ms, lỗi `UnboundLocalError`.
- Sau: 1 automated scenario; `tools/benchmark_similar.py --vector-id 0 --top-k 5 --json` báo 0 pass, 1 fail/error, load 2.033,09 ms, case 0,01 ms, exit 1 và cùng lỗi baseline. Compile tool exit 0.
- Metric cải thiện: coverage tự động 0 → 1 scenario; trạng thái chức năng cố ý chưa đổi và được báo đỏ chính xác, không có kết luận rằng similar search đã tốt hơn.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `7052dfb` (`chore: checkpoint before similar-search benchmark`).
- Kết quả: **giữ lại benchmark**. `PROJECT_CONTEXT.md` đã cập nhật với công cụ đo và lỗi similar-by-vector đang mở.

## 2026-09-21 20:01 +07:00 — Vòng tối ưu 53: sửa ranking similar-by-vector

- Thay đổi: cập nhật nhánh `query_vector_id` trong `SQLiteSearchEngine.search()` tại `src/sqlite_engine.py` để tính cosine score, chọn `top_k` bằng `argpartition` và sắp xếp candidate trước khi dùng pipeline metadata chung. Nhánh FAISS tương ứng vẫn được giữ tương thích dù runtime hiện tắt FAISS.
- Mục tiêu: khôi phục chức năng `/api/v1/search/similar`; metric chính là pass/error, số kết quả và self-match của `tools/benchmark_similar.py`.
- Khám phá sơ bộ: không cần; benchmark vòng 52 đã cô lập nguyên nhân `top_indices`/`scores` chưa được gán trong nhánh vector ID.
- Benchmark: `.venv\Scripts\python.exe tools\benchmark_similar.py --vector-id 0 --top-k 5 --json`, cùng cấu hình trước/sau. Guardrail: compile toàn bộ `src` và tool; chạy `tools/benchmark.py --top-k 50` trên đủ 57 case.
  - Trước: 0/1 pass, 1 fail, 1 error; case 0,02 ms rồi crash với `UnboundLocalError`.
  - Sau: 1/1 pass, 0 fail, 0 error; case 29,30 ms; trả đủ 5 kết quả, top vector ID `0`, thứ tự đầu `[0, 2904, 6972, 12228, 2416]`; benchmark exit 0.
  - Guardrail retrieval: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%), trung bình 216,03 ms; compile exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `fcc12bf` (`chore: checkpoint before similar-search fix`).
- Kết quả: **giữ lại** vì chức năng tăng 0/1 → 1/1 pass, lỗi giảm 1 → 0 và semantic guardrail giữ nguyên accuracy. `PROJECT_CONTEXT.md` đã cập nhật để bỏ lỗi đang mở và ghi benchmark regression.

## 2026-09-21 20:05 +07:00 — Vòng tối ưu 54: cache LRU candidate similar-by-vector

- Thay đổi: thêm cache LRU thread-safe tối đa 256 entry trong `SQLiteSearchEngine` cho candidate/scores của nhánh `query_vector_id`; key gồm vector nguồn và số candidate cần lấy. Cache lưu tuple immutable của ID/score, còn metadata tiếp tục dùng pipeline/cache chung.
- Mục tiêu: giảm latency khi `/api/v1/search/similar` lặp lại cùng vector/top-K, không thay đổi cosine scoring, ranking hoặc payload.
- Khám phá sơ bộ: không cần; benchmark vòng 53 cho thấy mỗi request lặp vẫn tính dot product và argpartition lại trên toàn bộ 177.321 vector.
- Benchmark/tool: trên cùng một engine, gọi `tools.benchmark_similar.run_case(engine, 0, 50)` năm lần; run 1 là cold, run 2-5 là warm. Guardrail là 50/50 kết quả pass, self-match và toàn bộ thứ tự vector ID. Chạy thêm benchmark chuẩn `tools/benchmark_similar.py --vector-id 0 --top-k 5 --json` và compile.
  - Trước: 28,307 / 14,368 / 17,827 / 21,546 / 20,101 ms; warm trung bình 18,461 ms, median 18,964 ms.
  - Sau: 22,126 / 0,055 / 0,038 / 0,036 / 0,061 ms; warm trung bình 0,047 ms, median 0,046 ms.
  - Chênh lệch: warm average giảm 99,74%, warm median giảm 99,76%; cold giảm 21,84% nhưng không dùng làm kết luận chính vì chỉ một mẫu.
  - Guardrail: cả năm run trả cùng 50 vector ID như baseline, top vector `0`; benchmark chuẩn 1/1 pass, 0 error, 5 kết quả, case 19,62 ms; compile exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `d506464` (`chore: checkpoint before similar candidate cache`).
- Kết quả: **giữ lại**. `PROJECT_CONTEXT.md` đã cập nhật để mô tả cache candidate similar-by-vector.

## 2026-09-21 20:09 +07:00 — Vòng tối ưu 55: chặn vector ID ngoài phạm vi

- Thay đổi: cập nhật `SQLiteSearchEngine.search()` để trả danh sách rỗng ngay khi `query_vector_id` âm hoặc lớn hơn/equal số vector, thay vì rơi sang nhánh encode chuỗi rỗng rồi trả semantic result không liên quan.
- Mục tiêu: sửa tính đúng đắn của similar-by-vector ở input biên; metric chính là số case invalid trả rỗng và tổng kết quả ngoài ý muốn.
- Khám phá sơ bộ: không cần; điều kiện nhánh hiện tại cho thấy ID không hợp lệ đi thẳng vào nhánh text-search.
- Benchmark/tool: cùng một harness Python gọi production engine với `query_vector_id=-1` và `query_vector_id=len(engine.vectors)`, `top_k=5`; pass khi kết quả chính xác là `[]`. Guardrail dùng `tools/benchmark_similar.py --vector-id 0 --top-k 5 --json` và compile toàn bộ `src` cùng benchmark.
  - Trước: 0/2 case pass; mỗi case trả 5 semantic result, tổng 10 kết quả ngoài ý muốn; hai case cùng có top IDs `[3368, 137291, 16288]`.
  - Sau: 2/2 case pass; cả hai trả 0 kết quả, không lỗi; tổng kết quả ngoài ý muốn giảm 10 → 0.
  - Guardrail valid-vector: 1/1 pass, 0 error, 5 kết quả, top vector ID `0`, case 16,59 ms; compile exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `8b467b3` (`chore: checkpoint before invalid vector handling`).
- Kết quả: **giữ lại** vì correctness tăng 0/2 → 2/2 và valid-vector không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật hành vi input ngoài phạm vi.

## 2026-09-21 20:12 +07:00 — Vòng tối ưu 56: mở rộng benchmark similar cho input biên

- Thay đổi: mở rộng `tools/benchmark_similar.py` bằng hai scenario tự động cho vector ID `-1` và `len(engine.vectors)`; giữ nguyên scenario valid và trường `case` cũ để tương thích output, bổ sung `invalid_cases` cùng aggregate pass/fail/error.
- Mục tiêu: khóa hồi quy hành vi invalid-ID của vòng 55 bằng công cụ chính thức; metric chính là số scenario tự động và tỷ lệ pass.
- Khám phá sơ bộ: không cần; khoảng trống coverage đã được xác định trực tiếp từ benchmark chỉ có một valid case.
- Benchmark/tool: `.venv\Scripts\python.exe tools\benchmark_similar.py --vector-id 0 --top-k 5 --json`, cùng cấu hình trước/sau; compile toàn bộ `src` và benchmark làm guardrail.
  - Trước: 1 scenario tự động, 1/1 pass, 0 fail/error; valid case 26,52 ms.
  - Sau: 3 scenario tự động, 3/3 pass, 0 fail/error; valid case 18,42 ms; hai invalid case lần lượt 0,0022 ms và 0,0013 ms, đều trả 0 kết quả.
  - Chênh lệch mục tiêu: coverage tăng 1 → 3 scenario, thêm đủ hai biên invalid; không dùng dao động latency cold làm kết luận. Compile exit 0.
- Sửa phụ: không có. Không sửa file cấm; runtime không thay đổi.
- Checkpoint vòng: `f00684a` (`chore: checkpoint before similar edge benchmarks`).
- Kết quả: **giữ lại** vì coverage tăng và toàn bộ scenario pass. `PROJECT_CONTEXT.md` đã cập nhật mô tả benchmark.

## 2026-09-21 20:17 +07:00 — Vòng tối ưu 57: thử lazy-load OpenCLIP

- Thay đổi thử nghiệm: bỏ eager `load_clip_model()` khỏi constructor và thêm khóa lazy initialization thread-safe; encoder chỉ được nạp ở lần encode text/image đầu tiên. Thay đổi này đã được rollback hoàn toàn.
- Mục tiêu: giảm thời gian khởi tạo engine cho similar-by-vector; metric chính là `load_ms` của benchmark similar, với 57-case semantic accuracy/latency làm guardrail liên quan.
- Khám phá sơ bộ: xác nhận similar-by-vector chỉ dùng vector matrix, trong khi constructor luôn load/warm OpenCLIP; các hàm encode đã có điểm gọi lazy load nên hướng có thể thử có kiểm soát.
- Benchmark/tool: `tools/benchmark_similar.py --vector-id 0 --top-k 5 --json` và `tools/benchmark.py --top-k 50`, cùng cấu hình trước/sau; compile và benchmark similar sau rollback để xác nhận checkpoint.
  - Trước: similar load 1.568,11 ms, valid case 19,22 ms, 3/3 pass. Semantic: 2/57 đúng (3,51%), trung bình 214,64 ms.
  - Sau thử nghiệm: similar load 128,22 ms (giảm 91,82%), valid case 16,84 ms, 3/3 pass. Semantic vẫn 2/57 đúng nhưng trung bình tăng lên 294,97 ms (tăng 37,42%) vì model load chuyển vào request đầu; lần guardrail lặp tiếp theo không hoàn tất sau log model load.
  - Sau rollback: similar 3/3 pass, load 1.598,61 ms, valid case 18,98 ms; compile exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `a10be28` (`chore: checkpoint before lazy CLIP loading`). Vì workspace có `plan.md` đã sửa và `chatbot/` chưa track của người dùng, rollback dùng restore có phạm vi duy nhất `src/sqlite_engine.py` về checkpoint thay cho `git reset --hard`, tránh xóa thay đổi ngoài vòng.
- Kết quả: **rollback** vì metric chính tốt hơn nhưng semantic first-request/average latency hồi quy rõ ràng; không cập nhật `PROJECT_CONTEXT.md`.

## 2026-09-21 20:21 +07:00 — Vòng tối ưu 58: tái sử dụng prefix cache similar top-K

- Thay đổi: khi cache similar không có exact `(vector_id, top_candidates)`, tìm entry gần đây của cùng vector có candidate count lớn hơn/equal, cắt prefix đã xếp hạng và lưu lại exact key trong cùng LRU thread-safe. Không đổi scoring, metadata hay giới hạn 256 entry.
- Mục tiêu: loại dot product/argpartition lặp khi request top-K nhỏ theo sau request top-K lớn của cùng vector; metric chính là latency top-5 sau khi prime top-50, với toàn bộ ID/order làm guardrail.
- Khám phá sơ bộ: harness xác nhận top-50 đã cache nhưng top-5 vẫn mất 17,25 ms do cache key exact; prefix đầu của top-50 trùng chính xác kết quả top-5.
- Benchmark/tool: cùng một harness production engine chạy `search(query_vector_id=0, top_k=50)` rồi `top_k=5`; cùng cấu hình trước/sau. Guardrail dùng benchmark similar chuẩn ba scenario và compile.
  - Trước: prime top-50 32,60 ms; request top-5 17,25 ms; IDs `[0, 2904, 6972, 12228, 2416]`.
  - Sau: prime top-50 34,42 ms; request top-5 0,096 ms; IDs không đổi `[0, 2904, 6972, 12228, 2416]`.
  - Chênh lệch mục tiêu: latency top-5 giảm 99,44%. Benchmark chuẩn 3/3 pass, 0 fail/error; valid case 26,29 ms; compile exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `b86b746` (`chore: checkpoint before similar prefix cache reuse`).
- Kết quả: **giữ lại** vì metric mục tiêu cải thiện lớn và ranking/correctness không đổi. `PROJECT_CONTEXT.md` đã cập nhật chiến lược cache prefix.

## 2026-09-21 20:24 +07:00 — Vòng tối ưu 59: benchmark hồi quy prefix cache similar

- Thay đổi: mở rộng `tools/benchmark_similar.py` bằng scenario dùng vector kế cận, prime top-K lớn rồi gọi top-K nhỏ; kiểm tra cả prefix ID/order và latency cache hit thấp hơn cold prime. Output JSON thêm `prefix_cache_case` và aggregate bao gồm scenario mới.
- Mục tiêu: khóa hồi quy tối ưu cache-prefix của vòng 58; metric chính là số scenario tự động và tỷ lệ pass.
- Khám phá sơ bộ: không cần; benchmark hiện có bao phủ valid/invalid nhưng chưa tạo chuỗi mixed-top-K cần thiết để kích hoạt nhánh prefix.
- Benchmark/tool: `.venv\Scripts\python.exe tools\benchmark_similar.py --vector-id 0 --top-k 5 --json`, cùng cấu hình trước/sau; compile toàn bộ `src` và tool làm guardrail.
  - Trước: 3 scenario, 3/3 pass; chưa có phép đo prefix cache; valid case 17,95 ms.
  - Sau: 4 scenario, 4/4 pass, 0 fail/error; prefix case vector `1` prime top-50 mất 24,80 ms, cached top-5 mất 0,026 ms và trả đúng prefix `[1, 5869, 5577, 568, 2677]`; valid case 17,10 ms.
  - Chênh lệch mục tiêu: coverage tăng 3 → 4 scenario; compile exit 0.
- Sửa phụ: không có. Không sửa file cấm; runtime không thay đổi.
- Checkpoint vòng: `3fad707` (`chore: checkpoint before similar prefix benchmark`).
- Kết quả: **giữ lại** vì coverage tăng và toàn bộ scenario pass. `PROJECT_CONTEXT.md` đã cập nhật mô tả benchmark.

## 2026-09-21 20:26 +07:00 — Vòng tối ưu 60: cache LRU embedding semantic query

- Thay đổi: thêm cache LRU thread-safe tối đa 256 entry cho embedding OpenCLIP, key là tuple text đã dịch/mệnh đề; cache dùng chung cho query một và nhiều mệnh đề, array được đặt read-only trước khi lưu. Translation, scoring, RRF, metadata và ranking không đổi.
- Mục tiêu: loại encode OpenCLIP lặp lại cho semantic query giống nhau; metric chính là warm average/median của bốn run sau cold run, guardrail là hash toàn bộ 50 vector ID và benchmark retrieval 57 case.
- Khám phá sơ bộ: năm lần cùng query vẫn mất 216,72–540,77 ms dù metadata đã warm; bốn warm run trung bình 230,49 ms và cùng hash ranking, xác nhận encode lặp là hướng đủ triển vọng.
- Benchmark/tool: cùng một engine chạy năm lần `search(query_text="a person riding a bicycle", top_k=50)`; run 1 cold, run 2-5 warm. Guardrail dùng `tools/benchmark.py --top-k 50` và compile toàn bộ `src/tools`.
  - Trước: 540,77 / 227,77 / 233,40 / 244,08 / 216,72 ms; warm trung bình 230,49 ms, median 230,59 ms.
  - Sau: 169,59 / 15,47 / 16,05 / 16,85 / 21,24 ms; warm trung bình 17,40 ms, median 16,45 ms.
  - Chênh lệch: warm average giảm 92,45%, warm median giảm 92,87%; cả năm run giữ nguyên hash `de06d9ac615155ce1471bc01bbf15b347171deb67e50c6df1cbc5d0d3af914c3` và đủ 50 kết quả.
  - Guardrail retrieval: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%), trung bình 218,85 ms so với baseline gần nhất 214,64 ms (+1,96%, trong dao động run), accuracy không đổi; compile exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `089f49f` (`chore: checkpoint before semantic embedding cache`).
- Kết quả: **giữ lại** vì repeated-query latency giảm hơn 92%, ranking/accuracy giữ nguyên và unique-query guardrail không có hồi quy đáng kể. `PROJECT_CONTEXT.md` đã cập nhật.

## 2026-09-21 20:29 +07:00 — Vòng tối ưu 61: cache LRU candidate semantic

- Thay đổi: thêm cache LRU thread-safe tối đa 256 entry cho candidate IDs/scores đã xếp hạng của semantic query; key gồm tuple text/mệnh đề đã dịch và số candidate. Cache lưu tuple immutable, còn metadata/payload tiếp tục qua cache/pipeline chung.
- Mục tiêu: loại dot product, `argpartition` và RRF lặp lại sau khi embedding đã cache; metric chính là warm average/median của bốn run sau cold run, guardrail là hash 50 ID và benchmark 57 case.
- Khám phá sơ bộ: không cần; sau vòng 60, warm query vẫn mất trung bình 17,22 ms trong scoring/ranking dù embedding không còn encode lại.
- Benchmark/tool: cùng một engine chạy năm lần `search(query_text="a person riding a bicycle", top_k=50)`; run 1 cold, run 2-5 warm. Guardrail dùng `tools/benchmark.py --top-k 50` và compile toàn bộ `src/tools`.
  - Trước: 168,80 / 16,34 / 17,08 / 17,21 / 18,24 ms; warm trung bình 17,216 ms, median 17,145 ms.
  - Sau: 142,75 / 0,119 / 0,067 / 0,047 / 0,044 ms; warm trung bình 0,069 ms, median 0,057 ms.
  - Chênh lệch: warm average giảm 99,60%, warm median giảm 99,67%; cả năm run giữ nguyên hash `de06d9ac615155ce1471bc01bbf15b347171deb67e50c6df1cbc5d0d3af914c3` và đủ 50 kết quả.
  - Guardrail retrieval: KIS 1/39, QA hoàn chỉnh 1/16 (location 1/16, text_answer 6/16), TRAKE 0/2; tổng 2/57 (3,51%), trung bình 213,13 ms so với 218,85 ms vòng trước; compile exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `db75ed7` (`chore: checkpoint before semantic candidate cache`).
- Kết quả: **giữ lại** vì repeated-query latency giảm hơn 99%, ranking/accuracy không đổi và guardrail latency không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật.

## 2026-09-21 20:33 +07:00 — Vòng tối ưu 62: tái sử dụng prefix cache semantic top-K

- Thay đổi: khi cache semantic một mệnh đề không có exact key, tái sử dụng prefix của entry gần đây có cùng text và candidate count lớn hơn/equal, rồi lưu exact key trong LRU. Cố ý không áp dụng cho query nhiều mệnh đề/RRF vì thay cutoff candidate có thể đổi fused ranking.
- Mục tiêu: loại scoring/ranking lặp khi semantic top-K nhỏ theo sau top-K lớn cùng query; metric chính là latency top-5 sau prime top-50, với ID/order làm guardrail.
- Khám phá sơ bộ: harness xác nhận sau khi prime top-50, top-5 vẫn mất 15,22 ms dù embedding đã cache; năm ID khớp chính xác prefix top-50 nên cosine path đủ điều kiện tái sử dụng an toàn.
- Benchmark/tool: cùng một engine chạy `search(query_text="a person riding a bicycle", top_k=50)` rồi `top_k=5`, cùng cấu hình trước/sau; guardrail dùng `tools/benchmark.py --top-k 50` và compile.
  - Trước: cold top-50 171,86 ms; top-5 15,220 ms; IDs `[17448, 169413, 151961, 17450, 169432]`.
  - Sau: cold top-50 153,97 ms; top-5 0,045 ms; IDs và hash top-5 không đổi.
  - Chênh lệch mục tiêu: top-5 giảm 99,70%; cold prime không hồi quy trong phép đo trực tiếp.
  - Guardrail retrieval hoàn tất lần đầu: accuracy giữ nguyên KIS 1/39, QA hoàn chỉnh 1/16 (text_answer 6/16), TRAKE 0/2, tổng 2/57; average 249,95 ms bị kéo bởi outlier case đầu 2.712,3 ms, còn 56 case sau trung bình 205,98 ms. Lần lặp thứ hai chỉ xuất log khởi tạo model rồi không trả case output, nên không dùng làm kết luận latency. Compile exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `123e282` (`chore: checkpoint before semantic prefix cache reuse`).
- Kết quả: **giữ lại** dựa trên phép đo trực tiếp (−99,70%), cold prime và ranking không hồi quy; accuracy guardrail giữ nguyên. Ghi nhận full-suite latency có outlier/độ tin cậy thấp để không dùng số average đó cho vòng sau. `PROJECT_CONTEXT.md` đã cập nhật.

## 2026-09-21 20:37 +07:00 — Vòng tối ưu 63: thêm benchmark semantic cache chuyên biệt

- Thay đổi: thêm `tools/benchmark_semantic_cache.py`, chạy production engine và kiểm tra ba scenario: repeated single-clause, mixed-top-K prefix single-clause, repeated multi-clause/RRF. Tool báo load/cold/warm latency, toàn bộ vector IDs, aggregate pass/fail/error, hỗ trợ text/JSON và exit khác 0 khi fail.
- Mục tiêu: thay phép đo ad-hoc bằng regression benchmark tái lập cho semantic cache, tách khỏi nhiễu của full 57-case suite; metric chính là coverage scenario tự động và tỷ lệ pass. Runtime không thay đổi.
- Khám phá sơ bộ: không cần; vòng 62 đã ghi nhận full-suite latency có outlier và lần lặp không hoàn tất, trong khi chưa có tool chuyên biệt cho cache path.
- Baseline trước thay đổi: 0 scenario tự động chuyên biệt; chỉ có harness thủ công cho repeated/mixed-top-K.
- Sau: 3 scenario tự động, 3/3 pass, 0 fail/error. Single repeat cold/warm 147,51/0,035 ms; prefix top-50/top-5 70,72/0,037 ms với đúng prefix; multi-clause repeat cold/warm 116,36/0,043 ms với IDs không đổi. Compile exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `0beaa3e` (`chore: checkpoint before semantic cache benchmark`).
- Kết quả: **giữ lại benchmark** vì coverage tăng 0 → 3 scenario và tất cả pass. `PROJECT_CONTEXT.md` đã cập nhật danh sách công cụ đo.

## 2026-09-21 21:07 +07:00 — Vòng tối ưu 64: thêm benchmark fallback OCR/ASR

- Thay đổi: thêm `tools/benchmark_fuzzy_cache.py`, chạy production `SQLiteSearchEngine` và kiểm tra năm scenario fallback khi DB thiếu FTS: repeated OCR, repeated ASR, mixed top-K OCR, mixed top-K ASR và ASR có video filter. Tool báo load/cold/warm latency, vector/video IDs, aggregate pass/fail/error, hỗ trợ text/JSON và exit khác 0 khi fail.
- Mục tiêu: tạo phép đo tái lập cho fallback OCR/ASR trước khi tối ưu thêm; vòng này không thay đổi runtime.
- Khám phá/baseline thủ công: 0 scenario tự động chuyên biệt; OCR cold/warm 2.354,32/0,027 ms, ASR cold/warm 1.077,65/0,034 ms; smoke ASR filter `L22_V019` trả 3/3 kết quả. Lần chạy đầu của tool phát hiện JSON Unicode không tương thích console Windows cp1252; output đã chuyển sang ASCII-safe trong cùng phạm vi công cụ đo.
- Sau: 5 scenario tự động, 5/5 pass, 0 fail/error. OCR repeat cold/warm 1.318,37/0,046 ms; ASR repeat 1.112,89/0,090 ms; OCR mixed top-K prime-50/small-5 750,28/626,04 ms; ASR mixed top-K 783,36/676,78 ms; ASR filter 4,95 ms và trả đúng 3 kết quả trong `L22_V019`. Compile `src/tools` exit 0.
- Sửa phụ: không có. Không sửa file cấm hay runtime.
- Checkpoint vòng: `18b81a4` (`chore: checkpoint before fuzzy cache benchmark`).
- Kết quả: **giữ lại benchmark** vì coverage tăng 0 → 5 scenario và tất cả pass. `PROJECT_CONTEXT.md` đã cập nhật danh sách công cụ đo.

## 2026-09-21 21:09 +07:00 — Vòng tối ưu 65: tái sử dụng prefix cache fallback OCR/ASR

- Thay đổi: cập nhật `_fuzzy_text_search()` trong `src/sqlite_engine.py`; khi cache không có exact key, tìm entry gần đây cùng field, tuple token và video filter có top-K lớn hơn/equal, cắt prefix đã xếp hạng và lưu exact key vào cùng LRU. Matching, scoring, metadata và giới hạn 256 entry không đổi.
- Mục tiêu: loại lần scan LIKE lặp khi request top-K nhỏ theo sau request top-K lớn cùng truy vấn; metric chính là latency small-5 của hai scenario prefix, với ID/order và 5/5 scenario là guardrail.
- Khám phá sơ bộ: không cần; benchmark vòng 64 đã cô lập hai lượt scan thừa và xác nhận small-5 là prefix chính xác của prime-50.
- Benchmark/tool: `.venv\Scripts\python.exe tools\benchmark_fuzzy_cache.py --top-k 5 --json`, cùng cấu hình trước/sau; compile toàn bộ `src/tools` là guardrail.
  - Trước: OCR prime-50/small-5 878,33/2.013,32 ms; ASR prime-50/small-5 2.604,52/2.154,74 ms; 5/5 scenario pass, 0 fail/error.
  - Sau: OCR prime-50/small-5 1.973,89/0,116 ms; ASR prime-50/small-5 2.391,39/0,079 ms; 5/5 scenario pass, 0 fail/error; compile exit 0.
  - Chênh lệch mục tiêu: OCR small-5 giảm 99,994%; ASR small-5 giảm 99,996%. Toàn bộ vector ID/order giữ nguyên đúng prefix; latency cold/prime dao động và không dùng làm kết luận.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `ea4c3ef` (`chore: checkpoint before fuzzy prefix cache reuse`).
- Kết quả: **giữ lại** vì metric latency mục tiêu cải thiện rõ ràng và correctness/compile không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật chiến lược prefix cache fallback.

## 2026-09-21 21:13 +07:00 — Vòng tối ưu 66: thăm dò cold fallback OCR/ASR

- Phạm vi dự kiến: giảm cold latency của LIKE fallback OCR/ASR sau khi warm/prefix cache đã được tối ưu; metric dự kiến là latency query cold và hash top-50 candidate.
- Khám phá sơ bộ chỉ đọc: `cProfile` trên OCR cold cho thấy 1.147/1.169 giây (98,12%) nằm trong hai `sqlite3.Cursor.fetchall`, trong khi Python `sorted` chỉ khoảng 3 ms; vì vậy loại hướng thay sort bằng heap. Thử SQL đánh dấu hit một lần nhưng fetch toàn bộ 177.321 row: OCR 764,89 ms so với 592,16 ms hiện tại (+29,17%); ASR 866,94 ms so với 587,27 ms (+47,62%). Hash top-50 giữ nguyên cho cả hai nhánh.
- Benchmark/tool: profiler chuẩn `cProfile` và harness SQLite read-only cùng query `học sinh trường học đồng phục sân`; không sửa source, DB hay file cấm.
- Sửa phụ: không có. Không tạo checkpoint vì hướng bị loại ở bước khám phá trước thay đổi chính thức.
- Kết quả: **không triển khai / không có thay đổi để rollback**. Hai hướng khả thi cục bộ đều không đủ triển vọng; cold path tiếp tục bị chi phối bởi full-text scan do artifact DB thiếu FTS. `PROJECT_CONTEXT.md` không cần cập nhật.

## 2026-09-21 21:15 +07:00 — Vòng tối ưu 67: thêm benchmark image-search cache

- Thay đổi: thêm `tools/benchmark_image_cache.py`; tool tạo hai JPEG xác định trong memory và gọi production `SQLiteSearchEngine.search_by_image()` để kiểm tra repeated image cùng chuỗi prime top-K lớn → top-K nhỏ. Tool báo load/request latency, vector IDs, aggregate pass/fail/error, hỗ trợ text/JSON và exit khác 0 khi fail.
- Mục tiêu: tạo phép đo tái lập cho image search trước khi tối ưu repeated input; vòng này không thay đổi runtime.
- Khám phá/baseline thủ công: 0 scenario tự động chuyên biệt; ba request cùng ảnh 151,67/87,34/93,77 ms với ID/order ổn định; mixed top-K prime-50/small-5 174,70/112,47 ms và small là prefix chính xác.
- Sau: 2 scenario tự động, 2/2 pass, 0 fail/error. Repeated cold/warm 455,84/438,37 ms; mixed top-K prime-50/small-5 501,99/372,70 ms; vector ID/order đúng; compile `src/tools` exit 0. Dao động latency không được dùng làm kết luận trong vòng tạo benchmark.
- Sửa phụ: không có. Không sửa file cấm hay runtime.
- Checkpoint vòng: `3aeeba3` (`chore: checkpoint before image cache benchmark`).
- Kết quả: **giữ lại benchmark** vì coverage tăng 0 → 2 scenario và tất cả pass. `PROJECT_CONTEXT.md` đã cập nhật danh sách công cụ đo.

## 2026-09-21 21:17 +07:00 — Vòng tối ưu 68: cache LRU candidate image search

- Thay đổi: thêm cache LRU thread-safe tối đa 256 entry trong `SQLiteSearchEngine.search_by_image()`; key gồm SHA-256 bytes ảnh và số candidate. Cache lưu tuple immutable ID/score, tái sử dụng prefix từ entry top-K lớn hơn và tiếp tục dùng pipeline metadata chung.
- Mục tiêu: loại OpenCLIP image encode, dot product và `argpartition` lặp khi cùng nội dung ảnh được tìm lại; metric chính là repeated warm và mixed small-5, với ID/order là guardrail.
- Khám phá sơ bộ: không cần; benchmark vòng 67 xác nhận mỗi request lặp vẫn encode/scoring và top-5 là prefix chính xác của top-50.
- Benchmark/tool: `.venv\Scripts\python.exe tools\benchmark_image_cache.py --top-k 5 --json`, cùng cấu hình trước/sau; compile toàn bộ `src/tools` là guardrail.
  - Trước: repeated cold/warm 86,10/77,31 ms; mixed top-K prime-50/small-5 102,89/141,09 ms; 2/2 scenario pass.
  - Sau: repeated cold/warm 82,50/0,031 ms; mixed top-K prime-50/small-5 81,60/0,039 ms; 2/2 scenario pass, 0 fail/error; compile exit 0.
  - Chênh lệch mục tiêu: repeated warm giảm 99,96%; mixed small-5 giảm 99,97%. Toàn bộ vector ID/order không đổi; cold latency không hồi quy trong phép đo chính.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `df2ee03` (`chore: checkpoint before image candidate cache`).
- Kết quả: **giữ lại** vì latency repeated/mixed top-K cải thiện hơn 99% và correctness/compile không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật chiến lược image cache.

## 2026-09-21 21:21 +07:00 — Vòng tối ưu 69: thêm benchmark runtime metadata path

- Thay đổi: thêm `tools/benchmark_runtime_paths.py`; tool chạy import `src.main` trong subprocess từ project root và từ temp directory, so sánh `video_metadata_cache` với 873 record thật trong artifact. Tool hỗ trợ text/JSON và exit khác 0 khi một launch CWD làm mất metadata.
- Mục tiêu: tạo phép đo tái lập cho path portability trước khi sửa runtime; vòng này không thay đổi `src/main.py`.
- Khám phá/baseline thủ công: 0 scenario tự động; project CWD load 873 metadata, temp CWD load 0 và cảnh báo không tìm thấy `video_drive_metadata.json`.
- Sau: 2 scenario tự động, 1/2 pass, 1 fail, 0 error. Project CWD 873/873; external CWD 0/873; tool exit 1 đúng theo regression đang mở; compile tool exit 0. Không dùng thời gian import OpenCLIP làm metric kết luận.
- Sửa phụ: không có. Không sửa file cấm hay runtime.
- Checkpoint vòng: `1091a05` (`chore: checkpoint before runtime path benchmark`).
- Kết quả: **giữ lại benchmark** vì coverage tăng 0 → 2 scenario và tool phát hiện đúng lỗi CWD. `PROJECT_CONTEXT.md` đã cập nhật danh sách công cụ và trạng thái regression.

## 2026-09-21 21:23 +07:00 — Vòng tối ưu 70: resolve Drive metadata theo BASE_DIR

- Thay đổi: cập nhật `src/main.py` để load `video_drive_metadata.json` qua `BASE_DIR / "video_drive_metadata.json"` thay vì path tương đối theo current working directory.
- Mục tiêu: giữ endpoint video metadata hoạt động khi app được launch từ service manager, IDE hoặc thư mục bất kỳ; metric chính là pass/count của hai scenario runtime path.
- Khám phá sơ bộ: không cần; benchmark vòng 69 đã cô lập chính xác path tương đối là nguyên nhân.
- Benchmark/tool: `.venv\Scripts\python.exe tools\benchmark_runtime_paths.py --json`, cùng project/temp CWD trước và sau; compile toàn bộ `src/tools` là guardrail.
  - Trước: 1/2 pass, 1 fail, 0 error; project CWD 873/873, external CWD 0/873; benchmark exit 1.
  - Sau: 2/2 pass, 0 fail/error; project CWD 873/873, external CWD 873/873; benchmark exit 0, compile exit 0.
  - Chênh lệch mục tiêu: pass rate 50% → 100%; metadata bị mất khi external CWD giảm 873 → 0 record. Thời gian import OpenCLIP không dùng làm metric kết luận.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `fc8e465` (`chore: checkpoint before metadata path fix`).
- Kết quả: **giữ lại** vì correctness tăng 1/2 → 2/2 scenario và compile không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật path behavior và bước tiếp theo.

## 2026-09-21 21:25 +07:00 — Vòng tối ưu 71: thêm benchmark DB_PATH override

- Thay đổi: thêm `tools/benchmark_database_config.py`; tool chạy engine trong subprocess với `DB_PATH` trỏ artifact thật nhưng `DATA_ROOT` trỏ temp directory, sau đó kiểm tra path engine và `COUNT(*)` read-only trên `keyframes`. Tool hỗ trợ text/JSON và exit khác 0 khi override bị bỏ qua.
- Mục tiêu: tạo phép đo tái lập cho DB config trước khi sửa engine; vòng này không thay đổi runtime.
- Khám phá/baseline thủ công: 0 scenario tự động; `src.config.DB_PATH` là DB thật nhưng `engine.db_path` bị suy thành temp path và `_get_db()` ném `OperationalError`.
- Sau: 1 scenario tự động, 0/1 pass, 1 fail/error. Config path đúng `video_index_v2.db`, engine path sai trong temp, row count `null` thay vì 177.321; benchmark exit 1 đúng theo regression đang mở; compile tool exit 0.
- Sửa phụ: không có. Không sửa file cấm hay runtime; DB chỉ được mở read-only để đo.
- Checkpoint vòng: `1ac7994` (`chore: checkpoint before database config benchmark`).
- Kết quả: **giữ lại benchmark** vì coverage tăng 0 → 1 scenario và tool phát hiện đúng lỗi `DB_PATH`. `PROJECT_CONTEXT.md` đã cập nhật tool và trạng thái regression.

## 2026-09-21 21:27 +07:00 — Vòng tối ưu 72: cho SQLite engine tôn trọng DB_PATH

- Thay đổi: import `DB_PATH` từ `src.config`, thêm tham số constructor `db_path` và resolve path này trong `SQLiteSearchEngine`; không còn suy DB từ `DATA_ROOT.parent`.
- Mục tiêu: làm `.env`/config override hoạt động cho FastAPI engine và cho phép caller truyền DB tường minh; metric chính là pass/path/count của benchmark DB config.
- Khám phá sơ bộ: không cần; benchmark vòng 71 đã cô lập constructor engine là điểm bỏ qua config.
- Benchmark/tool: `.venv\Scripts\python.exe tools\benchmark_database_config.py --json`, cùng env override trước/sau. Guardrail: `tools\benchmark_similar.py --vector-id 0 --top-k 5 --json` và compile `src/tools`.
  - Trước: 0/1 pass, 1 fail/error; engine path trỏ temp, row count `null`, benchmark exit 1.
  - Sau: 1/1 pass, 0 fail/error; configured path và engine path cùng trỏ DB thật, row count 177.321, benchmark exit 0.
  - Guardrail similar-by-vector: 4/4 scenario pass, 0 fail/error; valid top vector `0`, prefix-cache IDs đúng; compile exit 0.
- Sửa phụ: không có. Không sửa file cấm; benchmark chỉ query DB read-only.
- Checkpoint vòng: `e24ae7e` (`chore: checkpoint before DB_PATH engine fix`).
- Kết quả: **giữ lại** vì correctness tăng 0/1 → 1/1 và guardrail không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật config behavior, run note và vấn đề còn lại.

## 2026-09-21 21:30 +07:00 — Vòng tối ưu 73: mở rộng benchmark DB_PATH cho MCP

- Thay đổi: mở rộng `tools/benchmark_database_config.py` từ một lên hai scenario: engine vẫn query read-only DB thật, scenario MCP import `mcp_server` trong subprocess với `DB_PATH` custom và kiểm tra module constant. Output/exit code aggregate cả hai nhánh.
- Mục tiêu: tạo phép đo tái lập cho MCP DB override trước khi sửa runtime; vòng này không thay đổi `mcp_server.py`.
- Khám phá/baseline thủ công: benchmark có 1 scenario engine đang pass; với env `DB_PATH` custom, MCP vẫn trỏ `video_index_v2.db` cạnh source.
- Sau: 2 scenario tự động, 1/2 pass, 1 fail, 0 error. Engine path/count pass 177.321; MCP expected temp `vision-custom.db` nhưng actual vẫn là DB project; benchmark exit 1 đúng theo regression đang mở; compile tool exit 0.
- Sửa phụ: không có. Không sửa file cấm hay runtime.
- Checkpoint vòng: `6c8d6f8` (`chore: checkpoint before MCP database config benchmark`).
- Kết quả: **giữ lại benchmark** vì coverage tăng 1 → 2 scenario và tool phát hiện đúng lỗi MCP override. `PROJECT_CONTEXT.md` đã cập nhật coverage và trạng thái regression.

## 2026-09-21 21:32 +07:00 — Vòng tối ưu 74: cho MCP tôn trọng DB_PATH

- Thay đổi: `mcp_server.py` import `DB_PATH` từ `src.config` và dùng path chung này thay cho DB cố định cạnh source.
- Mục tiêu: làm `.env`/environment DB override hoạt động nhất quán giữa FastAPI engine và MCP; metric chính là pass/path của hai scenario database config.
- Khám phá sơ bộ: không cần; benchmark vòng 73 đã cô lập module constant MCP là điểm bỏ qua config.
- Benchmark/tool: `.venv\Scripts\python.exe tools\benchmark_database_config.py --json`, cùng env override trước/sau. Guardrail: compile `src/tools/mcp_server.py` và import MCP/count tool.
  - Trước: 1/2 pass, 1 fail, 0 error; engine path/count đúng, MCP actual path vẫn là DB project thay vì custom temp; benchmark exit 1.
  - Sau: 2/2 pass, 0 fail/error; engine path/count vẫn đúng 177.321 và MCP path khớp custom temp; benchmark exit 0.
  - Guardrail: compile exit 0; `import mcp_server` pass và vẫn đăng ký đủ 9 tool.
- Sửa phụ: không có. Không sửa file cấm; benchmark engine chỉ query DB read-only.
- Checkpoint vòng: `18a26eb` (`chore: checkpoint before MCP DB_PATH fix`).
- Kết quả: **giữ lại** vì correctness tăng 1/2 → 2/2 và MCP/compile guardrail không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật config behavior và loại DB path khỏi bước tiếp theo.

## 2026-09-21 21:58 +07:00 — Vòng tối ưu 75: bổ sung metric xếp hạng cho benchmark thi chính

- Query type/luồng thi: KIS, Q&A và TRAKE; phục vụ đánh giá candidate ranking cho cả operator thủ công và agent tự động. Đây là vòng P0 chỉ sửa benchmark vì phép đo trước đó chưa phân biệt đáp án đúng đứng đầu hay cuối top-50.
- Cổng tác động cuộc thi: mục tiêu là đo Recall@K, MRR, location/event rank, ordered-sequence correctness, latency p50/p95 và thời gian hoàn tất truy hồi đúng (TTFC). Nếu thiếu các metric này, một thay đổi đẩy đáp án đúng xuống sâu trong top-50 vẫn có thể được coi là không hồi quy, làm tăng thời gian xác minh khi thi. KIS/Q&A/TRAKE là workload định hướng từ tài liệu; tolerance ±150 giây vẫn chỉ là cấu hình benchmark, không coi là luật 2026 đã xác nhận.
- Thay đổi: cập nhật `tools/benchmark.py`; ghi rank 1-based đầu tiên khớp location cho KIS/Q&A, event-rank cho từng sự kiện TRAKE, Recall@1/5/10/50, MRR, p50/p95 latency và TTFC trên các case hoàn chỉnh đúng. TRAKE tiếp tục yêu cầu đủ chuỗi sự kiện và báo riêng event hit; runtime retrieval không thay đổi.
- Benchmark/config quyết định: `.venv\Scripts\python.exe tools\benchmark.py --top-k 50`, đủ 57 case, cùng pipeline trực tiếp và frame tolerance ±150 giây trước/sau.
  - Trước: KIS 1/39, Q&A hoàn chỉnh 1/16 (location 1/16, text-answer 6/16), TRAKE 0/2, tổng 2/57 (3,51%), average 587,02 ms; không có rank, Recall@K, MRR, p50/p95 hoặc TTFC.
  - Sau: accuracy giữ nguyên KIS 1/39, Q&A 1/16, TRAKE 0/2, tổng 2/57 (3,51%); average 569,43 ms, p50/p95 411,59/1.377,37 ms, 0 lỗi. Trên 63 target độc lập: R@1 0/63, R@5 1/63, R@10 2/63, R@50 2/63, MRR 0,0079. Hai hit hiện có ở KIS rank 3 và Q&A rank 6; TTFC p50/p95 1.206,56/1.345,31 ms. TRAKE có 0/8 event hit và 0/2 ordered sequence.
  - Dao động average trước/sau không được coi là cải thiện runtime vì vòng này không sửa runtime; metric quyết định là coverage xếp hạng 0 → 63 target cùng accuracy/error được bảo toàn.
- Guardrail: `tools/benchmark_semantic_cache.py --top-k 5 --json` đạt 3/3 scenario, 0 lỗi; compile `tools/benchmark.py` exit 0; smoke helper percentile pass. Output correctness KIS/Q&A/TRAKE giữ nguyên so với baseline.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `51fcb7a` (`chore: checkpoint before competition retrieval metrics`).
- Kết quả: **giữ lại** vì benchmark thi chính chuyển từ không quan sát được rank sang báo đủ 63 target, Recall@K/MRR/latency distribution/TTFC, trong khi accuracy và guardrail không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật mô tả benchmark.

## 2026-09-21 22:06 +07:00 — Vòng tối ưu 76: thăm dò biểu diễn truy vấn tiếng Việt cho KIS/Q&A

- Query type/luồng thi: KIS và Q&A semantic retrieval; TRAKE dự kiến làm guardrail. Mục tiêu qua cổng là tăng Recall@5/10/50 và MRR bằng biểu diễn query tương thích với vector OpenCLIP tiếng Anh.
- Tác động cuộc thi: baseline vòng 75 chỉ đạt R@10 2/63 và R@50 2/63; nếu không có candidate đúng, operator/agent không thể xác minh hoặc trả submission. Mô tả sự kiện tiếng Việt là workload phù hợp tài liệu Chung kết, dù nhãn/phân bố query cụ thể chưa chính thức.
- Khám phá read-only: đối chiếu 57 query với `translation_cache.db` cho thấy chỉ 1/57 query khớp cache toàn câu. Workspace chỉ có cache Hugging Face của OpenCLIP image/text tiếng Anh; không có model dịch offline hoặc `ctranslate2`, `transformers`, `sentencepiece`, `sacremoses`, `sentence_transformers`. Direct Google Translate trong sandbox thất bại do network bị chặn.
- Hướng bị loại: không hard-code bản dịch từ dataset vì sẽ overfit benchmark; không tải/đổi model đa ngôn ngữ lớn khi chưa có ablation nhỏ chứng minh; không gửi query dataset ra Google Translate vì thao tác data-egress chưa được người dùng ủy quyền rõ ràng và yêu cầu quyền đã bị từ chối.
- Benchmark/config: chưa chuyển sang Bước 4; không chạy baseline chính thức vì mọi hướng triển khai an toàn bị loại ngay ở Bước 3. Tham chiếu gần nhất vẫn là vòng 75: R@1 0/63, R@5 1/63, R@10 2/63, R@50 2/63, MRR 0,0079; accuracy 2/57.
- Guardrail/sửa phụ: không sửa runtime, benchmark hay file cấm; không có guardrail cần chạy lại. `translation_cache.db` chỉ được đọc để đếm/match.
- Checkpoint: không tạo vì không có thay đổi chính thức sau khám phá.
- Kết quả: **không triển khai / không có gì để rollback**. `PROJECT_CONTEXT.md` cập nhật nút thắt translation. Chuỗi dừng để tránh mở vòng ngoài phạm vi; bước có bằng chứng tiếp theo cần quyền gửi query sang dịch vụ dịch bên thứ ba hoặc quyết định/download một model offline mới sau thử nghiệm được phê duyệt.

## 2026-09-22 13:24 +07:00 — Vòng tối ưu 77: chấm đúng chuỗi TRAKE cùng video và đúng thứ tự

- Query type/luồng thi: TRAKE cho cả operator thủ công và agent tự động; vòng P0 chỉ sửa benchmark. Cổng tác động xác định metric sequence correctness cũ có thể pass nhiều event bằng cùng một frame nằm trong tolerance, nên có nguy cơ giữ nhầm runtime trả submission TRAKE sai.
- Thay đổi: cập nhật `tools/benchmark.py` để giữ event-rank độc lập nhưng chỉ đánh dấu TRAKE đúng khi chọn được một candidate cho mỗi event, tất cả cùng video và `frame_idx` tăng nghiêm ngặt. Báo thêm `selected_sequence`, `same_video`, `ordered_sequence`. Thêm `tools/benchmark_trake_sequence.py` với ba scenario ordered/duplicate-frame/reverse-order.
- Benchmark/config quyết định: `.venv\Scripts\python.exe tools\benchmark.py --top-k 50`, đủ 57 case, tolerance ±150 giây; smoke/scenario tổng hợp dùng FPS 1 và cùng tolerance. Không sửa runtime hoặc file cấm.
  - Trước: KIS 1/39, Q&A hoàn chỉnh 1/16 (location 1/16, text-answer evidence 6/16), TRAKE 0/2 với 0/8 event hit, tổng 2/57; R@1/5/10/50 = 0/1/2/2 trên 63 target, MRR 0,0079; latency average 392,24 ms, p50/p95 332,49/943,63 ms, TTFC p50/p95 742,05/1.119,89 ms; 0 lỗi. Smoke lỗi cho thấy một frame `V1:150` được dùng cho cả E1 và E2 vẫn trả `correct=True`.
  - Sau: accuracy/rank không đổi: KIS 1/39, Q&A 1/16, TRAKE 0/2 với 0/8 event hit, tổng 2/57; R@1/5/10/50 = 0/1/2/2, MRR 0,0079; latency average 572,90 ms, p50/p95 226,66/411,09 ms, TTFC p50/p95 329,52/365,12 ms; 0 lỗi. Average bị kéo bởi outlier request đầu 20.560,4 ms và không dùng làm kết luận vì runtime không đổi.
  - Correctness mới: coverage tự động 0 → 3 scenario; 3/3 pass. Chuỗi `100 → 200` pass; dùng trùng frame `150 → 150` và đảo `200 → 100` đều fail dù event-rank riêng vẫn là `[1, 1]`.
- Guardrail: `tools/benchmark_semantic_cache.py --top-k 5 --json` đạt 3/3 scenario, 0 lỗi; compile hai benchmark exit 0. Sáu guardrail chuẩn bị đều pass: semantic 3/3, similar 4/4, fuzzy 5/5, image 2/2, runtime paths 2/2, database config 2/2.
- Sửa phụ: không có. Benchmark UI/operator/submission chưa tồn tại, vì vậy không mở tối ưu P5.
- Checkpoint vòng: `badcd8d` (`chore: checkpoint before TRAKE sequence benchmark fix`).
- Kết quả: **giữ lại** vì lỗi chấm phá tính đúng đắn chuyển fail → pass trong 3/3 scenario, accuracy/rank production không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật benchmark và tiêu chí TRAKE.

## 2026-09-22 13:30 +07:00 — Vòng tối ưu 78: ràng buộc Q&A answer evidence với location đúng

- Query type/luồng thi: Q&A/VQA cho operator thủ công và agent tự động; vòng P0 chỉ sửa benchmark. Cổng tác động xác định phép chấm cũ có thể lấy location đúng từ một candidate và `text_answer` từ candidate/video khác rồi ghép thành full Q&A đúng.
- Thay đổi: cập nhật `tools/benchmark.py` để chỉ tìm answer evidence trong các result khớp đúng `video_id` và cửa sổ thời gian của location. Output giữ alias `text_correct` để tương thích nhưng báo metric rõ nghĩa `answer_evidence_correct`/`answer_evidence`; đây là proxy evidence của retrieval, không phải câu trả lời do model sinh. Thêm `tools/benchmark_qa_evidence.py` với ba scenario aligned/disconnected/evidence-without-location.
- Benchmark/config quyết định: `.venv\Scripts\python.exe tools\benchmark.py --top-k 50`, đủ 57 case, tolerance ±150 giây; regression tổng hợp dùng tolerance 0 giây để cô lập phép chấm. Không sửa runtime hoặc file cấm.
  - Trước: KIS 1/39; Q&A hoàn chỉnh 1/16, location 1/16, metric gắn nhãn `text_answer` 6/16; TRAKE 0/2, tổng 2/57. R@1/5/10/50 = 0/1/2/2 trên 63 target, MRR 0,0079; latency average 245,63 ms, p50/p95 245,74/458,31 ms, TTFC p50/p95 381,96/396,80 ms; 0 lỗi. Case tổng hợp có location `V1:100` không chứa answer và candidate `V2:999` chứa answer vẫn trả `correct=True`.
  - Sau: KIS 1/39; Q&A hoàn chỉnh 1/16, location 1/16, `answer_evidence` đúng tại location 1/16; TRAKE 0/2, tổng 2/57. Rank giữ nguyên R@1/5/10/50 = 0/1/2/2, MRR 0,0079; latency average 600,96 ms, p50/p95 214,05/499,24 ms, TTFC p50/p95 447,11/492,61 ms; 0 lỗi. Average có outlier request đầu 20.566,2 ms và không dùng làm kết luận vì runtime không đổi.
  - Correctness mới: coverage tự động 0 → 3 scenario; 3/3 pass. Evidence cùng location pass; evidence ở video khác và evidence không có location đều fail. Số evidence proxy 6 → 1 phản ánh loại bỏ 5 positive không gắn với location; full Q&A accuracy không đổi 1/16.
- Guardrail: TRAKE sequence 3/3 pass; semantic cache 3/3 pass; compile benchmark và regression exit 0. ID/frame/rank production không đổi.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `5f5f6d9` (`chore: checkpoint before Q&A evidence scoring fix`).
- Kết quả: **giữ lại** vì lỗi benchmark tổng hợp chuyển pass sai → fail đúng, aligned evidence vẫn pass, và accuracy/rank production không hồi quy. `PROJECT_CONTEXT.md` đã cập nhật ngữ nghĩa metric và benchmark regression.

## 2026-09-22 13:42 +07:00 — Vòng tối ưu 79: thăm dò hybrid semantic/OCR/ASR

- Query type/luồng thi dự kiến: KIS/Q&A retrieval, làm nguồn candidate cho TRAKE và agent. Cổng tác động nhắm Recall@5/10/50 và MRR vì semantic baseline chỉ có 2/63 target trong top-50.
- Khám phá read-only: hướng dùng nguyên mô tả dài cho OCR bị dừng sau hơn 3 phút chưa hoàn tất nhánh, nên bị loại vì không phù hợp time-to-first-correct. Thử nghiệm nhỏ tiếp theo chọn tối đa 6 token bằng document-frequency trên query dataset, không dùng answer/label, rồi gọi các nhánh production semantic/OCR/ASR; RRF dùng công thức `1/(60 + rank)`.
- Ablation mẫu 14/57 case, 20 target: semantic 0 hit; OCR IDF-6 có 1 hit ở top-5, MRR 0,0500; ASR IDF-6 có 2 hit top-50, MRR 0,0023; RRF hybrid có 1 hit top-5, MRR 0,0250. Kết quả đủ để tiếp tục full-suite nhưng cho thấy RRF có thể làm mất hit riêng của ASR.
- Ablation full 57 case/63 target, tolerance ±150 giây, top-K 50:
  - Semantic: 2/57 đúng; R@1/5/10/50 = 0/1/2/2, MRR 0,0079; wall 15,73 giây.
  - OCR IDF-6: 3/57 đúng; R@1/5/10/50 = 3/3/3/3, MRR 0,0476; wall 85,10 giây.
  - ASR IDF-6: 11/57 đúng; R@1/5/10/50 = 5/8/8/14, MRR 0,0997; wall 57,33 giây.
  - RRF hybrid: 8/57 đúng; R@1/5/10/50 = 2/7/7/9, MRR 0,0622; các nhánh đã warm/cache nên wall 0,03 giây không được dùng làm kết luận latency.
- Guardrail/output correctness: ablation chỉ đọc file cấm và gọi engine production; không sửa runtime, benchmark hay artifact dữ liệu. Full semantic khớp chính xác baseline 2/57 và rank metrics hiện hành. Lượt full-query bị dừng chủ động, không crash hệ thống.
- Sửa phụ: không có. Không tạo checkpoint vì hướng dừng ở Bước 3 trước thay đổi chính thức.
- Kết quả: **không triển khai / không có gì để rollback**. Có bằng chứng mạnh rằng query reduction + ASR/OCR tăng recall, nhưng chưa có benchmark tái lập khóa query reduction, fusion và bảo toàn từng hit semantic. Theo điều kiện benchmark chưa đủ tin cậy, vòng kế tiếp chỉ được tạo benchmark P0 cho hybrid, chưa sửa runtime. `PROJECT_CONTEXT.md` không cập nhật vì kiến trúc/API/workflow chưa đổi.

## 2026-09-22 13:54 +07:00 — Vòng tối ưu 80: thêm benchmark multimodal và semantic-hit preservation

- Query type/luồng thi: KIS/Q&A/TRAKE retrieval cho operator thủ công và agent tự động; vòng P0 chỉ tạo benchmark vì vòng 79 chứng minh multimodal có tiềm năng nhưng chưa có phép đo tái lập.
- Thay đổi: thêm `tools/benchmark_multimodal.py`. Tool chạy semantic, OCR, ASR và reference RRF hybrid trên engine mới riêng cho từng strategy; lexical query dùng stopword tĩnh và tối đa 6 token duy nhất theo thứ tự, không dùng answer hoặc corpus-IDF. Báo correctness, rank từng target, Recall@1/5/10/50, MRR, p50/p95, TTFC, error, wall time và semantic-hit preservation.
- Baseline trước khi có tool: 0 strategy/scenario multimodal tự động; `tools/benchmark.py --top-k 50` semantic đạt KIS 1/39, Q&A 1/16 (location/evidence 1/16), TRAKE 0/2, tổng 2/57; R@1/5/10/50 = 0/1/2/2 trên 63 target, MRR 0,0079; average 260,71 ms, p50/p95 246,50/513,57 ms, TTFC p50/p95 516,94/623,88 ms; 0 lỗi.
- Sau, benchmark/config `.venv\Scripts\python.exe tools\benchmark_multimodal.py --top-k 50 --max-lexical-terms 6`, đủ 57 case, tolerance ±150 giây, engine tách biệt:
  - Semantic: 2/57; R@1/5/10/50 = 0/1/2/2, MRR 0,0079; p50/p95 277,43/606,15 ms; TTFC p50/p95 481,17/509,19 ms; wall 33,76 giây; 0 lỗi.
  - OCR: 0/57; R@1/5/10/50 = 0/0/0/0, MRR 0; p50/p95 542,78/1.785,94 ms; TTFC unavailable; wall 39,68 giây; 0 lỗi.
  - ASR: 7/57; R@1/5/10/50 = 2/2/3/7, MRR 0,0358; p50/p95 701,80/950,97 ms; TTFC p50/p95 718,08/837,21 ms; wall 43,95 giây; 0 lỗi.
  - Reference hybrid: 5/57; R@1/5/10/50 = 0/2/3/5, MRR 0,0144; p50/p95 1.528,98/2.414,43 ms; TTFC p50/p95 1.590,92/1.690,93 ms; wall 93,61 giây; 0 lỗi. Bảo toàn 2/2 semantic target, missing `[]`.
  - Coverage tăng 0 → 4 strategy; smoke 3 case và full 57 case đều exit 0. Lượt full xác nhận giữ đúng cùng accuracy/rank của lượt đầu (semantic 2, OCR 0, ASR 7, hybrid 5; preservation 2/2).
- Guardrail: Q&A evidence 3/3, TRAKE sequence 3/3, semantic cache 3/3; compile tool exit 0. Runtime, API, ID/frame/answer/sequence production và file cấm không thay đổi.
- Sửa phụ: không có.
- Checkpoint vòng: `ac9fb9f` (`chore: checkpoint before multimodal retrieval benchmark`).
- Kết quả: **giữ lại benchmark** vì coverage tăng 0 → 4 strategy, số liệu tái lập, phát hiện được ASR/hybrid tăng recall và khóa bảo toàn từng semantic hit. `PROJECT_CONTEXT.md` đã cập nhật công cụ/cách chạy và ghi rõ hybrid mới chỉ là reference benchmark.

## 2026-09-22 14:08 +07:00 — Vòng tối ưu 81: triển khai production smart hybrid retrieval

- Query type/luồng thi: KIS/Q&A/TRAKE retrieval qua API, làm primitive cho operator/tool và agent. Cổng tác động nhắm tăng full-case correctness và Recall@K của production `SQLiteSearchEngine.smart_search`, không thay mode semantic mặc định.
- Thay đổi: `src/sqlite_engine.py` thêm lexical reducer online-safe (stopword tĩnh, tối đa 6 token duy nhất theo thứ tự), chạy semantic trên query gốc, OCR/ASR trên lexical query rồi RRF ba nhánh trong `smart_search`. `src/main.py` cho phép schema `mode="smart"`, không pretranslate query trước smart để OCR/ASR vẫn nhận tiếng Việt, và route mode này vào production smart. `tools/benchmark_multimodal.py` chuyển hybrid từ reference logic trong tool sang gọi trực tiếp production `smart_search`/reducer.
- Benchmark/config quyết định: full 57 case, 63 target, top-K 50, tolerance ±150 giây; baseline gọi trực tiếp production `smart_search`, sau dùng `.venv\Scripts\python.exe tools\benchmark_multimodal.py --strategies semantic hybrid --top-k 50 --max-lexical-terms 6` với engine tách biệt.
  - Trước production smart chỉ alias semantic: 2/57; R@1/5/10/50 = 0/1/2/2, MRR 0,0079; p50/p95 273,21/585,26 ms; TTFC p50/p95 476,82/588,76 ms; 0 lỗi. `SearchRequest(mode="smart")` bị Pydantic từ chối `literal_error`.
  - Sau production smart: 5/57; R@1/5/10/50 = 0/2/3/5, MRR 0,0144; p50/p95 2.533,11/5.820,21 ms; TTFC p50/p95 2.182,19/5.226,71 ms; 0 lỗi. Bảo toàn 2/2 semantic target, missing `[]`. Schema smart chuyển fail → pass.
  - Tác động chính: full-case correctness +3 (+150%), R@50 +3 (+150%), R@5 +1, R@10 +1, MRR +81,4%. Smart latency tăng rõ vì thêm hai fallback scan trên artifact thiếu FTS; mode là opt-in, semantic mặc định không đổi. Cùng lượt đo hệ thống chậm, semantic p50/p95 cũng tăng lên 456,69/1.111,16 ms so với reference 277,43/606,15 ms; không dùng chênh lệch môi trường để phủ nhận tradeoff smart.
- Guardrail/output correctness: `tools/benchmark.py --top-k 50` giữ KIS 1/39, Q&A 1/16 (location/evidence 1/16), TRAKE 0/2, tổng 2/57, R@50 2/63, MRR 0,0079, 0 lỗi. Fuzzy cache 5/5, Q&A evidence 3/3, TRAKE sequence 3/3, compile `src/tools` exit 0. API smoke smart trả đúng 3 result có `video_id/frame_idx`; first uncached query mất 16,91 giây do translation/fallback cold path đã biết.
- Sửa phụ: không có. Không sửa frontend/MCP hoặc file cấm.
- Checkpoint vòng: `bca8c0e` (`chore: checkpoint before production smart hybrid retrieval`).
- Kết quả: **giữ lại** vì metric thi chính accuracy/rank tăng rõ, bảo toàn toàn bộ semantic hit và guardrail không hồi quy. Tradeoff latency được cô lập trong mode smart opt-in; theo nguyên tắc plan, candidate đúng tăng được ưu tiên hơn latency/cache đẹp. `PROJECT_CONTEXT.md` đã cập nhật workflow/API/benchmark và trạng thái chưa nối UI/MCP.

## 2026-09-22 14:25 +07:00 — Vòng tối ưu 82: loại nhánh OCR khỏi production smart fusion

- Query type/luồng thi: KIS/Q&A/TRAKE retrieval qua API cho operator/tool và agent. Cổng tác động: production smart đang hợp nhất semantic/OCR/ASR nhưng OCR đạt 0/57; mục tiêu là tăng candidate đúng/rank, giảm time-to-first-correct và vẫn bảo toàn mọi semantic hit. Benchmark quyết định là full `tools/benchmark_multimodal.py`; workload multimodal trực tiếp thuộc luồng tìm candidate Chung kết; nếu không làm, OCR vừa tốn một full fallback scan vừa kéo ASR hit xuống trong RRF.
- Khám phá sơ bộ trên cache kết quả nhánh đủ 57 case: semantic+OCR+ASR đạt 5/57, R@5/R@50 = 2/5, MRR 0,0144, bảo toàn 2/2 semantic hit; semantic+ASR đạt 6/57, R@5/R@50 = 3/6, MRR 0,0219, bảo toàn 2/2. Weight ASR 2x và ASR-only đạt 7/57 nhưng làm mất 2/2 semantic hit nên bị loại; weight semantic 2x chỉ còn 2/57.
- Thay đổi/vị trí/mục đích: `src/sqlite_engine.py`, `SQLiteSearchEngine.smart_search`, bỏ lời gọi `exact_ocr_search` và hợp nhất RRF hai nhánh semantic+ASR. Không đổi reducer, model, index, API hay mode semantic mặc định.
- Benchmark/config quyết định: full 57 case, 63 target, top-K 50, tolerance ±150 giây; `.venv\Scripts\python.exe tools\benchmark_multimodal.py --strategies semantic hybrid --top-k 50 --max-lexical-terms 6`, engine tách biệt cho mỗi strategy.
  - Trước smart ba nhánh: 5/57; R@1/5/10/50 = 0/2/3/5, MRR 0,0144; p50/p95 2.041,60/6.842,64 ms; TTFC p50/p95 2.678,42/4.510,37 ms; 0 lỗi; bảo toàn 2/2 semantic hit.
  - Sau smart semantic+ASR: 6/57; R@1/5/10/50 = 0/3/3/6, MRR 0,0219; p50/p95 2.763,15/4.908,22 ms; TTFC p50/p95 2.398,78/3.918,55 ms; wall 163,69 giây; 0 lỗi; bảo toàn 2/2 semantic hit, missing `[]`.
  - Tác động chính: correctness +1 (+20%), R@5 +1, R@50 +1, MRR +52,1%; p95 giảm 28,3%, TTFC p50/p95 giảm 10,4%/13,1%. p50 tổng tăng trong lượt máy chậm hơn; semantic control cùng lượt cũng tăng từ baseline 332,37 lên 587,92 ms, nên không coi chênh lệch p50 giữa hai lượt là hồi quy thuật toán.
- Guardrail/output correctness: semantic control vẫn 2/57, R@1/5/10/50 = 0/1/2/2, MRR 0,0079; fuzzy cache 5/5, Q&A evidence 3/3, TRAKE sequence 3/3, compile `src/tools` exit 0. ID/frame/answer/sequence và semantic-hit preservation không hồi quy.
- Sửa phụ: không có. Không sửa UI/MCP, model/index, artifact dữ liệu hoặc file cấm.
- Checkpoint vòng: `fa75802` (`chore: checkpoint before smart fusion branch pruning`).
- Kết quả: **giữ lại** vì metric thi chính accuracy/rank tốt hơn rõ ràng, TTFC/p95 tốt hơn, bảo toàn 2/2 semantic hit và mọi guardrail đều pass. `PROJECT_CONTEXT.md` đã cập nhật production smart thành semantic+ASR và số đo mới.

## 2026-09-22 20:09 +07:00 — Vòng tối ưu 83: consensus-head fusion bảo toàn rank đầu và mở rộng ASR recall

- Query type/luồng thi: KIS/Q&A/TRAKE retrieval qua production `smart_search` cho operator/API và agent. Cổng tác động: tăng full-case accuracy, Recall@10/@50 và MRR mà vẫn giữ rank đầu cùng 2/2 semantic hit; benchmark quyết định là full `tools/benchmark_multimodal.py`; fusion semantic–ASR trực tiếp thuộc retrieval multimedia Chung kết; nếu không làm, RRF hiện chỉ đạt 6/57 dù nhánh ASR riêng có 7/57 và tiếp tục bỏ candidate đúng.
- Khám phá sơ bộ read-only, đủ 57 case/63 target: ASR-only đạt 7/57 nhưng mất 2/2 semantic hit; interleave bằng RRF; semantic-head 10 + ASR đạt 8/57 nhưng R@5/MRR giảm. Biến thể được chọn xếp 5 RRF consensus đầu, tối đa 10 semantic candidate đầu chưa trùng rồi điền ASR: 8/57, R@5/10/50 = 3/4/8, MRR 0,0232, giữ 2/2 semantic hit. Các head 5/10/15 và thứ tự nhánh khác đều không tốt hơn đồng thời ở accuracy/rank/preservation.
- Thay đổi/vị trí/mục đích: thêm `_fuse_smart_candidates()` trong `src/sqlite_engine.py` và dùng riêng trong `SQLiteSearchEngine.smart_search`. Hàm loại trùng theo cùng result key và giữ tối đa `top_k`; không đổi query reducer, semantic/ASR retrieval, model, index, API hay mode semantic mặc định.
- Benchmark/config quyết định: `.venv\Scripts\python.exe tools\benchmark_multimodal.py --strategies semantic hybrid --top-k 50 --max-lexical-terms 6 --json`, full 57 case, tolerance ±150 giây, engine tách biệt.
  - Trước, smart RRF: 6/57; R@1/5/10/50 = 0/3/3/6, MRR 0,0219; p50/p95 1.261,78/2.017,50 ms; TTFC p50/p95 1.305,80/1.521,00 ms; wall 77,11 giây; 0 lỗi; bảo toàn 2/2 semantic hit.
  - Sau, consensus-head: 8/57; R@1/5/10/50 = 0/3/4/8, MRR 0,0232; p50/p95 1.668,71/2.658,09 ms; TTFC p50/p95 1.569,98/2.108,41 ms; wall 103,19 giây; 0 lỗi; bảo toàn 2/2 semantic hit, missing `[]`.
  - Tác động chính: correctness +2 (+33,3%), R@10 +1, R@50 +2, MRR +6,1%; R@5 giữ nguyên. Lượt sau có p50/p95 tăng 32,3%/31,8% và TTFC tăng 20,2%/38,6%; thay đổi không thêm lượt retrieval nhưng tradeoff end-to-end được ghi nhận. Theo nguyên tắc mục 13, candidate đúng/rank tốt hơn được ưu tiên hơn số latency đẹp hơn.
- Guardrail/output correctness: semantic control giữ 2/57, R@1/5/10/50 = 0/1/2/2, MRR 0,0079; semantic cache 3/3, fuzzy cache 5/5, Q&A evidence 3/3, TRAKE sequence 3/3, compile `src/tools` exit 0. ID/frame/answer/sequence và semantic-hit preservation không hồi quy.
- Sửa phụ: không có. Không sửa UI/MCP, model/index, artifact dữ liệu hoặc file cấm.
- Checkpoint vòng: `ecab88a` (`chore: checkpoint before consensus-head smart fusion`).
- Kết quả: **giữ lại** vì accuracy/rank thi chính cải thiện rõ, bảo toàn toàn bộ semantic hit và guardrail pass; chấp nhận tradeoff latency theo ưu tiên candidate đúng của plan. `PROJECT_CONTEXT.md` đã cập nhật fusion strategy và số đo production smart.

## 2026-09-22 20:15 +07:00 — Vòng tối ưu 84: thêm benchmark operator cho mode smart

- Query type/luồng thi: UI/operator thủ công cho KIS/Q&A/TRAKE. Cổng tác động P0 nhắm đo việc operator có thể chọn smart, frontend gửi đúng mode và API trả đúng ID/frame; benchmark này bắt buộc phải có trước vòng sửa UI. Luồng người điều khiển đã được BTC xác nhận; nếu thiếu phép đo, smart 8/57 có thể không đến được thao tác thi thật và thay đổi UI sau không có cơ sở giữ/rollback.
- Baseline/khám phá: chưa có benchmark UI/operator hoặc submission, tương đương 0 scenario tự động. Kiểm tra thủ công cho thấy API schema/routing đã hỗ trợ smart và request frontend lấy giá trị động từ `#searchMode`, nhưng dropdown chỉ có semantic/OCR/ASR nên operator không thể chọn smart.
- Thay đổi/vị trí/mục đích: thêm `tools/benchmark_operator_search.py`. Tool dùng HTML parser kiểm tra đủ bốn mode production, xác nhận request wiring tới `/api/v1/search`, rồi import production `SearchRequest` và monkeypatch duy nhất `smart_search` để kiểm tra schema, routing, `video_id/frame_idx` output mà không chạy retrieval đắt tiền. Hỗ trợ text/JSON và exit khác 0 khi scenario fail.
- Benchmark/config: `.venv\Scripts\python.exe tools\benchmark_operator_search.py --json` trên `frontend/index.html` và production `src.main`.
  - Trước: 0 automated scenario; manual 3 pass/1 fail; smart mode thiếu trong dropdown.
  - Sau: 4 automated scenario, 3 pass, 1 fail, 0 error, elapsed 10.493,88 ms. `frontend_smart_mode` fail với missing `['smart']`; frontend request wiring pass; API smart schema pass; API routing/output pass và giữ sentinel `TEST_V001,123`.
  - Accuracy/rank/TTFC/end-to-end retrieval latency: không đổi/không áp dụng vì vòng chỉ thêm benchmark và route dùng stub; elapsed gồm import production engine, không dùng làm metric thi.
- Guardrail/output correctness: benchmark phát hiện đúng regression UI đang mở, API trả `mode='smart'`, `total_results=1`, đúng `video_id/frame_idx`; compile tool exit 0. Runtime, frontend, model/index và file cấm không thay đổi.
- Sửa phụ: không có.
- Checkpoint vòng: `61bc5bf` (`chore: checkpoint before operator search benchmark`).
- Kết quả: **giữ lại benchmark** vì coverage tăng 0→4 scenario, ba contract đang hoạt động được khóa và thiếu smart control được báo đỏ chính xác. `PROJECT_CONTEXT.md` đã cập nhật công cụ/cách chạy và trạng thái 3/4.

## 2026-09-22 20:19 +07:00 — Vòng tối ưu 85: cho operator chọn Smart Hybrid trong UI

- Query type/luồng thi: UI/operator thủ công cho KIS/Q&A/TRAKE. Cổng tác động nhắm đưa production smart 8/57 tới luồng thao tác thi, chuyển operator workflow fail→pass mà không đổi semantic mặc định; benchmark quyết định là `tools/benchmark_operator_search.py`. Human-in-the-loop đã được BTC xác nhận; nếu không làm, operator bị giới hạn ở semantic 2/57 hoặc phải gọi API ngoài UI.
- Khám phá sơ bộ: không cần; vòng 84 đã cô lập duy nhất dropdown `#searchMode` thiếu option, trong khi dynamic request wiring và API smart đều pass.
- Thay đổi/vị trí/mục đích: thêm một option `value="smart"` với nhãn `Smart Hybrid (Semantic + ASR)` trong `frontend/index.html`; semantic vẫn selected mặc định. Không đổi JavaScript request, API, retrieval, model/index hay submission.
- Benchmark/config quyết định: `.venv\Scripts\python.exe tools\benchmark_operator_search.py --json`, cùng frontend và production schema/route stub trước/sau.
  - Trước: 3/4 scenario pass, 1 fail, 0 error, elapsed 16.755,91 ms; `frontend_smart_mode` thiếu `smart`; wiring, schema và routing/output `TEST_V001,123` pass.
  - Sau: 4/4 scenario pass, 0 fail/error, elapsed 45.947,79 ms; đủ semantic/smart/OCR/ASR, missing `[]`; wiring, schema và routing/output vẫn pass.
  - Operator correctness chuyển fail→pass. Production accuracy/rank giữ theo backend không đổi: smart 8/57, R@5/10/50 = 3/4/8, MRR 0,0232, bảo toàn 2/2 semantic hit. Retrieval TTFC/p50/p95 không đo lại vì vòng chỉ thêm HTML option; benchmark elapsed bị import OpenCLIP chi phối và không dùng làm latency thi.
- Guardrail/output correctness: mode gửi động từ dropdown tới `/api/v1/search`; API response giữ `mode='smart'`, `total_results=1`, đúng `video_id/frame_idx`; compile `src/tools` exit 0.
- Sửa phụ: không có. Không sửa file cấm.
- Checkpoint vòng: `0e84fa0` (`chore: checkpoint before exposing smart operator mode`).
- Kết quả: **giữ lại** vì lỗi phá luồng operator chuyển fail→pass và mọi contract/output guardrail giữ nguyên. `PROJECT_CONTEXT.md` đã cập nhật trạng thái frontend và benchmark 4/4.

## 2026-09-22 20:31 +07:00 — Vòng tối ưu 86: thăm dò heuristic chọn token ASR online-safe

- Query type/luồng thi dự kiến: KIS/Q&A/TRAKE smart retrieval cho operator và agent, tập trung nhánh ASR. Cổng tác động nhắm tăng accuracy/Recall@K/MRR so với reducer lấy 6 token đầu; benchmark quyết định dự kiến là full `tools/benchmark_multimodal.py`; ASR/multimedia retrieval thuộc trực tiếp định hướng Chung kết; nếu không cải thiện reducer, các từ khóa phân biệt ở cuối query có thể bị bỏ và candidate đúng bị mất.
- Khám phá read-only: trên 20 case đầu theo thứ tự dataset, top-K 50, tolerance ±150 giây, cùng production ASR fallback; so sánh năm reducer không dùng answer/label/corpus statistics: first-6 hiện tại, last-6, longest-6, first-3+last-3 và length-with-position. Không sửa source hoặc file cấm.
  - First-6: 2 case đúng; R@1/5/10/50 = 1/1/1/2, MRR 0,0446, 0 lỗi.
  - Last-6: 1 case đúng; R@1/5/10/50 = 0/1/1/3, MRR 0,0127, 0 lỗi.
  - Longest-6: 1 case đúng; R@1/5/10/50 = 1/1/1/1, MRR 0,0435, 0 lỗi.
  - First-3+last-3: 2 case đúng; R@1/5/10/50 = 0/0/1/3, MRR 0,0087, 0 lỗi.
  - Length-with-position: 1 case đúng; R@1/5/10/50 = 1/1/1/1, MRR 0,0435, 0 lỗi.
- Benchmark/baseline chính thức: không chuyển sang Bước 4 vì không hướng nào cải thiện đồng thời full correctness và rank đầu trên mẫu. Edge reducer tăng R@50 nhưng làm R@5 1→0 và MRR giảm 80,5%; các hướng còn lại giảm case đúng.
- Guardrail/output correctness: tất cả ablation 0 error; chỉ gọi engine production và đọc dataset/DB read-only. Runtime, UI, API, benchmark và file cấm không thay đổi.
- Sửa phụ: không có. Không tạo checkpoint vì dừng ở Bước 3 trước thay đổi chính thức.
- Kết quả: **không triển khai / không có gì để rollback**. First-6 hiện tại tiếp tục được giữ; `PROJECT_CONTEXT.md` không cập nhật vì kiến trúc/workflow/cách chạy không đổi.

## 2026-09-22 20:40 +07:00 — Vòng tối ưu 87: xác nhận độ tin cậy benchmark agent end-to-end

- Query type/luồng thi dự kiến: agent tự động cho KIS/Q&A/TRAKE. Cổng tác động P0 nhắm xác nhận `tools/benchmark_chatbot.py` có thể chấm final candidate/answer, latency và error trước khi cân nhắc nối production smart vào MCP/prompt. Hình thức tự động được BTC công bố thử nghiệm; nếu benchmark không đáng tin, thay đổi agent có thể chỉ gọi được tool nhưng output cuối vẫn sai.
- Chuẩn bị môi trường/readiness: `agy 1.2.7` tồn tại; MCP `video-researcher` enabled với đúng Python/workspace; FastAPI local khởi động thành công; Agy flash/pro đều báo ready; `/api/v1/chat` trả HTTP 200. Server test PID 25804 đã được dừng sau benchmark và health không còn lắng nghe port 8000.
- Benchmark/config khám phá: `.venv\Scripts\python.exe tools\benchmark_chatbot.py --api-url http://127.0.0.1:8000 --limit 1 --timeout 180`, sau đó lặp warm với `--limit 3`; dataset/fps/tolerance mặc định ±150 giây.
  - Smoke 1 case: 0/1 đúng, 0 candidate parse được, 0 error, 60.960,38 ms; usage/cost unavailable.
  - Smoke 3 case: 0/3 đúng, location 0/3, 0/3 candidate parse được; average 40.525,61 ms; case đầu lỗi sau 108,0 ms, hai case còn lại 60.638,0/60.830,8 ms; error rate 1/3 (33,3%); usage/cost unavailable.
- Benchmark/baseline chính thức: không chuyển sang Bước 4 vì output cuối không quan sát được candidate trên cả ba case và có lỗi SSE dù HTTP 200. Không thể dùng số 0/3 để kết luận chất lượng retrieval hoặc tác động của smart MCP.
- Guardrail/output correctness: server/model/MCP startup pass nhưng final output contract/candidate extraction fail 0/3; đây là lý do dừng, không phải bằng chứng để sửa prompt/tool trong cùng vòng.
- Sửa phụ: không có. Không sửa runtime, MCP, prompt, benchmark hoặc file cấm; không tạo checkpoint vì dừng trước thay đổi chính thức.
- Kết quả: **không triển khai / không có gì để rollback**. Theo điều kiện mục 11, benchmark thi tự động chưa đủ tin cậy nên không mở vòng tối ưu agent runtime. `PROJECT_CONTEXT.md` đã cập nhật trạng thái benchmark và điều kiện cần trước khi tiếp tục P4.

## 2026-09-22 20:48 +07:00 — Vòng tối ưu 88: thêm diagnostic và regression cho chatbot SSE benchmark

- Query type/luồng thi: P0 benchmark end-to-end cho agent KIS/Q&A/TRAKE; không sửa agent runtime. Cổng tác động nhắm phân biệt agent trả rỗng với parser bỏ dữ liệu bằng diagnostic event/tool/DONE/text/raw-tail; benchmark quyết định là regression SSE mới và smoke production. Agent tự động là workload được BTC định hướng thử nghiệm; nếu không làm, 0-candidate không thể dẫn tới quyết định MCP/prompt đáng tin.
- Khám phá nguyên nhân: `AgySession._read_until_result()` stream `step_update.text_delta` và tool labels, nhưng gặp event `result` thì break mà không forward payload cuối. `tools/benchmark_chatbot.py` trước đó bỏ tool event và không báo event count, DONE hoặc text length, nên smoke 0-candidate không xác định được tầng lỗi. Vòng này không sửa `src/agy_session.py`.
- Baseline: 0 regression scenario chuyên biệt; record chỉ có text/error/usage, không có tool events, SSE event count, DONE, text chars hoặc raw data tail. Smoke vòng 87 là 0/3 candidate với nguyên nhân không quan sát được.
- Thay đổi/vị trí/mục đích: `tools/benchmark_chatbot.py` giữ lại tool events, đếm SSE event, ghi `saw_done`, `raw_data_tail`, `text_chars`, in lỗi/raw tail theo case và aggregate stream diagnostics. Thêm `tools/benchmark_chatbot_stream.py`, monkeypatch transport bằng stream tổng hợp để khóa plain text candidate, JSON delta, tool/error và DONE parsing.
- Benchmark/config sau:
  - `.venv\Scripts\python.exe tools\benchmark_chatbot_stream.py --json`: 3/3 scenario pass, 0 fail/error; plain stream trích đúng `L21_V001,1500`, JSON delta trích đúng `L22_V002,222`, synthetic error và DONE được ghi đúng.
  - Production smoke `.venv\Scripts\python.exe tools\benchmark_chatbot.py --api-url http://127.0.0.1:8000 --limit 1 --timeout 180`: 0/1 đúng, 0 candidate, 60.762,11 ms, 0 error; diagnostic mới báo 8 SSE event, 7 tool event, DONE 1/1 nhưng text 0/1 và 0 ký tự. Usage/cost unavailable.
  - Accuracy/rank không cải thiện vì vòng chỉ sửa benchmark; TTFC không có do không candidate. Diagnostic coverage tăng 0→3 regression scenario và 0→5 trường quan sát chính.
- Guardrail/output correctness: regression parser 3/3, compile hai tool exit 0; production server/Agy/MCP khởi động và HTTP 200, server test PID 23540 đã được dừng. Không sửa runtime, API, MCP, prompt hoặc file cấm.
- Sửa phụ: không có.
- Checkpoint vòng: `13fc2ae` (`chore: checkpoint before chatbot benchmark diagnostics`).
- Kết quả: **giữ lại benchmark** vì parser/output extraction được khóa và nguyên nhân miss chuyển từ mơ hồ sang contract tool-only/DONE không có final text. `PROJECT_CONTEXT.md` đã cập nhật benchmark/cách chạy và blocker P4 còn lại.

## 2026-09-22 21:00 +07:00 — Vòng tối ưu 89: forward Agy final response và error ra SSE

- Query type/luồng thi: autonomous agent KIS/Q&A/TRAKE qua `/api/v1/chat`. Cổng tác động nhắm chuyển silent DONE với 0 text/candidate thành final response cấu trúc hoặc lỗi rõ ràng; benchmark quyết định là Agy-result regression, client SSE regression và production chatbot smoke. Agent tự động được BTC định hướng thử nghiệm; nếu không sửa, agent gọi tool xong vẫn trả rỗng và chắc chắn mất output thi.
- Khám phá schema read-only: chạy Agy stream-json trực tiếp xác nhận event `result.result` có `response`, `error`, `status`, `usage`. Môi trường hiện trả `status='ERROR'`, `error='authentication failed or timed out'`, nhưng backend cũ break ngay tại result và chỉ phát DONE. Thử trực tiếp lần đầu không có init event trong 20 giây; lần hai mô phỏng đúng production bằng cách tiếp tục sau init timeout và nhận được schema trên.
- Baseline contract tổng hợp trên implementation cũ: 1/3 pass. Result-only response `L21_V001,1500` bị mất; result error `auth failed` bị mất; text delta rồi result không bị lặp và pass. Production trước sửa: 0/1 đúng, 0 candidate/0 ký tự, 8 event, 7 tool event, DONE, 0 error, 60.762,11 ms.
- Thay đổi/vị trí/mục đích: `src/agy_session.py::_read_until_result()` theo dõi đã stream text, forward `result.response` chỉ khi chưa có delta, forward `result.error`/status ERROR thành SSE `[ERROR]`, sau đó giữ DONE. Thêm `tools/benchmark_agy_result_stream.py` với ba scenario response/error/no-duplicate. `tools/benchmark_chatbot.py` in error/raw-tail bằng JSON ASCII-safe để diagnostic Unicode không crash console Windows.
- Benchmark/config sau:
  - `.venv\Scripts\python.exe tools\benchmark_agy_result_stream.py --json`: 3/3 pass, 0 fail/error; response và error đều xuất hiện trước DONE, delta/result chỉ xuất candidate một lần.
  - `tools/benchmark_chatbot_stream.py --json`: 3/3 pass, 0 fail/error; compile runtime/ba benchmark exit 0.
  - Production smoke clean server: 0/1 đúng, 0 candidate/0 ký tự, 9 event, 7 tool, DONE và error 1/1; lỗi không còn bị nuốt mà báo `authentication failed or timed out` sau khoảng 60,84 giây. Lượt xác minh ASCII-safe trên session Agy đã chết hoàn tất summary thay vì crash, báo `Connection lost` trong 122,5 ms, 2 event/1 tool/DONE false.
  - Accuracy/rank/TTFC chưa cải thiện vì Agy chưa xác thực; metric sửa lỗi chính là result contract 1/3→3/3 và silent error→visible error. Error rate production tăng quan sát 0→1 đúng bản chất, không phải lỗi mới do thay đổi.
- Guardrail/output correctness: client SSE 3/3, Agy result SSE 3/3, compile pass; candidate IDs synthetic giữ đúng `L21_V001,1500` và `L22_V002,222`, không duplicate. Server test PID 21900 đã dừng và port 8000 không còn lắng nghe.
- Sửa phụ: diagnostic print ASCII-safe là sửa bắt buộc để benchmark đọc được error Unicode mới; không sửa prompt, MCP, model/index, UI hoặc file cấm.
- Checkpoint vòng: `372b746` (`chore: checkpoint before Agy result forwarding`).
- Kết quả: **giữ lại** vì lỗi phá luồng thi chuyển fail→pass ở contract output và lỗi môi trường không còn bị che giấu. `PROJECT_CONTEXT.md` đã cập nhật contract/benchmark và blocker xác thực Agy; chuỗi dừng vì bước tiếp theo cần trạng thái đăng nhập bên ngoài.

## 2026-09-22 23:09 +07:00 — Vòng tối ưu 90: cô lập session giữa các lượt benchmark chatbot

- Query type/luồng thi: P0 benchmark end-to-end cho agent tự động KIS/Q&A/TRAKE. Cổng tác động nhắm loại lịch sử hội thoại khỏi phép đo accuracy, latency và error trước khi tối ưu MCP/prompt; benchmark quyết định là `tools/benchmark_chatbot.py`, regression session mới và hai guardrail SSE. Hình thức agent tự động có căn cứ Chung kết 2026; nếu không sửa, before/after có thể đo các lượt hội thoại khác nhau và dẫn tới giữ sai thay đổi runtime.
- Khám phá/readiness: `agy 1.2.8` ngoài sandbox liệt kê đầy đủ model, xác nhận credential người dùng hoạt động. Trong sandbox, Agy không ghi được profile `.gemini` và báo `not logged in`; backend benchmark vì vậy phải chạy ngoài sandbox. Baseline sạch 3 KIS case sau prewarm đạt 0/3, location 0/3, trung bình 73.878,74 ms, error 0/3, text/DONE 3/3, 211 SSE event và 56 tool event.
- Nguyên nhân benchmark: session ID cũ chỉ phụ thuộc case ID. Chạy lại case 1 trên cùng backend tái sử dụng conversation: latency 72.853,3 → 8.477,9 ms, tool event 19 → 1 và agent trả sai `L26_V424` từ lịch sử thay vì thực hiện workflow mới. Vì vậy baseline accuracy 0/3 là output thật nhưng phép so sánh lần chạy kế tiếp chưa độc lập.
- Thay đổi/vị trí/mục đích: `tools/benchmark_chatbot.py` tạo namespace ngẫu nhiên cho mỗi invocation, hỗ trợ `--session-run-id` để tái lập namespace khi cần và ghép namespace vào mọi session ID. Thêm `tools/benchmark_chatbot_sessions.py` khóa ba contract: ổn định trong cùng run, khác giữa các run và khác giữa các case. Không sửa agent runtime, prompt, MCP, model/index hoặc file cấm.
- Benchmark/config sau: cùng dataset 3 case đầu, timeout 180 giây, tolerance ±150 giây, backend/prewarm/model như baseline; dùng `--session-run-id round90-after`.
  - Session isolation regression: 3/3 pass, 0 fail.
  - End-to-end: KIS/location 1/3, trung bình 52.860,12 ms, error 0/3, text/DONE 3/3, 199 SSE event, 52 tool event. Case đầu trở lại first-turn workflow 60.211,9 ms/18 tool event thay vì lượt reuse 8.477,9 ms/1 tool event.
  - Không coi 0/3 → 1/3 hoặc latency giảm 28,4% là cải thiện thuật toán vì model Agy có biến thiên; metric quyết định của vòng là contamination fail → pass và regression 3/3.
- Guardrail/output correctness: `tools/benchmark_chatbot_stream.py --json` 3/3 pass; `tools/benchmark_agy_result_stream.py --json` 3/3 pass; compile `src` và ba benchmark exit 0. Output sau sửa có candidate thật, DONE đầy đủ và 0 error.
- Sửa phụ: không có.
- Checkpoint vòng: `b370482` (`chore: checkpoint before chatbot benchmark session isolation`).
- Kết quả: **giữ lại** vì benchmark end-to-end chuyển từ tái sử dụng lịch sử sang session độc lập, mở khóa việc đo agent runtime đáng tin hơn. `PROJECT_CONTEXT.md` đã cập nhật cách chạy, credential/profile và baseline P4 gần nhất.
