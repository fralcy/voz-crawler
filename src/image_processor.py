import os
import logging
import time
import requests
from pathlib import Path
import easyocr
import re
import json
import hashlib
from PIL import Image
from io import BytesIO

from config import IMAGE_CACHE_DIR

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    Class để xử lý OCR cho các hình ảnh từ VOZ
    """
    def __init__(self, lazy_load=True):
        # Tạo thư mục cache nếu chưa tồn tại
        IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        self.reader = None
        self.lazy_load = lazy_load
        
        if not lazy_load:
            self._initialize_ocr()
            
    def _initialize_ocr(self):
        """Khởi tạo EasyOCR khi cần thiết"""
        if self.reader is None:
            # Khởi tạo EasyOCR với ngôn ngữ tiếng Việt và tiếng Anh
            logger.info("Khởi tạo EasyOCR với ngôn ngữ tiếng Việt và tiếng Anh...")
            self.reader = easyocr.Reader(['vi', 'en'], gpu=False)
            logger.info("Đã khởi tạo EasyOCR thành công")
        
    def process_image(self, image_url, use_cache=True):
        """
        Xử lý OCR cho một hình ảnh
        
        Args:
            image_url (str): URL của hình ảnh
            use_cache (bool): Sử dụng cache nếu có
            
        Returns:
            str: Văn bản đã trích xuất từ hình ảnh
        """
        try:
            # Tạo tên file cache từ URL
            url_hash = hashlib.md5(image_url.encode()).hexdigest()
            cache_file = IMAGE_CACHE_DIR / f"{url_hash}.json"
            
            # Kiểm tra cache
            if use_cache and cache_file.exists():
                logger.info(f"Sử dụng cache cho hình ảnh: {image_url}")
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        return cache_data.get('ocr_text', '')
                except Exception as e:
                    logger.error(f"Lỗi khi đọc cache: {str(e)}")
            
            # Khởi tạo OCR nếu cần
            self._initialize_ocr()
            
            # Tải hình ảnh
            logger.info(f"Đang tải hình ảnh: {image_url}")
            response = requests.get(image_url, stream=True, timeout=10)
            # Kiểm tra cả 200 (OK) và 304 (Not Modified) là các status thành công
            if response.status_code not in [200, 304]:
                logger.error(f"Không thể tải hình ảnh, mã trạng thái: {response.status_code}")
                return None
            
            # Mở hình ảnh bằng PIL
            img = Image.open(BytesIO(response.content))
            
            # Kiểm tra kích thước hình ảnh
            width, height = img.size
            if width < 50 or height < 50:
                logger.info(f"Hình ảnh quá nhỏ ({width}x{height}), bỏ qua OCR")
                # Lưu thông tin vào cache để không phải tải lại
                cache_data = {
                    'image_url': image_url,
                    'ocr_date': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    'ocr_text': '',
                    'reason': 'image_too_small'
                }
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                return ""
                
            # Kiểm tra nếu là avatar hoặc icon (thường là hình vuông nhỏ)
            if width < 100 and height < 100 and abs(width - height) < 10:
                logger.info(f"Hình ảnh có thể là avatar/icon ({width}x{height}), bỏ qua OCR")
                # Lưu thông tin vào cache để không phải tải lại
                cache_data = {
                    'image_url': image_url,
                    'ocr_date': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    'ocr_text': '',
                    'reason': 'likely_avatar'
                }
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                return ""
            
            # Resize hình ảnh nếu quá lớn để tăng tốc OCR
            max_dimension = 1600
            if width > max_dimension or height > max_dimension:
                scale = max_dimension / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Đã resize hình ảnh từ {width}x{height} xuống {new_width}x{new_height}")
            
            # Xử lý OCR
            try:
                logger.info(f"Đang xử lý OCR cho hình ảnh...")
                result = self.reader.readtext(
                    numpy_image=self._pil_to_numpy(img),
                    detail=0  # Chỉ trả về văn bản, không có bounding box
                )
                
                # Ghép các đoạn văn bản
                ocr_text = "\n".join(result)
                
                # Lưu kết quả vào cache
                cache_data = {
                    'image_url': image_url,
                    'ocr_date': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    'ocr_text': ocr_text,
                    'image_size': {'width': width, 'height': height}
                }
                
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Đã xử lý OCR và lưu cache cho hình ảnh: {len(ocr_text)} ký tự")
                return ocr_text
            except Exception as e:
                logger.error(f"Lỗi khi xử lý OCR: {str(e)}")
                # Lưu lỗi vào cache để không thử lại liên tục
                cache_data = {
                    'image_url': image_url,
                    'ocr_date': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    'ocr_text': '',
                    'error': str(e)
                }
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                return None
                
        except Exception as e:
            logger.error(f"Lỗi khi xử lý OCR cho hình ảnh {image_url}: {str(e)}")
            return None
    
    def _pil_to_numpy(self, pil_image):
        """Chuyển đổi hình ảnh PIL sang numpy array để EasyOCR có thể xử lý"""
        import numpy as np
        return np.array(pil_image)
    
    def process_thread_images(self, thread_data, max_retries=3):
        """
        Xử lý OCR cho tất cả hình ảnh trong một thread
        
        Args:
            thread_data (dict): Dữ liệu thread
            max_retries (int): Số lần thử lại tối đa cho mỗi hình ảnh
            
        Returns:
            dict: Dữ liệu thread đã cập nhật với kết quả OCR
        """
        if not thread_data or 'posts' not in thread_data:
            logger.error("Dữ liệu thread không hợp lệ")
            return thread_data
        
        total_images = 0
        processed_images = 0
        
        # Đếm tổng số hình ảnh
        for post in thread_data['posts']:
            total_images += len(post.get('images', []))
        
        logger.info(f"Bắt đầu xử lý OCR cho {total_images} hình ảnh trong thread {thread_data['thread_id']}")
        
        # Nếu không có hình ảnh, trả về luôn
        if total_images == 0:
            logger.info(f"Không có hình ảnh nào trong thread {thread_data['thread_id']}")
            return thread_data
            
        # Khởi tạo OCR nếu cần
        self._initialize_ocr()
        
        # Các biến thống kê
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        # Xử lý OCR cho từng bài viết
        for post in thread_data['posts']:
            if 'images' not in post or not post['images']:
                continue
                
            for image in post['images']:
                if 'url' not in image or not image['url']:
                    continue
                    
                # Xử lý OCR với số lần thử lại
                ocr_text = self.process_image(image['url'], max_retries=max_retries)
                image['ocr_text'] = ocr_text
                
                # Cập nhật thống kê
                processed_images += 1
                if ocr_text is None:
                    failed_count += 1
                elif ocr_text == "":
                    skipped_count += 1
                else:
                    success_count += 1
                
                # Log tiến độ
                if processed_images % 5 == 0 or processed_images == total_images:
                    logger.info(f"Đã xử lý {processed_images}/{total_images} hình ảnh")
        
        # Log kết quả
        logger.info(f"Đã hoàn thành xử lý OCR cho {processed_images} hình ảnh trong thread {thread_data['thread_id']}")
        logger.info(f"Thành công: {success_count}, Bỏ qua: {skipped_count}, Thất bại: {failed_count}")
        
        return thread_data


if __name__ == "__main__":
    # Test xử lý OCR cho một hình ảnh
    test_image_url = "https://i.imgur.com/example.jpg"  # Thay thế bằng URL thật
    
    processor = ImageProcessor()
    ocr_text = processor.process_image(test_image_url)
    
    if ocr_text:
        print(f"Kết quả OCR:\n{ocr_text}")
    else:
        print("Không thể xử lý OCR cho hình ảnh")