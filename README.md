# Báo Cáo Phân Tích Hiệu Quả Truyền Thông & Tỉ Lệ Giữ Chân (Facebook Insights)

Dự án này tự động hóa quy trình phân tích dữ liệu hiệu quả truyền thông và tỷ lệ giữ chân khán giả từ các tệp dữ liệu CSV xuất ra từ Facebook Insights của **Murrplastik Việt Nam**, từ đó tạo ra một trang Dashboard HTML tương tác cao cấp và tự động xuất bản lên web.

- **Đường dẫn Web trực tuyến:** [https://lylamkhai218.github.io/report_media/](https://lylamkhai218.github.io/report_media/)
- **Đường dẫn cục bộ:** `d:\T&TVina\Report`

---

## 📂 Cấu trúc thư mục Dự án

```text
d:\T&TVina\Report\
├── Tỉ lệ giữu chân May-01-2026_May-28-2026_...csv  # File dữ liệu CSV gốc từ Facebook
├── create_report.py                                # Script Python xử lý và kết xuất báo cáo
├── report_giu_chan.html                            # Trang Dashboard báo cáo HTML (đã kết xuất)
├── report_giu_chan_summary.csv                    # File tổng hợp kết quả (đọc tốt trên Excel)
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
* **Tự động quét file mới nhất**: Tự tìm tệp dữ liệu CSV có tên bắt đầu bằng `Tỉ lệ gi* chân` mới nhất trong thư mục.
* **Xử lý chỉ số**: Tính toán tổng lượng xem, thời lượng xem trung bình, tương tác và tỷ lệ tương tác.
* **Phân tích giữ chân**: Đọc dữ liệu giữ chân khán giả qua 40 điểm mốc thời gian của từng video.
* **Phân tích nhân khẩu học**: Thống kê số lượng lượt xem theo nhóm độ tuổi, giới tính và quốc gia.
* **Kết xuất tĩnh (Pre-rendering)**: Điền trực tiếp giá trị tính toán được vào mã HTML trước khi lưu. Điều này giúp các con số hiển thị đầy đủ ngay cả khi trình duyệt tắt JavaScript.
* **Dự phòng ngoại tuyến (Fallback CSS)**: Tích hợp sẵn bộ khung layout CSS để khi xem thử trên điện thoại (QuickLook của Zalo, Viber, Email nơi bị chặn tải CSS ngoài), giao diện vẫn đẹp mắt, ngay ngắn và không bị lỗi vỡ khung hay trượt ngang.

### 2. Tự động hóa Quy trình (`Cập Nhật Báo Cáo.bat`)
Mỗi khi bạn chạy tệp này, Windows sẽ tự động thực hiện tuần tự:
1. Chạy mã Python để cập nhật số liệu mới nhất vào file `report_giu_chan.html` và `report_giu_chan_summary.csv`.
2. Chạy lệnh Git để lưu trữ lịch sử thay đổi của bạn lên nhánh **`main`** của GitHub để sao lưu.
3. Chạy công cụ deploy đẩy bản build sạch lên nhánh **`gh-pages`** của GitHub để cập nhật trang web trực tuyến tức thì.

---

## 🚀 Hướng dẫn Vận hành & Cập nhật dữ liệu mới

Khi bạn có dữ liệu Facebook mới cho các tuần hoặc tháng tiếp theo:

1. **Bước 1:** Tải file CSV dữ liệu tỷ lệ giữ chân từ Facebook Insights về.
2. **Bước 2:** Thả file CSV đó vào thư mục `d:\T&TVina\Report`. Bạn không cần xóa file cũ, Python sẽ tự động ưu tiên đọc file có thời gian cập nhật mới nhất.
3. **Bước 3:** Bấm đúp chuột (Double click) vào tệp **`Cập Nhật Báo Cáo.bat`**.
4. **Bước 4:** Chờ cửa sổ đen chạy xong trong khoảng 5-10 giây.
5. **Bước 5:** Mở đường link web **`https://lylamkhai218.github.io/report_media/`** và nhấn **`Ctrl + Shift + R`** (để xóa bộ nhớ đệm trình duyệt) là bạn sẽ thấy báo cáo mới đã trực tuyến!

---

## 📱 Thiết kế tương thích Điện thoại (Mobile & QuickLook)
* Khi đối tác mở link trên **trình duyệt (Safari, Chrome)**: Báo cáo sẽ hiển thị đầy đủ hiệu ứng kính mờ (Glassmorphism), biểu đồ đường tương tác động, biểu đồ tròn phân tích quốc gia.
* Khi đối tác mở bằng **trình xem thử trực tiếp trong Zalo/Email** (nơi bị chặn tải JS/CSS ngoài): 
  * Giao diện tự động co giãn vừa vặn, không lỗi trượt ngang nhờ cơ chế `box-sizing: border-box`.
  * Các hộp chọn tiêu đề video tự xuống dòng dọc và cắt gọn bằng dấu ba chấm.
  * Các biểu đồ được tự vẽ bằng thanh cột HTML/CSS thuần nên số liệu và biểu đồ giữ chân vẫn hiển thị trực quan.
  * Xuất hiện thanh thông báo hướng dẫn đối tác click nút **[↑] (Chia sẻ)** ở dưới cùng màn hình -> chọn **"Mở bằng Safari"** để xem bản tương tác tốt nhất.
