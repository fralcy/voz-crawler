import logging
import json
import time
from bs4 import BeautifulSoup
from pathlib import Path

from browser import Browser
from config import VOZ_BOX_URL, THREAD_LIMIT, DATA_DIR, RAW_DATA_DIR

# Cấu hình logging
logger = logging.getLogger(__name__)

class BoxCrawler:
    """
    Class để crawl danh sách thread từ box "Tư vấn cấu hình"
    """
    def __init__(self, box_url=VOZ_BOX_URL):
        self.box_url = box_url
        self.browser = Browser()
        self.threads = []
        self.page_count = 0
        self.sticky_threads = []  # Thêm biến lưu danh sách thread sticky
        
    def crawl_threads_list(self, thread_limit=THREAD_LIMIT, include_sticky=False):
        """
        Crawl danh sách thread từ box
        
        Args:
            thread_limit (int): Số lượng thread tối đa cần crawl
            include_sticky (bool): Có bao gồm thread ghim không
            
        Returns:
            list: Danh sách thread đã crawl được
        """
        logger.info(f"Bắt đầu crawl danh sách thread từ box: {self.box_url}")
        logger.info(f"Giới hạn số lượng thread: {thread_limit}")
        
        self.threads = []
        self.sticky_threads = []
        self.page_count = 0
        
        next_page_url = self.box_url
        
        # Crawl từng trang cho đến khi đạt giới hạn số lượng thread
        while next_page_url and len(self.threads) < thread_limit:
            # Truy cập trang hiện tại
            if not self.browser.get(next_page_url):
                break
                
            # Đợi cho phần tử container xuất hiện
            if not self.browser.wait_for_element('.structItemContainer'):
                logger.error(f"Không thể tải trang: {next_page_url}")
                break
                
            # Lấy HTML của trang
            page_source = self.browser.get_page_source()
            
            # Parse HTML
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Parse danh sách thread
            new_threads, page_sticky_threads = self._parse_threads_on_page(soup)
            
            # Lưu thread sticky riêng (chỉ ở trang đầu tiên)
            if self.page_count == 0:
                self.sticky_threads = page_sticky_threads
                if include_sticky:
                    # Nếu include_sticky=True, thêm thread sticky vào danh sách threads
                    self.threads.extend(page_sticky_threads)
                
            # Thêm các thread thường vào danh sách đã crawl
            self.threads.extend(new_threads)
            
            logger.info(f"Đã crawl {len(new_threads)} thread thường từ trang {self.page_count + 1}")
            if self.page_count == 0:
                logger.info(f"Đã tìm thấy {len(page_sticky_threads)} thread ghim")
            logger.info(f"Tổng số thread đã crawl: {len(self.threads)}")
            
            # Tìm URL của trang tiếp theo
            next_page_url = self._find_next_page_url(soup)
            self.page_count += 1
            
            # Kiểm tra giới hạn
            if len(self.threads) >= thread_limit:
                logger.info(f"Đã đạt giới hạn {thread_limit} thread, dừng crawl.")
                self.threads = self.threads[:thread_limit]
                break
                
        logger.info(f"Đã hoàn thành crawl {len(self.threads)} thread từ {self.page_count} trang")
        
        # Nếu không bao gồm thread sticky trong danh sách threads nhưng cần lưu lại
        if not include_sticky:
            logger.info(f"Đã tách riêng {len(self.sticky_threads)} thread sticky (không bao gồm trong giới hạn {thread_limit})")
            
        return self.threads
        
    def _parse_threads_on_page(self, soup):
        """Parse danh sách thread từ HTML của một trang"""
        normal_threads = []
        sticky_threads = []
        
        # Lấy tất cả các phần tử thread
        thread_elements = soup.select('.structItem.structItem--thread')
        
        for element in thread_elements:
            try:
                # Xác định xem có phải thread ghim không
                is_sticky = 'is-sticky' in element.get('class', [])
                
                # Lấy tiêu đề và URL
                title_element = element.select_one('.structItem-title a')
                if not title_element:
                    continue
                    
                title = title_element.text.strip()
                url = title_element.get('href', '')
                
                # Xây dựng URL đầy đủ nếu là URL tương đối
                if url.startswith('/'):
                    from config import VOZ_BASE_URL
                    url = f"{VOZ_BASE_URL}{url}"
                    
                # Lấy thread ID từ URL
                thread_id = self._extract_thread_id(url)
                
                # Lấy thông tin tác giả
                author_element = element.select_one('.structItem-parts .username')
                author = author_element.text.strip() if author_element else "Unknown"
                
                # Lấy thời gian tạo
                time_element = element.select_one('.structItem-startDate time')
                created_date = time_element.get('datetime', '') if time_element else ""
                
                # Lấy số lượt trả lời và xem
                reply_count = 0
                view_count = 0
                
                reply_element = element.select_one('.structItem-cell--meta dd')
                if reply_element:
                    reply_count = int(reply_element.text.strip().replace(',', '')) if reply_element.text.strip() else 0
                    
                view_element = element.select_one('.structItem-cell--meta dd:nth-of-type(2)')
                if view_element:
                    view_count = int(view_element.text.strip().replace(',', '').replace('K', '000')) if view_element.text.strip() else 0
                
                # Tạo đối tượng thread
                thread_data = {
                    "thread_id": thread_id,
                    "title": title,
                    "url": url,
                    "author": author,
                    "created_date": created_date,
                    "reply_count": reply_count,
                    "view_count": view_count,
                    "is_sticky": is_sticky
                }
                
                # Phân loại thread vào danh sách tương ứng
                if is_sticky:
                    sticky_threads.append(thread_data)
                else:
                    normal_threads.append(thread_data)
                
            except Exception as e:
                logger.error(f"Lỗi khi parse thread: {str(e)}")
                continue
                
        return normal_threads, sticky_threads
        
    def _extract_thread_id(self, thread_url):
        """Trích xuất thread ID từ URL"""
        import re
        match = re.search(r'\.(\d+)/?', thread_url)
        return match.group(1) if match else None
        
    def _find_next_page_url(self, soup):
        """Tìm URL của trang tiếp theo"""
        next_page_element = soup.select_one('.pageNav-jump--next')
        if next_page_element and 'href' in next_page_element.attrs:
            next_url = next_page_element['href']
            # Xây dựng URL đầy đủ nếu là URL tương đối
            if next_url.startswith('/'):
                from config import VOZ_BASE_URL
                next_url = f"{VOZ_BASE_URL}{next_url}"
            return next_url
        return None
        
    def save_threads_list(self, filename="threads_list.json", save_sticky=True):
        """Lưu danh sách thread vào file JSON"""
        if not self.threads:
            logger.warning("Không có thread thường nào để lưu")
            return False
            
        # Tạo thư mục nếu chưa tồn tại
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Tạo đối tượng dữ liệu
        data = {
            "box_url": self.box_url,
            "crawl_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "thread_count": len(self.threads),
            "sticky_thread_count": len(self.sticky_threads),
            "page_count": self.page_count,
            "threads": self.threads
        }
        
        # Thêm danh sách thread sticky nếu cần
        if save_sticky:
            data["sticky_threads"] = self.sticky_threads
        
        # Lưu vào file
        output_file = RAW_DATA_DIR / filename
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Đã lưu danh sách {len(self.threads)} thread vào {output_file}")
            if save_sticky:
                logger.info(f"Đã lưu thêm {len(self.sticky_threads)} thread sticky vào {output_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu danh sách thread: {str(e)}")
            return False
            
    def close(self):
        """Đóng trình duyệt"""
        if self.browser:
            self.browser.close()
            
    def __del__(self):
        """Đảm bảo trình duyệt được đóng khi đối tượng bị hủy"""
        self.close()


if __name__ == "__main__":
    # Test crawl danh sách thread
    crawler = BoxCrawler()
    try:
        # Chỉ crawl 10 thread để test, không bao gồm thread sticky
        threads = crawler.crawl_threads_list(thread_limit=10, include_sticky=False)
        crawler.save_threads_list("test_threads_list.json")
    finally:
        crawler.close()