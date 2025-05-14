import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging

from config import HEADLESS_BROWSER, REQUEST_DELAY

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Browser:
    """
    Class quản lý trình duyệt Selenium và thao tác cơ bản
    """
    def __init__(self):
        self.driver = None
        self.setup_browser()
        
    def setup_browser(self):
        """Khởi tạo trình duyệt Chrome với Selenium"""
        chrome_options = Options()
        
        # Cấu hình headless mode nếu được chỉ định
        if HEADLESS_BROWSER:
            chrome_options.add_argument("--headless")
            
        # Các cấu hình khác
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Thêm User-Agent giống người dùng thật
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        # Khởi tạo WebDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Đã khởi tạo trình duyệt Chrome")
        
    def get(self, url):
        """Truy cập một URL với delay ngẫu nhiên"""
        try:
            logger.info(f"Đang truy cập: {url}")
            self.driver.get(url)
            
            # Delay ngẫu nhiên để giống hành vi người dùng thật
            delay = REQUEST_DELAY + random.uniform(0, 1)
            time.sleep(delay)
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi truy cập {url}: {str(e)}")
            return False
    
    def wait_for_element(self, selector, by=By.CSS_SELECTOR, timeout=10):
        """Đợi cho đến khi một phần tử xuất hiện trên trang"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except Exception as e:
            logger.error(f"Không tìm thấy phần tử {selector} sau {timeout} giây: {str(e)}")
            return None
    
    def wait_for_elements(self, selector, by=By.CSS_SELECTOR, timeout=10):
        """Đợi cho đến khi các phần tử xuất hiện trên trang"""
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((by, selector))
            )
            return elements
        except Exception as e:
            logger.error(f"Không tìm thấy phần tử {selector} sau {timeout} giây: {str(e)}")
            return []
            
    def get_page_source(self):
        """Lấy mã nguồn HTML của trang hiện tại"""
        return self.driver.page_source
        
    def close(self):
        """Đóng trình duyệt"""
        if self.driver:
            self.driver.quit()
            logger.info("Đã đóng trình duyệt")
            
    def __del__(self):
        """Đảm bảo trình duyệt được đóng khi đối tượng bị hủy"""
        self.close()