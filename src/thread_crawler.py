import os
import json
import logging
from pathlib import Path
from bs4 import BeautifulSoup
import time
from selenium.common.exceptions import TimeoutException

from browser import Browser
from config import THREAD_CACHE_DIR

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ThreadCrawler:
    """
    Class để crawl một thread cụ thể từ VOZ
    """
    def __init__(self):
        self.browser = Browser()
        
    def get_thread(self, thread_url, use_cache=True):
        """
        Lấy dữ liệu của một thread cụ thể
        
        Args:
            thread_url (str): URL của thread cần crawl
            use_cache (bool): Sử dụng cache nếu có
            
        Returns:
            dict: Dữ liệu của thread
        """
        # Trích xuất thread_id từ URL
        thread_id = self._extract_thread_id(thread_url)
        if not thread_id:
            logger.error(f"Không thể trích xuất thread ID từ URL: {thread_url}")
            return None
            
        # Kiểm tra cache
        cache_file = THREAD_CACHE_DIR / f"{thread_id}.json"
        if use_cache and cache_file.exists():
            logger.info(f"Sử dụng cache cho thread {thread_id}")
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Lỗi khi đọc cache: {str(e)}")
                # Tiếp tục crawl nếu cache lỗi
        
        # Crawl thread
        thread_data = self._crawl_thread(thread_url, thread_id)
        if thread_data:
            # Lưu vào cache
            self._save_cache(thread_data, cache_file)
            
        return thread_data
    
    def _extract_thread_id(self, thread_url):
        """Trích xuất thread ID từ URL"""
        import re
        match = re.search(r'\.(\d+)/?', thread_url)
        return match.group(1) if match else None
    
    def _crawl_thread(self, thread_url, thread_id):
        """Crawl một thread cụ thể"""
        try:
            # Truy cập vào thread
            if not self.browser.get(thread_url):
                return None
                
            # Đợi cho phần tử body xuất hiện để đảm bảo trang đã tải
            if not self.browser.wait_for_element('.message-body'):
                logger.error(f"Không thể tải thread: {thread_url}")
                return None
                
            # Lấy HTML của trang
            page_source = self.browser.get_page_source()
            
            # Parse HTML
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Lấy tiêu đề thread
            title_element = soup.select_one('.p-title-value')
            thread_title = title_element.text.strip() if title_element else ""
            
            # Lấy các post
            posts_data = self._parse_posts(soup)
            
            # Tạo dữ liệu thread
            thread_data = {
                "thread_id": thread_id,
                "title": thread_title,
                "url": thread_url,
                "crawl_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "posts": posts_data
            }
            
            return thread_data
            
        except Exception as e:
            logger.error(f"Lỗi khi crawl thread {thread_url}: {str(e)}")
            return None
            
    def _parse_posts(self, soup):
        """Parse các bài viết từ HTML"""
        posts = []
        
        # Lấy tất cả các bài đăng
        post_elements = soup.select('.block-body article.message')
        
        for i, element in enumerate(post_elements):
            try:
                # Kiểm tra xem có phải là bài đầu tiên không
                is_op = i == 0
                
                # Lấy ID bài viết
                post_id = None
                if 'data-content' in element.attrs:
                    content_attr = element['data-content']
                    if content_attr.startswith('post-'):
                        post_id = content_attr.replace('post-', '')
                
                # Lấy thông tin người đăng
                username_element = element.select_one('.message-userDetails .username')
                username = username_element.text.strip() if username_element else "Unknown"
                
                # Lấy thời gian đăng
                time_element = element.select_one('.message-attribution-main time')
                created_date = time_element.get('datetime', '') if time_element else ""
                
                # Lấy nội dung bài viết
                content_element = element.select_one('.message-body .bbWrapper')
                content = content_element.text.strip() if content_element else ""
                
                # Lấy URL ảnh
                image_elements = element.select('.message-body .bbWrapper img')
                images = []
                for img in image_elements:
                    img_url = img.get('src', '')
                    if img_url:
                        images.append({
                            "url": img_url,
                            "ocr_text": None  # Sẽ xử lý OCR sau
                        })
                
                # Tạo đối tượng post
                post_data = {
                    "post_id": post_id,
                    "post_index": i + 1,
                    "is_op": is_op,
                    "author": username,
                    "created_date": created_date,
                    "content_text": content,
                    "images": images
                }
                
                posts.append(post_data)
                
            except Exception as e:
                logger.error(f"Lỗi khi parse bài viết: {str(e)}")
                continue
                
        return posts
        
    def _save_cache(self, thread_data, cache_file):
        """Lưu dữ liệu thread vào cache"""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(thread_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Đã lưu cache cho thread {thread_data['thread_id']}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cache: {str(e)}")
            return False
            
    def close(self):
        """Đóng trình duyệt"""
        if self.browser:
            self.browser.close()