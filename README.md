# Hệ thống tìm kiếm video — AI Challenge 2026

Ứng dụng web giúp tìm keyframe, kiểm chứng vị trí trong video và chuẩn bị đáp án cho **Textual KIS, Video KIS, Q&A, TRAKE**. Backend FastAPI tìm trên SQLite và vector OpenCLIP; giao diện nằm trong `frontend/index.html`. Có thể xuất JSON DRES để kiểm tra hoặc đăng nhập và gửi từ hộp review.

## 1. Cài đặt nhanh trên Windows

Máy cần Python 3.12 (môi trường hiện tại dùng 3.12.5), Git và đủ dung lượng cho dữ liệu, model cùng thư viện Python. Cần Internet để cài dependency, tải ảnh từ nguồn ngoài và dùng các dịch vụ tùy chọn. AI Assistant cần thêm Antigravity CLI (`agy`).

```powershell
git clone --branch codex/development https://github.com/toilacongkhoa/vision.git
cd vision
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip check
```

Sau đó tải gói dữ liệu ở mục 2, giải nén vào thư mục gốc của dự án và kiểm tra `.env`. Nếu gói không có `.env`, tạo từ mẫu:

```powershell
Copy-Item .env.example .env
```

Chạy backend:

```powershell
& .\.venv\Scripts\python.exe -m src.main
```

Mở [http://localhost:8000](http://localhost:8000). Kiểm tra sơ bộ:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

Health chỉ xác nhận trạng thái cơ bản và sự hiện diện của DB/vector; nên thử một truy vấn tìm kiếm và mở một frame trước khi thi. Nếu cổng 8000 đã có server, kiểm tra server đó và khởi động lại khi code hoặc `.env` thay đổi, thay vì chạy thêm tiến trình thứ hai.

## 2. Bảy file không có trong Git

Tải [video_data_bundle_with_env.zip từ Google Drive](https://drive.google.com/file/d/1CVWi82-NgVVe3UchQMu-6P3ESMIsrroM/view), giải nén và đặt **bảy file** sau trực tiếp trong thư mục `vision/` (cùng cấp với `README.md`). Liên kết Drive có thể yêu cầu quyền truy cập do người chia sẻ cấp. Sau khi giải nén, đối chiếu tên file trước khi chạy.

| File | Công dụng | Mức độ cần thiết |
|---|---|---|
| `video_index_v2.db` | Chỉ mục keyframe, metadata, OCR/ASR; backend đọc SQLite ở chế độ chỉ đọc. | Bắt buộc cho tìm kiếm. |
| `all_vectors.npy` | Vector ảnh OpenCLIP cho semantic, tìm bằng ảnh và tìm frame tương tự. | Bắt buộc cho các chế độ tìm bằng vector. |
| `video_drive_metadata.json` | Ánh xạ Video ID tới thông tin video/Google Drive cho API video và preview. | Cần cho luồng xem video đầy đủ. |
| `video_fps_map.json` | FPS theo video cho API đổi thời gian sang Frame ID; nếu thiếu, API dùng FPS được truyền vào hoặc mặc định 25. | Nên có để đổi thời gian đúng. |
| `translation_cache.db` | Cache SQLite cho bản dịch truy vấn Việt → Anh; ứng dụng tự tạo lại nếu thiếu. | Tùy chọn, giúp truy vấn đã dịch chạy nhanh và ổn định hơn. |
| `frame_map_supabase.json` | Dữ liệu ánh xạ phục vụ việc tái lập bộ dữ liệu; mã runtime hiện tại không đọc trực tiếp file này. | Không cần cho luồng web hiện tại. |
| `.env` | Cấu hình server, đường dẫn và thông tin kết nối tùy chọn. | Cần kiểm tra hoặc tạo từ `.env.example`; DRES cần cấu hình phù hợp. |

`.env` có thể chứa thông tin đăng nhập: kiểm tra giá trị sau khi giải nén, không đưa file hoặc nội dung của nó lên Git/ảnh chụp màn hình. Các file dữ liệu trên bị `.gitignore` loại khỏi repository, nên clone Git riêng lẻ sẽ không có chúng. `DB_PATH` và `CONSOLIDATED_VECTORS_PATH` trong `.env` có thể trỏ DB/vector sang vị trí khác; metadata video, FPS và cache dịch mặc định được đọc ở thư mục gốc.

Thư mục `models/opus-mt-vi-en-ct2/` **không thuộc bảy file trên** và chỉ cần khi muốn dịch Việt → Anh cục bộ. Nếu không có model này, ứng dụng thử dịch trực tuyến; các câu đã dịch trước đó vẫn có thể lấy từ `translation_cache.db`. Nên khởi động và thử tìm kiếm trên chính máy thi trước khi dùng trong môi trường không có mạng.

## 3. Luồng sử dụng

1. Chọn dạng câu thi, ghi mô tả và các gợi ý. Đồng hồ trong UI là 4 phút cho Video KIS, 5 phút cho các dạng còn lại.
2. Tìm bằng `Smart` (semantic + ASR), `Semantic`, `OCR`, `ASR` hoặc ảnh mẫu. Có thể lọc Video ID ở tìm kiếm văn bản; xem frame lân cận, filmstrip, video và ghim ứng viên để kiểm chứng.
3. Trong **Submission Builder**, chọn một đáp án KIS/Q&A hoặc một video với chuỗi semantic keyframe tăng dần cho TRAKE. Kiểm tra Video ID, Frame ID, mốc thời gian và câu trả lời Q&A.
4. Mở **Kiểm tra và nộp** để xem bằng chứng cùng JSON DRES. **Tải JSON** chỉ lưu file cục bộ; **Gửi đáp án** mới POST tới DRES sau khi đăng nhập và chọn evaluation đang `ACTIVE`.

Video KIS phải được diễn tả bằng lời hoặc phác họa theo quy định cuộc thi; không thu lại clip truy vấn bằng thiết bị để nạp vào công cụ. Nháp câu hỏi và lịch sử nộp được giữ trong `localStorage` của trình duyệt; session DRES chỉ ở bộ nhớ trang và mất khi refresh.

## 4. DRES và trạng thái nộp

Backend tạo payload trong `src/dres_submission.py`, kiểm tra dữ liệu ở `POST /api/v1/submission/dres/export` rồi gửi qua `src/dres_api.py`/`src/dres_client.py` nếu operator bấm gửi. KIS/Q&A lấy PTS của **frame tồn tại trong index** để đổi sang mili giây; video/frame không tồn tại trả 404, không tự ước lượng thời gian bằng FPS. KIS dùng `mediaItemName` không có đuôi video và `start == end`; Q&A dùng chuỗi `QA-...`; TRAKE dùng `TR-...`.

Địa chỉ DRES cấu hình bằng `DRES_API_BASE_URL` (mặc định `https://eventretrieval.one`, yêu cầu HTTPS). Có thể nhập tài khoản trong hộp review hoặc đặt `DRES_USERNAME`/`DRES_PASSWORD` trong `.env` rồi bấm lấy session; cách lấy từ `.env` chỉ hoạt động trên ứng dụng cùng origin localhost. Luôn chọn đúng evaluation `ACTIVE` và xem JSON trước khi gửi.

Lịch sử nộp hiển thị `CORRECT` màu xanh, `WRONG` màu đỏ; HTTP 412 cảnh báo nộp trùng kết quả hoặc hết giờ, HTTP 401 yêu cầu đăng nhập lại, HTTP 404 báo sai Evaluation ID. HTTP 202 hoặc HTTP 200 chưa có verdict chỉ là **đã gửi, chưa có kết luận**. Nếu kết quả mạng/timeout không rõ, kiểm tra DRES trước khi thử lại. UI cảnh báo payload cùng query đã gửi nhưng **vẫn cho gửi lại**; mỗi lần gửi hợp lệ được chuyển tiếp tới DRES và có thể tính là một attempt mới.

Các kiểm thử hiện có dùng mock/local; chưa thay thế việc xác nhận endpoint, evaluation, `start == end` và response thực tế trong buổi tập huấn. Xem [checklist vận hành](docs/DRES_OPERATOR_CHECKLIST.md).

## 5. AI Assistant và MCP (tùy chọn)

AI Assistant gọi Antigravity CLI để phân tích truy vấn phức tạp, tìm ứng viên và xem ảnh kiểm chứng qua MCP `video-researcher`. Phần này nằm ở `src/agy_session.py` và `mcp_server.py`; không cần để dùng các form tìm kiếm trực tiếp.

Sau khi cài `agy`, đăng ký MCP bằng Python của môi trường ảo:

```powershell
$projectRoot = (Get-Location).Path
agy mcp add video-researcher "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\mcp_server.py"
agy mcp list
```

Kiểm tra `video-researcher` ở trạng thái enabled. Nếu thay `mcp_server.py`, đóng phiên Agy cũ và restart backend để phiên mới nhận code. `mcp_server.py` hiện gọi API tại `127.0.0.1:8000`; giao diện cũng dùng backend tại cổng 8000, nên chỉ đổi biến `PORT` là chưa đủ để chuyển toàn bộ hệ thống sang cổng khác.

## 6. Cấu trúc và cấu hình

| Thành phần | Vai trò |
|---|---|
| `frontend/index.html` | UI, workspace câu hỏi, tìm kiếm, Submission Builder và review DRES. |
| `src/main.py` | FastAPI: tìm kiếm, video/frame, chat SSE, export DRES và phục vụ UI. |
| `src/sqlite_engine.py` | SQLite, OpenCLIP/NumPy retrieval, OCR/ASR và các cache truy vấn. |
| `src/fast_translator.py` | Dịch truy vấn tiếng Việt với cache/model cục bộ hoặc dịch vụ trực tuyến. |
| `src/dres_*.py` | Tạo, kiểm tra và gửi payload DRES. |
| `src/agy_session.py`, `mcp_server.py` | AI Assistant và công cụ MCP kiểm chứng video. |
| `src/supabase_service.py` | API metadata Supabase tùy chọn khi có `SUPABASE_URL` và `SUPABASE_KEY`. |
| `tools/` | Benchmark và contract checks; không phải mã runtime. |

`.env.example` mô tả các biến cấu hình. `HOST`/`PORT` điều khiển backend; `DB_PATH`/`CONSOLIDATED_VECTORS_PATH` chỉ tới dữ liệu tìm kiếm; `DATA_ROOT` là gốc dữ liệu phụ; `AGY_PATH` dùng khi `agy` không ở trong `PATH`. Supabase là tùy chọn. Trang chủ và API hoạt động trên cùng server FastAPI; mở `http://localhost:8000/` thay vì mở file HTML trực tiếp.

## 7. Kiểm tra nhanh và xử lý lỗi

Các lệnh dưới đây kiểm tra local/mock và không gửi đáp án lên DRES thật:

```powershell
& .\.venv\Scripts\python.exe -m unittest tools.dres_contract_checks
& .\.venv\Scripts\python.exe tools\benchmark_dres_submission.py
& .\.venv\Scripts\python.exe tools\benchmark_dres_operator.py
```

- **Thiếu DB/vector:** kiểm tra đúng tên và vị trí `video_index_v2.db`/`all_vectors.npy`, hoặc đường dẫn `DB_PATH`/`CONSOLIDATED_VECTORS_PATH`. Health chưa bảo đảm truy vấn thực tế chạy được.
- **Không thấy ảnh/video:** kiểm tra `video_drive_metadata.json`, kết nối tới nguồn ảnh R2/Google Drive và Video ID đã chọn.
- **Xuất DRES trả 404:** Frame ID không nằm trong index của Video ID đó; chọn frame có trong kết quả tìm kiếm thay vì dựa vào FPS ước lượng.
- **Chatbot không thấy tool:** kiểm tra `agy mcp list`, Python của MCP và server ở cổng 8000; khởi động lại Agy/backend khi đổi cấu hình.
- **Dịch tiếng Việt chậm:** kiểm tra cache `translation_cache.db`, model tùy chọn hoặc kết nối dịch trực tuyến.

Các kiểm tra sâu hơn nằm trong các script `tools/benchmark_*.py`. Không dùng evaluation thi đang tính điểm để smoke test DRES.
