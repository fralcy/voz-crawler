import os
import json
import logging
from pathlib import Path
from bs4 import BeautifulSoup
import time
import re
from selenium.common.exceptions import TimeoutException

from browser import Browser
from config import THREAD_CACHE_DIR, VOZ_BASE_URL

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ThreadCrawler:
    """
    Class để crawl một thread cụ thể từ VOZ, hỗ trợ phân trang và cache
    """
    def __init__(self):
        self.browser = Browser()
        
    def get_thread(self, thread_url, use_cache=True, max_pages=None):
        """
        Lấy dữ liệu của một thread cụ thể, hỗ trợ phân trang
        
        Args:
            thread_url (str): URL của thread cần crawl
            use_cache (bool): Sử dụng cache nếu có
            max_pages (int, optional): Số trang tối đa cần crawl, None để crawl tất cả
            
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
                    thread_data = json.load(f)
                    # Kiểm tra xem cache có đầy đủ không (có thể đã crawl một phần trước đó)
                    if max_pages is None or len(thread_data.get('pages', [])) >= max_pages:
                        return thread_data
                    # Nếu cache không đầy đủ, tiếp tục crawl từ trang cuối
                    logger.info(f"Cache không đầy đủ, tiếp tục crawl từ trang {len(thread_data.get('pages', []))+1}")
            except Exception as e:
                logger.error(f"Lỗi khi đọc cache: {str(e)}")
                # Tiếp tục crawl nếu cache lỗi
        
        # Crawl thread
        thread_data = self._crawl_thread(thread_url, thread_id, max_pages)
        if thread_data:
            # Lưu vào cache
            self._save_cache(thread_data, cache_file)
            
        return thread_data
    
    def _extract_thread_id(self, thread_url):
        """Trích xuất thread ID từ URL"""
        match = re.search(r'\.(\d+)/?', thread_url)
        return match.group(1) if match else None
    
    def _crawl_thread(self, thread_url, thread_id, max_pages=None):
        """
        Crawl một thread cụ thể với hỗ trợ phân trang
        
        Args:
            thread_url (str): URL của thread
            thread_id (str): ID của thread
            max_pages (int, optional): Số trang tối đa cần crawl, None để crawl tất cả
            
        Returns:
            dict: Dữ liệu của thread
        """
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
            
            # Kiểm tra số trang
            current_page = 1
            total_pages = 1
            
            # Tìm phân trang
            pagination = soup.select_one('.pagination')
            if pagination:
                # Tìm trang hiện tại
                current_page_element = pagination.select_one('.pagination-current')
                if current_page_element:
                    current_page = int(current_page_element.text.strip())
                
                # Tìm tổng số trang
                page_elements = pagination.select('li a')
                if page_elements:
                    try:
                        # Lấy số trang từ phần tử cuối cùng
                        last_page = page_elements[-1].text.strip()
                        if last_page.isdigit():
                            total_pages = int(last_page)
                    except:
                        # Nếu có lỗi, dùng cách khác để tìm tổng số trang
                        for el in page_elements:
                            try:
                                page_num = int(el.text.strip())
                                total_pages = max(total_pages, page_num)
                            except:
                                pass
            
            logger.info(f"Thread {thread_id} có {total_pages} trang")
            
            # Giới hạn số trang nếu cần
            if max_pages is not None:
                total_pages = min(total_pages, max_pages)
                logger.info(f"Giới hạn crawl {total_pages} trang")
            
            # Crawl từng trang
            thread_data = {
                "thread_id": thread_id,
                "title": thread_title,
                "url": thread_url,
                "crawl_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_pages": total_pages,
                "pages": []
            }
            
            # Crawl trang đầu tiên (đã load rồi)
            page_data = {
                "page_number": current_page,
                "posts": self._parse_posts(soup)
            }
            thread_data["pages"].append(page_data)
            logger.info(f"Đã crawl trang {current_page}/{total_pages}")
            
            # Crawl các trang tiếp theo
            for page_num in range(2, total_pages + 1):
                # Tạo URL cho trang tiếp theo
                next_page_url = f"{thread_url}page-{page_num}"
                
                # Crawl trang tiếp theo
                page_data = self._crawl_page(next_page_url, page_num)
                if page_data:
                    thread_data["pages"].append(page_data)
                    logger.info(f"Đã crawl trang {page_num}/{total_pages}")
                else:
                    logger.error(f"Không thể crawl trang {page_num}")
                    break
            
            # Tạo danh sách tất cả các posts từ tất cả các trang
            all_posts = []
            for page in thread_data["pages"]:
                all_posts.extend(page["posts"])
            
            # Thêm danh sách posts vào thread_data để tiện sử dụng
            thread_data["posts"] = all_posts
            thread_data["post_count"] = len(all_posts)
            
            return thread_data
            
        except Exception as e:
            logger.error(f"Lỗi khi crawl thread {thread_url}: {str(e)}")
            return None
    
    def _crawl_page(self, page_url, page_num):
        """Crawl một trang cụ thể của thread"""
        try:
            # Truy cập vào trang
            if not self.browser.get(page_url):
                return None
                
            # Đợi cho phần tử body xuất hiện để đảm bảo trang đã tải
            if not self.browser.wait_for_element('.message-body'):
                logger.error(f"Không thể tải trang: {page_url}")
                return None
                
            # Lấy HTML của trang
            page_source = self.browser.get_page_source()
            
            # Parse HTML
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Parse các posts
            posts = self._parse_posts(soup)
            
            # Tạo dữ liệu trang
            page_data = {
                "page_number": page_num,
                "posts": posts
            }
            
            return page_data
            
        except Exception as e:
            logger.error(f"Lỗi khi crawl trang {page_url}: {str(e)}")
            return None
            
    def _parse_posts(self, soup):
        """Parse các bài viết từ HTML"""
        posts = []
        
        # Lấy tất cả các bài đăng
        post_elements = soup.select('.block-body article.message')
        
        for i, element in enumerate(post_elements):
            try:
                # Lấy ID bài viết
                post_id = None
                if 'data-content' in element.attrs:
                    content_attr = element['data-content']
                    if content_attr.startswith('post-'):
                        post_id = content_attr.replace('post-', '')
                
                # Lấy thông tin người đăng
                username_element = element.select_one('.message-userDetails .username')
                username = username_element.text.strip() if username_element else "Unknown"
                
                # Lấy user ID nếu có
                user_id = None
                if username_element and 'data-user-id' in username_element.attrs:
                    user_id = username_element['data-user-id']
                
                # Lấy thời gian đăng
                time_element = element.select_one('.message-attribution-main time')
                created_date = time_element.get('datetime', '') if time_element else ""
                
                # Lấy thời gian chỉnh sửa nếu có
                modified_date = None
                edited_element = element.select_one('.message-lastEdit time')
                if edited_element:
                    modified_date = edited_element.get('datetime', '')
                
                # Lấy nội dung bài viết
                content_element = element.select_one('.message-body .bbWrapper')
                content = content_element.text.strip() if content_element else ""
                
                # Lấy các trích dẫn
                quotes = []
                quote_elements = element.select('.bbCodeBlock--quote')
                for quote_el in quote_elements:
                    quote_author = None
                    quote_content = None
                    
                    # Lấy người được trích dẫn
                    author_el = quote_el.select_one('.bbCodeBlock-sourceJump')
                    if author_el:
                        quote_author = author_el.text.strip()
                    
                    # Lấy nội dung trích dẫn
                    content_el = quote_el.select_one('.bbCodeBlock-content')
                    if content_el:
                        quote_content = content_el.text.strip()
                    
                    if quote_author or quote_content:
                        quotes.append({
                            "author": quote_author,
                            "content": quote_content
                        })
                
                # Lấy URL ảnh
                image_elements = element.select('.message-body .bbWrapper img')
                images = []
                for img in image_elements:
                    img_url = img.get('src', '')
                    if img_url:
                        # Xử lý URL tương đối
                        if img_url.startswith('/'):
                            img_url = f"{VOZ_BASE_URL}{img_url}"
                            
                        images.append({
                            "url": img_url,
                            "ocr_text": None  # Sẽ xử lý OCR sau
                        })
                
                # Lấy thông tin reaction
                reactions = {}
                reaction_elements = element.select('.reactionsBar-link')
                for reaction_el in reaction_elements:
                    try:
                        reaction_text = reaction_el.text.strip()
                        if 'x' in reaction_text:
                            parts = reaction_text.split('x')
                            reaction_type = parts[0].strip()
                            reaction_count = int(parts[1].strip())
                            reactions[reaction_type] = reaction_count
                    except:
                        pass
                
                # Tạo đối tượng post
                post_data = {
                    "post_id": post_id,
                    "author": {
                        "username": username,
                        "user_id": user_id
                    },
                    "created_date": created_date,
                    "modified_date": modified_date,
                    "content_text": content,
                    "quotes": quotes,
                    "images": images,
                    "reactions": reactions
                }
                
                posts.append(post_data)
                
            except Exception as e:
                logger.error(f"Lỗi khi parse bài viết: {str(e)}")
                continue
                
        return posts
        
    def _save_cache(self, thread_data, cache_file):
        """Lưu dữ liệu thread vào cache"""
        try:
            # Tạo thư mục cha nếu chưa tồn tại
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
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

    def __del__(self):
        """Đảm bảo trình duyệt được đóng khi đối tượng bị hủy"""
        self.close()


if __name__ == "__main__":
    # Test crawl một thread cụ thể
    test_url = "https://voz.vn/t/ngan-sach-15tr-ca-man-choi-game-lien-minh-tac-vu-co-ban-cpu-co-card-onboard-vga-nang-cap-sau.1097752/"
    
    crawler = ThreadCrawler()
    try:
        # Chỉ crawl tối đa 2 trang để test
        thread_data = crawler.get_thread(test_url, use_cache=False, max_pages=2)
        if thread_data:
            print(f"Đã crawl thread: {thread_data['title']}")
            print(f"Số lượng bài viết: {thread_data['post_count']}")
    finally:
        crawler.close()