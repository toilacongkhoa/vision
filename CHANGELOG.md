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
