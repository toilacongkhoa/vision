# Hệ thống tìm kiếm video — AI Challenge 2026

Ứng dụng FastAPI tìm keyframe bằng semantic, OCR, ASR hoặc ảnh mẫu; giao diện hỗ trợ kiểm chứng video, tạo đáp án KIS/Q&A/TRAKE và nộp qua DRES. Mỗi thành viên cài và chạy backend trên máy riêng tại `http://localhost:8000`.

## Cài đặt và chạy

Cần Python 3.12 x64. Trên Windows, cài dependencies trong PowerShell:

```powershell
git clone --branch codex/development https://github.com/toilacongkhoa/vision.git
cd vision
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Đặt dữ liệu ở mục dưới vào thư mục gốc, sau đó chạy:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& .\.venv\Scripts\python.exe tools\preflight.py
if ($LASTEXITCODE -ne 0) { throw "Preflight phát hiện lỗi bắt buộc; xem chẩn đoán phía trên." }
& .\.venv\Scripts\python.exe tools\run_server.py
```

`tools\run_server.py` và `tools\preflight.py` lấy cấu hình từ vị trí project, nên có thể gọi bằng đường dẫn đầy đủ khi PowerShell đang ở thư mục khác. Mặc định backend chỉ bind `127.0.0.1:8000`; frontend và MCP cùng theo `PORT` trong `.env`. Port mặc định 8000 đang được dùng thì dừng process cũ hoặc đổi `PORT`; khi đổi port, mở URL mới theo `PORT`. `/api/v1/health` báo trạng thái dịch vụ đang chạy, còn preflight kiểm tra file/model trước khi khởi động. Nếu gói tải xuống có `.env`, hãy giữ cấu hình riêng của máy và không chia sẻ credential.

Để dừng server, nhấn `Ctrl+C` trong cửa sổ đang chạy. Để restart, chạy lại `tools\run_server.py` bằng Python trong `.venv`; đừng mở thêm một bản server nếu port đang được sử dụng.

## Dữ liệu ngoài Git

Tải [gói dữ liệu trên Google Drive](https://drive.google.com/file/d/1CVWi82-NgVVe3UchQMu-6P3ESMIsrroM/view) rồi đặt các file sau cùng cấp với `README.md`:

| File | Vai trò |
|---|---|
| `video_index_v2.db` | Bắt buộc: chỉ mục frame và metadata. |
| `all_vectors.npy` | Bắt buộc: vector cho semantic và tìm kiếm ảnh. |
| `video_drive_metadata.json` | Tùy chọn: metadata để xem video; thiếu thì thông tin media bị giảm cấp. |
| `video_fps_map.json` | Tùy chọn: FPS cho chuyển đổi thời gian/frame; payload KIS/Q&A lấy PTS từ frame index. |
| `translation_cache.db` | Tùy chọn, có thể tạo lại; cache dịch. |
| `frame_map_supabase.json` | Không dùng trực tiếp trong web hiện tại. |
| `docs/answerAndQuestion.jsonl` | Bộ nhãn local cho benchmark KIS/Q&A/TRAKE; không đưa vào gói phát hành chung. Hiện chưa tách riêng Textual KIS và Video KIS. |
| `.env` | Cấu hình riêng từng máy; không đưa vào gói dữ liệu/manifest chung. Tạo từ `.env.example`. |

Gói Drive có thể yêu cầu quyền truy cập. Sau khi chuẩn bị gói phát hành, tạo manifest cạnh dữ liệu bằng `python tools/data_manifest.py create --root .`; người nhận chạy `python tools/data_manifest.py verify --root .` để kiểm tra kích thước và SHA-256. Manifest không chứa credential. Giữ kín `.env`; không commit dữ liệu hoặc credential. Model OpenCLIP mặc định là `ViT-B-32-quickgelu/openai` để khớp activation của checkpoint; giữ cùng tên model/pretrained với model đã dùng tạo vectors. Checkpoint phải được tải/cache trên từng máy trước khi chạy offline; preflight kiểm tra cache PyTorch và Hugging Face. Model dịch offline `models/opus-mt-vi-en-ct2/` là tùy chọn.

Nếu preflight báo thiếu DB/vector, kiểm tra đã giải nén đúng hai file bắt buộc vào thư mục chứa `README.md` hoặc đặt `DB_PATH`/`CONSOLIDATED_VECTORS_PATH` trong `.env`. Nếu OpenCLIP thiếu checkpoint, kết nối mạng rồi chạy `& .\.venv\Scripts\python.exe tools\warm_open_clip.py`, sau đó preflight lại; server runtime giữ chế độ offline. Nếu máy ít RAM, đặt `AGY_PREWARM_ON_STARTUP=false` trong `.env` để bỏ prewarm hai phiên Agy; phiên sẽ khởi động khi gửi chat đầu tiên. Nếu Agy chưa cài, tìm tay vẫn hoạt động; Assistant là tùy chọn. Ảnh ngoài Supabase/Drive cần mạng và cấu hình dịch vụ phù hợp; khi ảnh lỗi, dùng Video ID/Frame ID/PTS để tiếp tục xác minh.

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
