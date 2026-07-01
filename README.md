# Báo Cáo Phân Tích Hiệu Quả Truyền Thông & Tỉ Lệ Giữ Chân (Facebook Insights)

Dự án này tự động hóa quy trình phân tích dữ liệu hiệu quả truyền thông và tỷ lệ giữ chân khán giả từ các tệp dữ liệu CSV xuất ra từ Facebook Insights của **Murrplastik Việt Nam**, từ đó tạo ra một trang Dashboard HTML tương tác cao cấp và tự động xuất bản lên web.

- **Đường dẫn Web trực tuyến:** [https://lylamkhai218.github.io/report_media/](https://lylamkhai218.github.io/report_media/)
- **Đường dẫn cục bộ:** `d:\T&TVina\Report`

---

## 📂 Cấu trúc thư mục Dự án

```text
d:\T&TVina\Report\
├── data/                                           # Thư mục chứa các file dữ liệu CSV gốc theo tháng
│   ├── Tỉ lệ giữu chân May-01-2026_...csv         # Dữ liệu tháng 5 (tiếng Việt)
│   └── Jun-01-2026_Jun-30-2026_...csv             # Dữ liệu tháng 6 (tiếng Anh)
├── assets/                                         # Thư mục chứa hình ảnh, logo, favicon của dự án
├── references/                                     # Thư mục chứa tài liệu nháp hoặc tham khảo
├── create_report.py                                # Script Python xử lý và kết xuất báo cáo đa tháng
├── report_media.html                               # Trang Dashboard báo cáo HTML (hỗ trợ chuyển đổi tháng)
├── report_giu_chan_summary.csv                    # File tổng hợp kết quả của tất cả các tháng (đọc trên Excel)
├── index.html                                      # File chuyển hướng tự động (redirect) lên web
├── Cập Nhật Báo Cáo.bat                            # File chạy tự động hóa (chạy bằng click chuột)
├── package.json                                    # Cấu hình thư viện Node.js (gh-pages)
├── .gitignore                                      # Loại bỏ file CSV và rác khỏi GitHub để bảo mật
└── node_modules/                                   # Các gói phụ thuộc Node.js hỗ trợ deploy
```

---

## ⚙️ Các thành phần và Cách hoạt động

### 1. Xử lý Dữ liệu (`create_report.py`)
Mã nguồn Python có nhiệm vụ:
* **Tự động quét và phân loại theo tháng**: Quét toàn bộ các file dữ liệu CSV trong thư mục `data/` và tự động phân nhóm theo tháng dựa trên định dạng ngày tháng trong tên file.
* **Hỗ trợ định dạng ngôn ngữ kép**: Đọc được cả file CSV xuất ra từ giao diện Facebook tiếng Việt (có cột "ID bài viết", "Xem tự nhiên", v.v.) và tiếng Anh (có cột "Post ID", "Organic", v.v.).
* **Tính toán chỉ số & Phân tích giữ chân**: Tính toán tổng lượng xem, thời lượng xem trung bình, tỷ lệ giữ chân khán giả tại 41 mốc và phân tích nhân khẩu học cho từng tháng một cách độc lập.
* **Kết xuất tĩnh & Động**: Tích hợp toàn bộ cơ sở dữ liệu các tháng vào trong file `report_media.html` dưới dạng JSON, giúp trang web hoạt động hoàn toàn offline, tải cực nhanh mà vẫn hỗ trợ chuyển đổi tháng và ngôn ngữ linh hoạt bằng JavaScript.

### 2. Tự động hóa Quy trình (`Cập Nhật Báo Cáo.bat`)
Mỗi khi bạn chạy tệp này, Windows sẽ tự động thực hiện tuần tự:
1. Chạy mã Python để quét toàn bộ dữ liệu trong `data/`, cập nhật `report_media.html` và `report_giu_chan_summary.csv`.
2. Chạy lệnh Git để lưu trữ lịch sử thay đổi của bạn lên nhánh **`main`** của GitHub để sao lưu.
3. Chạy công cụ deploy đẩy bản build sạch lên nhánh **`gh-pages`** của GitHub để cập nhật trang web trực tuyến tức thì.

---

## 🚀 Hướng dẫn Vận hành & Cập nhật dữ liệu mới

Khi bạn có dữ liệu Facebook mới cho các tuần hoặc tháng tiếp theo:

1. **Bước 1:** Tải file CSV dữ liệu tỷ lệ giữ chân từ Facebook Insights về.
2. **Bước 2:** Thả file CSV đó vào thư mục **`data/`** (`d:\T&TVina\Report\data`). Bạn không cần xóa file cũ, Python sẽ tự động nhóm các file và hiển thị từng tháng tương ứng.
3. **Bước 3:** Bấm đúp chuột (Double click) vào tệp **`Cập Nhật Báo Cáo.bat`**.
4. **Bước 4:** Chờ cửa sổ đen chạy xong trong khoảng 5-10 giây.
5. **Bước 5:** Mở đường link web **`https://lylamkhai218.github.io/report_media/`** và nhấn **`Ctrl + Shift + R`** (để xóa bộ nhớ đệm trình duyệt) là bạn sẽ thấy báo cáo mới đã cập nhật!

---

## 📱 Thiết kế tương thích Điện thoại (Mobile & QuickLook)
* Khi đối tác mở link trên **trình duyệt (Safari, Chrome)**: Báo cáo sẽ hiển thị đầy đủ hiệu ứng kính mờ (Glassmorphism), biểu đồ đường tương tác động, biểu đồ tròn phân tích quốc gia.
* Khi đối tác mở bằng **trình xem thử trực tiếp trong Zalo/Email** (nơi bị chặn tải JS/CSS ngoài): 
  * Giao diện tự động co giãn vừa vặn, không lỗi trượt ngang nhờ cơ chế `box-sizing: border-box`.
  * Các hộp chọn tiêu đề video tự xuống dòng dọc và cắt gọn bằng dấu ba chấm.
  * Các biểu đồ được tự vẽ bằng thanh cột HTML/CSS thuần nên số liệu và biểu đồ giữ chân vẫn hiển thị trực quan.
  * Xuất hiện thanh thông báo hướng dẫn đối tác click nút **[↑] (Chia sẻ)** ở dưới cùng màn hình -> chọn **"Mở bằng Safari"** để xem bản tương tác tốt nhất.
