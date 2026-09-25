# Hệ thống tìm kiếm video — AI Challenge 2026

Ứng dụng FastAPI tìm keyframe bằng semantic, OCR, ASR hoặc ảnh mẫu; giao diện hỗ trợ kiểm chứng video, tạo đáp án KIS/Q&A/TRAKE và nộp qua DRES.

## Cài đặt và chạy

Cần Python 3.12. Trên Windows:

```powershell
git clone --branch codex/development https://github.com/toilacongkhoa/vision.git
cd vision
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Đặt dữ liệu ở mục dưới vào thư mục gốc, sau đó chạy:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& .\.venv\Scripts\python.exe -m src.main
```

Mở [http://localhost:8000](http://localhost:8000); kiểm tra server tại `/api/v1/health`. Nếu gói tải xuống đã có `.env`, kiểm tra cấu hình của nó trước khi chạy.

## Bảy file dữ liệu ngoài Git

Tải [gói dữ liệu trên Google Drive](https://drive.google.com/file/d/1CVWi82-NgVVe3UchQMu-6P3ESMIsrroM/view) rồi đặt các file sau cùng cấp với `README.md`:

| File | Vai trò |
|---|---|
| `video_index_v2.db` | Chỉ mục frame và metadata; cần để tìm kiếm. |
| `all_vectors.npy` | Vector ảnh; cần cho tìm kiếm semantic/ảnh. |
| `video_drive_metadata.json` | Metadata để xem video. |
| `video_fps_map.json` | FPS dùng khi đổi thời gian sang Frame ID. |
| `translation_cache.db` | Cache dịch; có thể tạo lại. |
| `frame_map_supabase.json` | Dữ liệu phụ; web hiện không đọc trực tiếp. |
| `.env` | Cấu hình server và tích hợp; có thể tạo từ `.env.example`. |

Gói Drive có thể yêu cầu quyền truy cập. Giữ kín `.env`; không commit dữ liệu hoặc credential. Model dịch offline `models/opus-mt-vi-en-ct2/` là tùy chọn.

## Sử dụng và nộp bài

1. Chọn dạng câu hỏi, tìm frame, xem frame lân cận/video và ghim ứng viên.
2. Dùng **Submission Builder** chọn đáp án; mở **Kiểm tra và nộp** để xem JSON DRES.
3. **Tải JSON** chỉ lưu cục bộ. **Gửi đáp án** mới POST tới DRES sau khi đăng nhập và chọn evaluation `ACTIVE`.

KIS/Q&A chỉ xuất được frame có trong index; Video ID hoặc Frame ID không hợp lệ trả 404. Lịch sử nộp hiển thị kết quả đúng/sai màu xanh/đỏ; HTTP 412 báo trùng kết quả hoặc hết giờ, 401 báo session hết hạn, 404 báo sai Evaluation ID. UI cảnh báo payload đã gửi nhưng vẫn cho gửi lại. Xem [checklist DRES](docs/DRES_OPERATOR_CHECKLIST.md).

## Kiểm tra local

```powershell
& .\.venv\Scripts\python.exe -m unittest tools.dres_contract_checks
& .\.venv\Scripts\python.exe tools\benchmark_dres_submission.py
& .\.venv\Scripts\python.exe tools\benchmark_dres_operator.py
```

Các lệnh này dùng mock/local, không POST lên DRES thật. AI Assistant qua Antigravity CLI và MCP là tùy chọn; chi tiết cấu hình, vận hành và kế hoạch kiểm thử nằm trong [PROJECT_CONTEXT](docs/PROJECT_CONTEXT.md), [plan](docs/plan.md) và [TEST_PLAN](docs/TEST_PLAN.md).
