# Kết quả thực hiện - Ngày 3: Phân tích sơ bộ dữ liệu

## Ngày thực hiện: 16/05/2025

## 1. Tổng quan công việc đã thực hiện

- Xây dựng module tiền xử lý dữ liệu (`data_preprocessor.py`)
- Phát triển các công cụ phân tích tổng quát (`data_analyzer.py`)
- Phân tích chi tiết các bài đăng đầu tiên (OP) (`op_analyzer.py`)
- Phân tích chi tiết các bài trả lời (`reply_analyzer.py`)
- Tạo công cụ tổng hợp để tự động hóa quy trình (`create_datasets.py`)
- Các công cụ trên đã giúp chuẩn hóa dữ liệu từ ngày 2 (sau khi crawling) thành các dataset có cấu trúc, phù hợp cho phân tích định lượng ở ngày 4.

## 2. Các module chính đã phát triển

### 2.1. Module tiền xử lý dữ liệu (data_preprocessor.py)
- Chức năng: Làm sạch văn bản, chuẩn hóa định dạng
- Kết quả: File JSON chứa dữ liệu đã được tiền xử lý

### 2.2. Module phân tích tổng quát (data_analyzer.py)
- Chức năng: Phân tích threads, OP và replies để tạo bộ dataset thống nhất
- Kết quả: Các file CSV chứa thông tin tổng quan về threads, budget, purpose

### 2.3. Module phân tích OP (op_analyzer.py)
- Chức năng: Trích xuất ngân sách, mục đích sử dụng từ bài đăng đầu
- Kết quả: Dataset phân tích chi tiết về các OP

### 2.4. Module phân tích replies (reply_analyzer.py)
- Chức năng: Trích xuất đề xuất linh kiện từ các bài trả lời
- Kết quả: Dataset phân tích chi tiết về các đề xuất

### 2.5. Công cụ tự động (create_datasets.py)
- Chức năng: Tự động hóa toàn bộ quy trình phân tích
- Cách sử dụng: python src/create_datasets.py hoặc với các tham số riêng lẻ

## 3. Thách thức và kinh nghiệm rút ra

### 3.1. Xử lý ngôn ngữ tự nhiên
- Tiếng Việt unicode: Văn bản tiếng Việt thường gặp vấn đề với dấu.
- Cách viết không thống nhất: Người dùng viết tên linh kiện theo nhiều cách khác nhau (i5, Core i5, i5-1240P...).
- Không phân biệt phủ định: Hệ thống chưa hiểu "không cần RGB" khác với "cần RGB".
- Từ đồng âm khác nghĩa: Như "k" vừa là đơn vị tiền tệ (15k đồng), vừa là đơn vị độ phân giải (màn hình 4k).

### 3.2. Trích xuất thông tin
- Ngân sách đa dạng: Người dùng có nhiều cách diễn đạt ngân sách, khi thì rõ ràng, khi thì ẩn trong câu.
- Ưu tiên mâu thuẫn: Khó xác định ưu tiên khi người dùng vừa muốn "màn hình đẹp" vừa "giá rẻ".
- Thông tin mâu thuẫn trong thread: Đôi khi OP đề cập ngân sách khác nhau ở các phần khác nhau.

### 3.3. Dataset được tạo ra

Module này tạo ra các file CSV chính:
- `threads_analysis.csv`: Thông tin tổng quan về các threads
- `component_suggestions.csv`: Chi tiết về các đề xuất linh kiện
- `budget_distribution.csv`: Phân tích phân bố ngân sách
- `purpose_analysis.csv`: Phân tích mục đích sử dụng

## 4. Kết quả đạt được

### 4.1. Dataset phân tích
- Dữ liệu threads: Thông tin tổng quan về 197 threads thu thập được
- Phân tích OP: Dataset phân tích chi tiết về ngân sách, mục đích sử dụng
- Phân tích replies: Dataset về các đề xuất linh kiện

### 4.2. Sẵn sàng cho ngày 4
- Các dataset đã tạo ra là nền tảng vững chắc cho ngày 4 (Phân tích chi tiết dữ liệu).