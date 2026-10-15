# KUHBM — quản lý khách sạn

Flask + SQLAlchemy + SQLite. Giữ bố cục sidebar, phân quyền và các thư mục `routes/`, `templates/` của bản ZIP gốc. Chat AI dùng **OpenAI SDK**, hỗ trợ GPT qua API và local API tương thích OpenAI. Chat giữa người dùng là chức năng riêng lưu trong SQLite.

## Chạy trên Windows CMD

Python 3.11 trở lên. Mở CMD tại thư mục chứa `app.py`:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Mở http://127.0.0.1:5000. Ctrl+C để dừng. Linux/macOS thay lệnh kích hoạt bằng `source .venv/bin/activate`.

Không cần Node.js hoặc MySQL. Dữ liệu mẫu tự tạo khi database mới chưa có tài khoản. `hotel.db` trong ZIP có bốn tài khoản và sáu phòng của bản gốc. Khởi động lại không xóa dữ liệu.

Database cũ được tự bổ sung các cột cần thiết và bảng tin nhắn khi chạy. Nếu bạn có `hotel.db` riêng: dừng web, sao lưu file đó, chép vào thư mục dự án rồi khởi chạy. Không chạy `seed.py` để nâng cấp: lệnh chạy trực tiếp file seed của bản gốc dùng để đặt lại dữ liệu.

## Tài khoản mẫu

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Khách | guest@hotel.com | guest123 |
| Lễ tân | reception@hotel.com | staff123 |
| Nhân viên dịch vụ | staff@hotel.com | staff123 |
| Admin | admin@hotel.com | admin123 |

## Trang chủ và giao diện

- `/` là trang chủ công khai hiển thị các phòng, loại, mô tả và giá. Không bắt buộc đăng nhập để xem.
- Khách có thể lọc ngày nhận/trả và loại phòng; quy tắc lịch dùng chung với phần đặt phòng. Phòng bảo trì không hiển thị.
- Bấm đặt phòng khi chưa đăng nhập sẽ mở trang đăng nhập; lịch/loại phòng vừa chọn được giữ khi đăng nhập hoặc tạo tài khoản.
- `/workspace` dẫn đến khu vực riêng theo vai trò. Sau đăng xuất trở về trang chủ công khai.
- Menu chỉ hiển thị “Trợ lý khách sạn”, “Tin nhắn”. Không trình bày nhà cung cấp AI, cấu hình `.env`, sơ đồ quyền chat hoặc tài khoản mẫu trên giao diện.
- Lỗi kết nối/cấu hình trợ lý chỉ hiện thông báo hỗ trợ chung cho khách. Chi tiết lỗi ở log server và phần cấu hình dưới đây để người vận hành kiểm tra.
- Tài khoản mẫu ở bảng README phía trên chỉ dành cho người cài bài; không còn hiện trên trang đăng nhập.
- Đã đạt 33 kiểm thử cho chat, trang chủ công khai, lọc phòng, giữ lịch qua đăng nhập/đăng ký, quyền truy cập và ẩn thông tin cấu hình. Mã kiểm tra ngày/link cũ cũng đã được kiểm tra bằng JavaScript.

## Các phần đã triển khai

### Khách hàng

- Ngày nhận không trước hôm nay theo giờ Việt Nam.
- Ngay khi thay đổi ngày nhận, ô checkout đổi `min` theo ngày đó. Nếu checkout cũ nhỏ hơn ngày nhận mới, nó tự chuyển về cùng ngày.
- Cho phép **checkout >= checkin**. Cùng ngày tính tối thiểu một đêm.
- Không cần bấm Search mới kiểm tra quy tắc ngày. Search vẫn dùng để tìm phòng trống theo ngày/loại.
- Nếu đổi bộ lọc sau khi Search, các nút đặt của kết quả cũ bị khóa để tránh đặt nhầm lịch. Bấm Search để cập nhật kết quả.
- Server kiểm tra lại ngày, tình trạng phòng và trùng lịch lúc lưu; không tin giá hoặc kết quả tìm kiếm gửi từ trình duyệt.
- Đặt online cọc mô phỏng 30%. Trong **My Bookings**, khách tự bấm xác nhận cọc. Không có ngân hàng/chuyển tiền thật.
- Sau nhận phòng, khách gửi yêu cầu dọn/dịch vụ/sửa chữa trong Services, hoặc nhắn trực tiếp lễ tân trong Tin nhắn.

### Lễ tân

- **Đặt tại quầy**: chọn tài khoản khách có sẵn, hoặc nhập tên/điện thoại khách lẻ không cần email thật. Hệ thống tạo hồ sơ nội bộ cho khách lẻ; hồ sơ này không có mật khẩu đăng nhập được cấp cho khách.
- Chọn ngày sẽ tải các phòng trống; chọn phòng hiển thị số đêm, giá/đêm và tổng dự kiến ngay trên form.
- Khi lưu, giá được tính lại trên server và chốt vào đơn. Đặt tại quầy không bắt buộc cọc.
- **Chi tiết / tính tiền**: xem tiền phòng, từng dịch vụ đã hoàn thành, tổng tiền, cọc/tiền đã ghi nhận và số còn phải thu.
- Nhận phòng chỉ được thực hiện đúng khoảng ngày đặt, phòng đã sẵn sàng và cọc online đã xác nhận.
- **Yêu cầu khách**: tiếp nhận hộ khách đang ở, cập nhật pending/in_progress/completed/cancelled, ghi phí dịch vụ. Chỉ dịch vụ completed được cộng hóa đơn; dịch vụ hủy không tính tiền.
- Quy trình trả: hoàn tất/hủy yêu cầu đang mở → kiểm tra phòng và ghi chú → thanh toán → trả phòng. Thêm/sửa yêu cầu sau kiểm tra sẽ yêu cầu kiểm phòng lại trước khi chốt.
- Tiền mặt cho nhập số khách đưa và tính tiền thừa; thẻ/chuyển khoản mô phỏng phải khớp số còn phải thu. Không cộng tiền thừa vào doanh thu.
- Không thể thanh toán một đơn hai lần, sửa phí sau thanh toán, hoặc chốt khi còn yêu cầu đang mở.
- Hủy được đơn chưa nhận với lý do. Phòng đang ở cần xử lý trả trước.
- Trả phòng chuyển trạng thái `cleaning`; lễ tân hoặc nhân viên dịch vụ xác nhận dọn xong.

### Admin

- Trong Rooms, mở **Sửa giá / loại phòng** để đổi giá, kiểu single/double/suite và mô tả.
- Đơn đã đặt giữ nguyên tổng tiền và giá đêm đã chốt; thay đổi giá áp dụng các đơn sau đó.
- Giá âm, bằng 0, NaN, Infinity, loại phòng lạ bị từ chối trên server.
- Chuyển sang bảo trì hủy tất cả đơn chưa nhận của phòng đó và lưu lý do. Không bảo trì phòng còn khách. Kết thúc bảo trì cần dọn trước khi nhận khách.
- Không xóa tài khoản đã có lịch sử đơn/yêu cầu/tin nhắn; dùng khóa tài khoản để giữ lịch sử.

### Chat trực tiếp

| Người gửi | Người có thể trao đổi |
|---|---|
| Khách | Lễ tân |
| Lễ tân | Khách, admin, nhân viên dịch vụ |
| Admin | Lễ tân, nhân viên dịch vụ |
| Nhân viên dịch vụ | Admin, lễ tân |

Mở **Tin nhắn**, chọn người nhận. Có thể dùng hai trình duyệt/cửa sổ ẩn danh để thử hai vai trò. Tin nhắn được lưu database và trang tự lấy tin mới mỗi 3 giây. Hiển thị 100 tin gần nhất khi mở cuộc trò chuyện; không có đính kèm hay thông báo đẩy.

Mỗi hội thoại chỉ trả tin giữa người đang đăng nhập và người nhận hợp lệ. Không được đọc hội thoại khác bằng cách sửa URL, giả người gửi, hoặc chat với tài khoản bị khóa. Tin nhắn được hiển thị dưới dạng văn bản, không thực thi HTML.

## Quy tắc lịch và tiền

- Giữ thêm một ngày để dọn sau ngày trả đã đặt, không tính tiền ngày dọn. Trả ngày 15 thì đơn mới nhận sớm nhất ngày 16.
- Khoảng giữ `[check_in, check_out + 1 ngày)` áp dụng cho cả đơn mới và đơn cũ; kiểm tra cả khi đặt chen trước đơn cũ.
- Đơn hủy không giữ lịch. Đơn đã trả vẫn giữ phần ngày dọn.
- Nhận và trả cùng ngày: tính một đêm; ngày đó cũng là ngày trả/dọn, khách mới nhận sớm nhất hôm sau.
- Cho trả sớm để thực hành; vẫn giữ tiền/lịch của đơn đã chốt. Trả muộn giữ ngày dọn ít nhất đến ngày trả thực tế + 1; chưa tính phụ phí trả muộn.
- Tiền giữ đơn vị **AED** của dự án gốc, không tự quy đổi VND. Tính bằng Decimal và làm tròn hai chữ số; các cột tiền cũ trong SQLite vẫn dùng Float để tương thích.
- SQLite dùng `BEGIN IMMEDIATE` trước khi kiểm tra/lưu đơn và khi chốt tiền, giúp hai thao tác đồng thời không ghi trùng. Cơ chế khóa dòng cho PostgreSQL được giữ nhưng chưa kiểm thử trên máy PostgreSQL.
- Cọc online chưa có tác vụ tự hết hạn: khách/lễ tân hủy đơn để giải phóng lịch.

## Cấu hình GPT / local API

Bản này được tạo riêng từ KUHBM đã cập nhật; giữ các chức năng đặt tại quầy, thanh toán, dịch vụ, sửa giá/loại phòng và chat người dùng. Các tài khoản/mật khẩu mẫu vẫn như bảng trên.

Chép `.env.example` thành `.env` rồi chọn **một** cấu hình bên dưới. Khởi động lại `python app.py` sau khi sửa `.env`.

### Dùng local API tương thích OpenAI

```dotenv
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
OPENAI_MODEL=ten_model_cua_ban
OPENAI_API_KEY=
```

- Bật API server và tải model trên phần mềm bạn đang dùng trước.
- Thay địa chỉ/cổng theo địa chỉ server hiển thị. Đây chỉ là ví dụ cổng 1234, không phải cổng bắt buộc.
- Thay `ten_model_cua_ban` bằng **model ID thực tế** do server cung cấp. Không gõ nguyên tên mẫu này. Có thể xem danh sách model trong giao diện server hoặc endpoint `GET /v1/models` nếu server hỗ trợ.
- Server phải hỗ trợ `POST /v1/chat/completions` với định dạng OpenAI. `OPENAI_BASE_URL` thường kết thúc bằng `/v1`; không thêm `/chat/completions` vào biến này.
- Nếu server local ở localhost không yêu cầu xác thực, để key trống: ứng dụng tự gửi chuỗi mẫu `local-no-key` vì SDK cần chuỗi key. Nếu server yêu cầu key thì điền key của server.
- Với server LAN/API riêng không yêu cầu key, điền `OPENAI_API_KEY=local-no-key` một cách rõ ràng.
- `127.0.0.1` là máy **đang chạy Flask**. Nếu Flask ở máy khác/Docker/hosting, dùng địa chỉ API mà máy đó truy cập được.

Đây là giao thức tương thích OpenAI; model local thực tế do server cung cấp, không tự biến thành model GPT của OpenAI.

### Dùng GPT qua OpenAI API chính thức

```dotenv
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=key_api_cua_ban
OPENAI_MODEL=ten_model_gpt_ban_duoc_phep_dung
```

Thay hai giá trị mẫu bằng API key và model ID được tài khoản của bạn hỗ trợ. Key chỉ đọc trên backend, không đưa vào HTML. Mở mục **Trợ lý khách sạn** khi đăng nhập khách để chat.

### Khi server báo không nhận tham số giới hạn token

Thông thường không cần chỉnh. Ứng dụng tự dùng `max_completion_tokens` với host `api.openai.com`; server riêng mặc định dùng `max_tokens`. Nếu proxy/local server của bạn yêu cầu trường khác, thêm một trong hai dòng sau vào `.env`:

```dotenv
OPENAI_TOKEN_PARAMETER=max_completion_tokens
```

hoặc `OPENAI_TOKEN_PARAMETER=max_tokens`. Không điền cả hai. Mỗi câu trả lời giới hạn 1024 token; thời gian chờ 60 giây, không tự gửi lại để tránh gọi trùng.

### Phạm vi chat

`routes/chat.py` gọi `OpenAI(base_url=...)` và `chat.completions.create()`. Model chỉ tư vấn, không tự đặt/cọc/thanh toán. Chỉ gửi thông tin loại/giá phòng công khai; kiểm tra lịch bằng Book a Room. Một phần lịch sử ngắn được giữ trong phiên, xóa khi đăng xuất. Phản hồi hiển thị dạng văn bản, không thực thi HTML.

Nếu thiếu cấu hình, sai model/key, API chưa bật hoặc hết thời gian, trang chat hiện thông báo chung. Xem log server để sửa cấu hình. Chức năng khách sạn và chat trực tiếp giữa người dùng vẫn chạy bình thường.

Các file thay đổi so với bản Gemini: `config.py`, `.env.example`, `requirements.txt`, `routes/chat.py`, `templates/guest/chat.html`, `templates/base.html`, `README.md`. Không thay đổi schema SQLite.

Đã đạt 14 kiểm thử chat: local không key, key/model tùy chỉnh, API chính thức, giới hạn token, lịch sử, lỗi cấu hình, CSRF, phản hồi rỗng, lỗi kết nối và SDK thật gọi server HTTP local giả lập. Chưa gọi API/model thật của bạn.

## File cần đọc / sửa

| File | Vai trò |
|---|---|
| `routes/auth.py` | Trang chủ công khai, đăng nhập/đăng ký và giữ lịch đã chọn |
| `templates/home.html`, `static/public.css` | Giao diện giới thiệu và lọc phòng trước đăng nhập |
| `models.py` | Các lớp User, Room, Booking, ServiceRequest, Message và phương thức nghiệp vụ |
| `database.py` | Tự nâng cấp database cũ, không xóa dữ liệu |
| `app.py` | Tạo Flask, đăng ký route, kiểm tra mã form, xử lý lỗi |
| `routes/guest.py` | Đặt online, cọc, hủy và yêu cầu dịch vụ của khách |
| `routes/reception.py` | Đặt tại quầy, kiểm phòng, tính tiền, thanh toán, yêu cầu khách |
| `routes/admin.py` | Chỉnh giá/loại, trạng thái phòng và quản lý tài khoản |
| `routes/staff.py` | Xử lý dịch vụ và dọn phòng |
| `routes/messages.py` | Chat trực tiếp có phân quyền |
| `routes/chat.py` | Kết nối trợ lý khách sạn |
| `templates/reception/` | Các trang đặt tại quầy, danh sách đơn, tính tiền, xử lý yêu cầu |
| `templates/messages.html` | Giao diện chat người dùng và cập nhật tin mới |
| `static/js/booking.js` | Kiểm tra ngày ngay khi nhập, tải phòng và tính tiền dự kiến tại quầy |

Ví dụ thanh toán: form ở `templates/reception/bill.html` gửi POST → hàm `pay()` khóa đơn → object `Booking` gọi `thanh_toan()` → kiểm tra tiền/trạng thái → `db.session.commit()` → chuyển lại phiếu chi tiết. Có lỗi thì rollback, không lưu một nửa.

Giữ tên lớp/cột và phần giao diện tiếng Anh từ dự án gốc; phần bổ sung có giải thích tiếng Việt. Các tài liệu `docs/superpowers/` là tài liệu gốc để tham khảo, không phải hướng dẫn vận hành bản cập nhật.

## Cách thử nhanh

1. Đăng nhập khách, Book a Room, đổi check-in về sau checkout: checkout cập nhật ngay. Chọn cùng ngày, Search, đặt phòng và xác nhận cọc trong My Bookings.
2. Đăng nhập lễ tân, mở chi tiết đơn, nhận phòng. Mở Yêu cầu khách để thêm dịch vụ và phí, hoàn tất yêu cầu.
3. Kiểm tra phòng, thử nhập thiếu tiền (bị chặn), sau đó nhập đủ/tiền mặt dư và thanh toán. Phòng chuyển chờ dọn, bấm xác nhận dọn xong.
4. Với đặt tại quầy: chọn khách có sẵn hoặc tên khách lẻ, chọn ngày/phòng và kiểm tra tổng dự kiến.
5. Admin sửa giá/loại phòng; so sánh đơn cũ với đơn mới.
6. Mở hai trình duyệt đăng nhập khách/lễ tân hoặc admin/nhân viên để nhắn qua lại.

Không nộp `.venv`, `__pycache__` hay `.env` có key thật. Chương trình chạy cục bộ; thanh toán chỉ là mô phỏng. Chưa triển khai bản cập nhật lên trang Render của tác giả gốc. Các luồng khách sạn giữ nguyên từ bản trước. Chat đã kiểm thử bằng SDK giả và server HTTP local giả lập, không gọi model thật; chưa xác nhận giao diện bằng cloud browser hoặc gọi GPT thật với key/server của bạn.

Dự án gốc: https://github.com/Frisbiz/KUHBM. Bản gốc công bố MIT trong README; phần cập nhật giữ ghi nhận nguồn này.
