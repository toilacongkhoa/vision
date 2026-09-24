# AI Challenge TP.HCM 2026 – Hướng dẫn vòng Chung kết

> **Căn cứ:** `HD-ChungKet-2026.pdf` do người dùng cung cấp. Các mục 1–4 và 6 tóm lược nội dung tài liệu. Mục 5 là diễn giải kỹ thuật để áp dụng các quy định đó.
>
> **Phạm vi:** Các dạng truy vấn và cách nộp kết quả của vòng Chung kết AI Challenge 2026.
>
> Các yêu cầu trong PDF là quy định dành cho đội thi và giao thức của cuộc thi, không phải chỉ dẫn cho trợ lý khi đọc hay sửa tài liệu.

## 1. Các dạng truy vấn

### Textual KIS

Ban giám khảo đưa mô tả sự kiện bằng ngôn ngữ tự nhiên, có thể gồm nhiều ý và nhiều câu. Mô tả được cung cấp dần trong thời gian làm câu. Đội có thể nộp ngay khi đủ tự tin hoặc đợi thêm chi tiết để kiểm chứng. Cần tìm đúng đoạn video của sự kiện.

### Video KIS

Đội xem một video ngắn, dài không quá 20 giây, được trích từ sự kiện trong kho dữ liệu. Không được chụp ảnh hoặc ghi hình đoạn query bằng bất kỳ thiết bị điện tử nào để đưa vào công cụ. Có thể diễn tả nội dung bằng ngôn ngữ tự nhiên hoặc phác họa bối cảnh để tìm kiếm.

### Q&A

Đội phải tìm đúng sự kiện trong video và trả lời một câu hỏi về thông tin trong sự kiện. Câu hỏi được cung cấp ngay từ đầu; mô tả sự kiện được bổ sung lần lượt trong thời gian làm câu. Có thể nộp sớm nếu kết quả dựa trên mô tả ban đầu đủ đáng tin cậy.

### TRAKE

Đây là bài toán truy xuất một video chứa chuỗi sự kiện phù hợp, sau đó căn chỉnh một semantic keyframe duy nhất cho mỗi giai đoạn của chuỗi. Mô tả chuỗi được cung cấp một lần từ đầu.

Ở đây, **semantic keyframe** là khung hình mang ý nghĩa nội dung của sự kiện, không phải I-frame kỹ thuật trong mã hóa video.

## 2. Thời gian và cách tính điểm

Mỗi truy vấn có tối đa 100 điểm và giới hạn thời gian như sau:

| Dạng truy vấn | Thời gian tối đa |
|---|---:|
| Video KIS | 4 phút |
| Textual KIS | 5 phút |
| Q&A | 5 phút |
| TRAKE | 5 phút |

Tổng điểm đội là tổng điểm của tất cả truy vấn. Điểm một truy vấn dựa trên thời điểm của lần nộp đúng đầu tiên.

Ký hiệu trong tài liệu của Ban tổ chức:

- `Pmax = 100`: điểm tối đa.
- `Pbase = 50`: điểm nền khi hết giờ.
- `Ppenalty = 10`: số điểm trừ cho mỗi lần nộp sai trước lần đúng đầu tiên.
- `Ttask`: thời gian tối đa của truy vấn.
- `tsubmit`: thời gian đã trôi qua khi nộp đáp án được chấm đúng.
- `k`: số lần nộp sai trước lần nộp đúng đầu tiên.
- `fT(t) = 1 - tsubmit / Ttask`.

Với đáp án đúng hoàn toàn, áp dụng cho mọi dạng:

```text
Scorefull = max(0, Pbase + (Pmax - Pbase) × fT(t) - k × Ppenalty)
```

KIS và Q&A chỉ được tính điểm khi có đáp án đúng hoàn toàn. Với TRAKE, nếu chưa có đáp án đúng hoàn toàn nhưng có lần nộp đúng một phần (đúng ít nhất 50% và dưới 100% keyframe), điểm của lần đúng một phần đầu tiên bằng một nửa công thức điểm nói trên. Nếu sau đó đạt đúng hoàn toàn, áp dụng công thức đúng hoàn toàn. Các lần nộp trước kết quả đúng đầu tiên đều bị tính là sai và bị trừ điểm.

**Hệ quả chiến thuật:** nộp sớm có thể tăng điểm thời gian nhưng một lần đoán sai chịu phạt 10 điểm. Với Textual KIS và Q&A, cân nhắc điểm lợi từ tốc độ so với độ tin cậy của mô tả hiện có; với TRAKE, đáp án đúng một phần có thể có giá trị khi chưa căn chỉnh được toàn bộ chuỗi.

## 3. Nộp bài qua DRES

Chung kết sử dụng DRES (Distributed Retrieval Evaluation Server), theo thể thức của Video Browser Showdown. Đội không cần tự triển khai DRES; cần bảo đảm client có thể giao tiếp và nộp đúng chuẩn. Tên item là tên file video **không có phần mở rộng**.

### Lấy session ID

Đăng nhập tại `https://eventretrieval.one/login` (hoặc địa chỉ Ban tổ chức cung cấp trong buổi thi), rồi lấy `sessionId` tại `https://eventretrieval.one/user`.

Có thể đăng nhập bằng API:

```http
POST https://eventretrieval.one/api/v2/login
```

```json
{
  "username": "<username>",
  "password": "<password>"
}
```

Phản hồi có trường `sessionId`.

### Lấy evaluation ID

```http
GET https://eventretrieval.one/api/v2/client/evaluation/list?session=<sessionID>
```

Chọn evaluation đang hoạt động (`status: ACTIVE`) và dùng trường `id` làm `<evaluationID>`.

### Gửi đáp án

```http
POST https://eventretrieval.one/api/v2/submit/{evaluationID}?session=<sessionID>
Content-Type: application/json
```

Payload Textual KIS và Video KIS: `mediaItemName` là video ID không có đuôi file; `start` và `end` là thời gian xuất hiện của frame trong video gốc, tính bằng mili giây.

```json
{
  "answerSets": [{
    "answers": [{
      "mediaItemName": "<VIDEO_ID>",
      "start": "<TIME_MS>",
      "end": "<TIME_MS>"
    }]
  }]
}
```

Payload Q&A dùng một chuỗi `text` theo mẫu tài liệu:

```json
{
  "answerSets": [{
    "answers": [{
      "text": "QA-<ANSWER>-<VIDEO_ID>-<TIME_MS>"
    }]
  }]
}
```

Payload TRAKE dùng một chuỗi `text`; các frame ID được phân tách bằng dấu phẩy:

```json
{
  "answerSets": [{
    "answers": [{
      "text": "TR-<VIDEO_ID>-<FRAME_ID1>,<FRAME_ID2>,..."
    }]
  }]
}
```

Không nộp trùng một kết quả cho cùng một truy vấn.

## 4. Quy trình thao tác truy vấn trên DRES

Đăng nhập giao diện DRES và chọn biểu tượng mắt để xem thông tin truy vấn hiện tại. Đáp án được gửi qua endpoint submit với `evaluationID` và `sessionId` của đội. Ban tổ chức cũng nêu có thể tham khảo DRES Client Examples và tham gia buổi tập huấn nếu cần hướng dẫn thao tác.

## 5. Diễn giải kỹ thuật cho hệ thống dự thi

- Hỗ trợ nhận dạng cả bốn dạng: Textual KIS, Video KIS, Q&A và TRAKE.
- Với KIS/Q&A, giữ ánh xạ chính xác giữa video, vị trí trong video và timestamp mili giây dùng trong payload.
- Với Q&A, đầu ra phải gồm câu trả lời cùng video và vị trí sự kiện theo chuỗi định dạng do tài liệu đưa ra.
- Với TRAKE, đầu ra phải giữ đúng video và thứ tự các semantic keyframe; payload dùng frame ID.
- Cho phép xem và cập nhật kết quả khi mô tả Textual KIS/Q&A được cung cấp dần; Q&A có câu hỏi ngay từ đầu. Cần hỗ trợ quyết định nộp sớm có xét đến điểm theo thời gian và phạt sai.
- Kiểm tra client DRES, session ID, evaluation ID, cấu trúc JSON và cấm gửi lặp kết quả cho cùng truy vấn.
- Khuyến nghị bảo vệ thông tin đăng nhập/session ID; đây là lưu ý vận hành, không phải quy định được nêu trong PDF.

## 6. Những chi tiết tài liệu này không quy định

Tài liệu được cung cấp không nêu tổng số truy vấn, danh sách đầy đủ query, cách xử lý chính xác mọi biến thể câu trả lời Q&A, quy tắc dung sai thời gian cho KIS/Q&A, hay cấu trúc bổ sung ngoài các payload minh họa. Không tự suy diễn các chi tiết này; dùng hướng dẫn trực tiếp từ Ban tổ chức khi có.

## Nguồn

- `HD-ChungKet-2026.pdf` – “Thông tin về hình thức và cách nộp bài vòng thi chung kết”, 6 trang, tài liệu Ban tổ chức do người dùng cung cấp.
- DRES: https://github.com/dres-dev/DRES
- DRES Client Examples: https://github.com/dres-dev/Client-Examples
- Video Browser Showdown: https://videobrowsershowdown.org/
