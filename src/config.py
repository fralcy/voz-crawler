import os
from dotenv import load_dotenv
from pathlib import Path

# Load biến môi trường từ file .env
load_dotenv()

# Thư mục gốc của dự án
BASE_DIR = Path(__file__).resolve().parent.parent

# Đường dẫn các thư mục
CACHE_DIR = BASE_DIR / "cache"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Cache các thread
THREAD_CACHE_DIR = CACHE_DIR / "threads"
IMAGE_CACHE_DIR = CACHE_DIR / "images"

# Data directories
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "ocr-processed"

# Tạo các thư mục nếu chưa tồn tại
for dir_path in [CACHE_DIR, DATA_DIR, LOG_DIR, THREAD_CACHE_DIR, 
                IMAGE_CACHE_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Cấu hình VOZ
VOZ_BASE_URL = os.getenv("VOZ_BASE_URL", "https://voz.vn")
VOZ_BOX_URL = os.getenv("VOZ_BOX_URL", "https://voz.vn/f/tu-van-cau-hinh.70/")
THREAD_LIMIT = int(os.getenv("THREAD_LIMIT", 200))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 2))
HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "True").lower() == "true"

# Cấu hình crawler
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", 60))  # Thời gian timeout khi tải trang (giây)
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))  # Số lần thử lại tối đa khi gặp lỗi

# Cấu hình OCR
OCR_MIN_IMAGE_WIDTH = int(os.getenv("OCR_MIN_IMAGE_WIDTH", 100))  # Chiều rộng tối thiểu của hình ảnh để OCR
OCR_MIN_IMAGE_HEIGHT = int(os.getenv("OCR_MIN_IMAGE_HEIGHT", 100))  # Chiều cao tối thiểu của hình ảnh để OCR
OCR_MAX_DIMENSION = int(os.getenv("OCR_MAX_DIMENSION", 1600))  # Kích thước tối đa cho một chiều của hình ảnh khi OCR

# Cấu hình checkpoint
CHECKPOINT_INTERVAL = int(os.getenv("CHECKPOINT_INTERVAL", 5))  # Số thread giữa các lần lưu checkpoint