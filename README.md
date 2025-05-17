# VOZ Crawler - Hướng dẫn sử dụng

## Mục lục
- [1. Clone dự án](#1-clone-dự-án)
- [2. Cài đặt thư viện](#2-cài-đặt-thư-viện)
- [3. Chạy crawl & OCR](#3-chạy-crawl--ocr)
- [4. Tiền xử lý & phân tích sơ bộ](#4-tiền-xử-lý--phân-tích-sơ-bộ)
- [5. Phân tích chi tiết & vẽ biểu đồ](#5-phân-tích-chi-tiết--vẽ-biểu-đồ)
- [6. Cấu trúc thư mục](#6-cấu-trúc-thư-mục)
- [7. Ghi chú](#7-ghi-chú)

---

## 1. Clone dự án

```bash
git clone https://github.com/your-username/voz-crawler.git
cd voz-crawler
```

## 2. Cài đặt thư viện

Tạo và kích hoạt môi trường ảo:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```
Cài đặt:
```bash
pip install -r requirements.txt
```
> **Yêu cầu:** Đã cài Chrome để dùng selenium.

---

## 3. Chạy crawl & OCR

```bash
python src/main.py
```
Một số tùy chọn:
- `--thread-limit 100` : Giới hạn số thread
- `--workers 2` : Số luồng xử lý
- `--no-ocr` : Bỏ qua OCR
- `--resume` : Tiếp tục từ checkpoint

---

## 4. Tiền xử lý & phân tích sơ bộ

```bash
python src/create_datasets.py
```
Chạy từng bước:
```bash
python src/create_datasets.py --preprocessor-only
python src/create_datasets.py --analyzer-only
python src/create_datasets.py --op-only
python src/create_datasets.py --reply-only
```
> Kết quả lưu ở `data/analysis/`

---

## 5. Phân tích chi tiết & vẽ biểu đồ

```bash
python src/detailed_analysis.py
```
Một số tùy chọn:
```bash
python src/detailed_analysis.py --analysis-only
python src/detailed_analysis.py --network-only
python src/detailed_analysis.py --sentiment-only
python src/detailed_analysis.py --visualization-only
```
> Biểu đồ lưu ở `data/analysis/visualizations/`

---

## 6. Cấu trúc thư mục

```text
voz-crawler/
├── cache/
├── data/
│   ├── raw/
│   ├── ocr-processed/
│   ├── preprocessed/
│   └── analysis/
│       ├── op_analysis/
│       ├── reply_analysis/
│       ├── budget_analysis/
│       ├── detailed_analysis/
│       ├── network_analysis/
│       ├── sentiment_analysis/
│       └── visualizations/
├── logs/
├── src/
└── requirements.txt
```

---

## 7. Ghi chú

- Theo dõi tiến độ:  
  `python src/monitor.py`
- Tạo lại biểu đồ:  
  `python src/visualization_creator.py`  
- Yêu cầu: Python ≥ 3.8, Chrome, RAM ≥ 4GB
- Lỗi ChromeDriver: kiểm tra Chrome đã cài đặt
- Crawl chậm: tăng `REQUEST_DELAY` trong `config.py`
- Lỗi OCR: dùng `--no-ocr` để bỏ qua