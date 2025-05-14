import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import json
import os
from pathlib import Path
import logging

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Tạo thư mục cho dữ liệu
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

def test_single_thread():
    """Thử nghiệm crawl một thread đơn"""
    # URL thread mẫu
    test_thread_url = "https://voz.vn/t/ngan-sach-15tr-ca-man-choi-game-lien-minh-tac-vu-co-ban-cpu-co-card-onboard-vga-nang-cap-sau.1097752/"
    
    try:
        # Khởi tạo trình duyệt
        logger.info("Đang khởi tạo trình duyệt...")
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Thêm user-agent để tránh phát hiện
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36')
        
        driver = uc.Chrome(options=options)
        
        # Truy cập thread
        logger.info(f"Đang truy cập: {test_thread_url}")
        driver.get(test_thread_url)
        
        # Đợi để đảm bảo trang đã tải
        logger.info("Đang đợi trang tải...")
        time.sleep(3)
        
        # Lấy HTML của trang
        logger.info("Đang phân tích HTML...")
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Lấy tiêu đề thread
        title_element = soup.select_one(".p-title-value")
        thread_title = title_element.text.strip() if title_element else "Không tìm thấy tiêu đề"
        logger.info(f"Tiêu đề thread: {thread_title}")
        
        # Parse các bài viết
        posts_data = []
        post_elements = soup.select(".block-body article.message")
        logger.info(f"Tìm thấy {len(post_elements)} bài viết")
        
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
                username_element = element.select_one(".message-userDetails .username")
                username = username_element.text.strip() if username_element else "Unknown"
                
                # Lấy thời gian đăng
                time_element = element.select_one(".message-attribution-main time")
                created_date = time_element.get('datetime', '') if time_element else ""
                
                # Lấy nội dung bài viết
                content_element = element.select_one(".message-body .bbWrapper")
                content = content_element.text.strip() if content_element else ""
                
                # Lấy URL ảnh
                image_elements = element.select(".message-body .bbWrapper img")
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
                    "content_text": content[:200] + "..." if len(content) > 200 else content,  # Lưu trích đoạn
                    "content_length": len(content),
                    "images": images
                }
                
                posts_data.append(post_data)
                
                # Log thông tin về bài đầu tiên và một số bài khác
                if i < 3 or i == len(post_elements) - 1:
                    logger.info(f"Đã parse bài viết #{i+1} của {username}")
                elif i == 3:
                    logger.info(f"... và {len(post_elements) - 4} bài viết khác ...")
                
            except Exception as e:
                logger.error(f"Lỗi khi parse bài viết #{i+1}: {str(e)}")
                continue
        
        # Tạo dữ liệu thread
        thread_data = {
            "thread_id": test_thread_url.split('.')[-2].split('/')[-1],
            "title": thread_title,
            "url": test_thread_url,
            "crawl_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "post_count": len(posts_data),
            "posts": posts_data
        }
        
        # Lưu kết quả vào file JSON
        output_file = PROCESSED_DATA_DIR / "test_thread.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(thread_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Đã lưu dữ liệu thread vào {output_file}")
        
        # Đóng trình duyệt
        driver.close()
        driver.quit()
        driver = None
        logger.info("Đã đóng trình duyệt")
        
        return True
    
    except Exception as e:
        logger.error(f"Lỗi trong quá trình test: {str(e)}")
        if 'driver' in locals() and driver is not None:
            try:
                driver.quit()
            except:
                pass
        return False

if __name__ == "__main__":
    test_single_thread()