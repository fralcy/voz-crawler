import re
import string
import unicodedata
import json
import logging
from pathlib import Path

from config import PROCESSED_DATA_DIR, DATA_DIR

# Tạo thư mục cho dữ liệu đã tiền xử lý
PREPROCESSED_DATA_DIR = DATA_DIR / "preprocessed"
PREPROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DataPreprocessor:
    """
    Class tiền xử lý dữ liệu từ các thread VOZ để chuẩn bị cho phân tích
    """
    def __init__(self, threads_dir=PROCESSED_DATA_DIR):
        self.threads_dir = threads_dir
        self.threads_data = []
        self.preprocessed_data = []
        
    def load_thread_files(self):
        """Tải tất cả các file thread đã crawl"""
        self.threads_data = []
        thread_files = list(self.threads_dir.glob("thread_*.json"))
        logger.info(f"Tìm thấy {len(thread_files)} file thread để tiền xử lý")
        
        for file_path in thread_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    thread_data = json.load(f)
                    self.threads_data.append(thread_data)
            except Exception as e:
                logger.error(f"Lỗi khi đọc file {file_path}: {str(e)}")
                
        logger.info(f"Đã tải {len(self.threads_data)} threads để tiền xử lý")
        return self.threads_data
        
    def clean_text(self, text):
        """Làm sạch văn bản: loại bỏ emoji, ký tự đặc biệt, chuẩn hóa Unicode"""
        if not text:
            return ""
            
        # Chuẩn hóa Unicode
        text = unicodedata.normalize('NFC', text)
        
        # Loại bỏ emoji và ký tự đặc biệt không phải chữ cái, số
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F700-\U0001F77F"  # alchemical symbols
                                   u"\U0001F780-\U0001F7FF"  # Geometric Shapes
                                   u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                                   u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                                   u"\U0001FA00-\U0001FA6F"  # Chess Symbols
                                   u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                                   u"\U00002702-\U000027B0"  # Dingbats
                                   u"\U000024C2-\U0001F251" 
                                   "]+", flags=re.UNICODE)
        text = emoji_pattern.sub(r'', text)
        
        # Thay thế nhiều dấu cách liên tiếp bằng một dấu cách
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    def normalize_price_format(self, text):
        """Chuẩn hóa định dạng giá tiền (VND -> triệu đồng)"""
        if not text:
            return text
            
        # Tìm các mẫu số tiền phổ biến và chuẩn hóa về triệu đồng
        price_patterns = [
            # Dạng "X triệu"
            (r'(\d+(?:[,.]\d+)?)\s*(?:triệu|tr|củ)', lambda m: f"{float(m.group(1).replace(',', '.'))} triệu"),
            # Dạng "X nghìn" - Nghìn k = nghìn nghìn = triệu
            (r'(\d+(?:[,.]\d+)?)\s*(?:nghìn|ngàn)\s*k', lambda m: f"{float(m.group(1).replace(',', '.')) * 1000 / 1000000} triệu"),
            # Dạng "X nghìn"
            (r'(\d+(?:[,.]\d+)?)\s*(?:nghìn|ngàn)', lambda m: f"{float(m.group(1).replace(',', '.')) / 1000} triệu"),
            # Dạng "X.XXX.XXX đồng"
            (r'(\d+(?:[,.]\d+)+)\s*(?:đồng|vnd|đ)', lambda m: f"{float(m.group(1).replace('.', '').replace(',', '.')) / 1000000} triệu"),
            # Dạng "X k" - Chú ý: k ở đây là "nghìn" (kilo), KHÔNG phải độ phân giải
            (r'(\d+(?:[,.]\d+)?)\s*k(?:\s|$|,|\.|;|:)', lambda m: f"{float(m.group(1).replace(',', '.')) / 1000} triệu")
        ]
        
        for pattern, replacement in price_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            
        return text
        
    def normalize_component_names(self, text):
        """Chuẩn hóa tên các linh kiện máy tính"""
        if not text:
            return text
            
        # Từ điển chuẩn hóa tên linh kiện
        component_mappings = {
            # CPU
            r'\bi(\d)\s*\-\s*(\d{4,5})(?:[a-z]*)\b': r'Intel Core i\1-\2',
            r'\bi(\d)\s*(\d{4,5})(?:[a-z]*)\b': r'Intel Core i\1-\2',
            r'\br(\d)\s*\-\s*(\d{4,5})(?:[a-z]*)\b': r'AMD Ryzen \1-\2',
            r'\br(\d)\s*(\d{4,5})(?:[a-z]*)\b': r'AMD Ryzen \1-\2',
            r'\bryzen\s*(\d)\s*\-\s*(\d{4,5})(?:[a-z]*)\b': r'AMD Ryzen \1-\2',
            r'\bryzen\s*(\d)\s*(\d{4,5})(?:[a-z]*)\b': r'AMD Ryzen \1-\2',
            
            # GPU
            r'\brtx\s*(\d{4})(?:\s*ti)?\b': r'NVIDIA RTX \1',
            r'\bgtx\s*(\d{4})(?:\s*ti)?\b': r'NVIDIA GTX \1',
            r'\brx\s*(\d{4})(?:\s*xt)?\b': r'AMD RX \1',
            
            # RAM
            r'\b(\d{1,2})\s*gb\s*ram\b': r'\1GB RAM',
            r'\bram\s*(\d{1,2})\s*gb\b': r'\1GB RAM',
            r'\b(\d{1,2})\s*gb\s*x\s*(\d)\b': r'\1GB x\2 RAM',
            
            # Ổ cứng
            r'\bssd\s*(\d{3,4})\s*gb\b': r'SSD \1GB',
            r'\bssd\s*(\d)\s*tb\b': r'SSD \1TB',
            r'\bhdd\s*(\d)\s*tb\b': r'HDD \1TB',
            
            # Mainboard
            r'\bb(\d{3})\b': r'B\1',
            r'\bz(\d{3})\b': r'Z\1',
            r'\bh(\d{3})\b': r'H\1',
            r'\ba(\d{3})\b': r'A\1',
            r'\bx(\d{3})\b': r'X\1'
        }
        
        # Áp dụng các quy tắc chuẩn hóa
        for pattern, replacement in component_mappings.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            
        return text
        
    def combine_text_and_ocr(self, post_data):
        """Kết hợp nội dung text thường và text OCR từ ảnh"""
        if not post_data:
            return ""
            
        content_text = post_data.get('content_text', '')
        
        # Kết hợp với text OCR từ ảnh nếu có
        ocr_texts = []
        for image in post_data.get('images', []):
            ocr_text = image.get('ocr_text', '')
            if ocr_text:
                ocr_texts.append(ocr_text)
                
        # Nếu có OCR text, thêm vào sau content_text
        if ocr_texts:
            combined_text = content_text + "\n\n" + "\n\n".join(ocr_texts)
        else:
            combined_text = content_text
            
        return combined_text
        
    def preprocess_thread(self, thread_data):
        """Tiền xử lý một thread cụ thể"""
        if not thread_data or 'posts' not in thread_data:
            return None
            
        # Tạo bản sao để không ảnh hưởng đến dữ liệu gốc
        preprocessed_thread = {
            'thread_id': thread_data.get('thread_id', ''),
            'title': self.clean_text(thread_data.get('title', '')),
            'url': thread_data.get('url', ''),
            'crawl_date': thread_data.get('crawl_date', ''),
            'posts': []
        }
        
        # Xử lý từng bài viết
        for post in thread_data.get('posts', []):
            # Kết hợp nội dung text và OCR
            combined_text = self.combine_text_and_ocr(post)
            
            # Làm sạch văn bản
            cleaned_text = self.clean_text(combined_text)
            
            # Chuẩn hóa định dạng giá tiền
            normalized_price_text = self.normalize_price_format(cleaned_text)
            
            # Chuẩn hóa tên linh kiện
            normalized_component_text = self.normalize_component_names(normalized_price_text)
            
            # Tạo bài viết đã tiền xử lý
            preprocessed_post = {
                'post_id': post.get('post_id', ''),
                'author': post.get('author', {}),
                'created_date': post.get('created_date', ''),
                'original_content': post.get('content_text', ''),
                'preprocessed_content': normalized_component_text,
                'quotes': post.get('quotes', []),
                'reactions': post.get('reactions', {})
            }
            
            preprocessed_thread['posts'].append(preprocessed_post)
            
        return preprocessed_thread
        
    def preprocess_all_threads(self):
        """Tiền xử lý tất cả các threads đã tải"""
        if not self.threads_data:
            self.load_thread_files()
            
        self.preprocessed_data = []
        
        for i, thread_data in enumerate(self.threads_data):
            try:
                logger.info(f"Đang tiền xử lý thread {i+1}/{len(self.threads_data)}: {thread_data.get('thread_id', '')}")
                
                # Tiền xử lý thread
                preprocessed_thread = self.preprocess_thread(thread_data)
                
                if preprocessed_thread:
                    self.preprocessed_data.append(preprocessed_thread)
                    
                # Log tiến độ
                if (i + 1) % 10 == 0 or i == len(self.threads_data) - 1:
                    logger.info(f"Đã tiền xử lý {i+1}/{len(self.threads_data)} threads")
                    
            except Exception as e:
                logger.error(f"Lỗi khi tiền xử lý thread {thread_data.get('thread_id', '')}: {str(e)}")
                continue
                
        logger.info(f"Đã tiền xử lý xong {len(self.preprocessed_data)}/{len(self.threads_data)} threads")
        return self.preprocessed_data
        
    def save_preprocessed_data(self, all_in_one=True):
        """Lưu dữ liệu đã tiền xử lý"""
        if not self.preprocessed_data:
            logger.warning("Không có dữ liệu tiền xử lý để lưu")
            return False
            
        try:
            # Tạo thư mục nếu chưa tồn tại
            PREPROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            if all_in_one:
                # Lưu tất cả vào một file
                output_file = PREPROCESSED_DATA_DIR / "all_preprocessed_threads.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.preprocessed_data, f, ensure_ascii=False, indent=2)
                logger.info(f"Đã lưu tất cả dữ liệu tiền xử lý vào {output_file}")
            else:
                # Lưu riêng từng thread
                for thread in self.preprocessed_data:
                    thread_id = thread.get('thread_id', '')
                    output_file = PREPROCESSED_DATA_DIR / f"preprocessed_thread_{thread_id}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(thread, f, ensure_ascii=False, indent=2)
                logger.info(f"Đã lưu {len(self.preprocessed_data)} files dữ liệu tiền xử lý vào {PREPROCESSED_DATA_DIR}")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu tiền xử lý: {str(e)}")
            return False
            
    def run_preprocessing(self):
        """Chạy toàn bộ quá trình tiền xử lý"""
        self.load_thread_files()
        self.preprocess_all_threads()
        self.save_preprocessed_data()
        
        return self.preprocessed_data


if __name__ == "__main__":
    # Chạy tiền xử lý dữ liệu
    preprocessor = DataPreprocessor()
    preprocessor.run_preprocessing()