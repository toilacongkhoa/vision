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
