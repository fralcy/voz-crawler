# simple_test.py
import undetected_chromedriver as uc
import time

def test_browser():
    """Kiểm tra undetected-chromedriver"""
    print("Bắt đầu test trình duyệt...")
    
    try:
        # Khởi tạo trình duyệt
        print("Đang khởi tạo trình duyệt...")
        options = uc.ChromeOptions()
        options.headless = True
        driver = uc.Chrome(options=options)
        
        # Truy cập trang web
        print("Đang truy cập Google...")
        driver.get("https://www.google.com")
        
        # Lấy tiêu đề trang
        title = driver.title
        print(f"Tiêu đề trang: {title}")
        
        # Đóng trình duyệt
        driver.quit()
        print("Đã đóng trình duyệt")
        print("Test thành công!")
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    test_browser()