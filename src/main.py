import os
import json
import logging
import time
import argparse
from pathlib import Path
import concurrent.futures
from tqdm import tqdm
import sys
import traceback

from config import VOZ_BOX_URL, THREAD_LIMIT, RAW_DATA_DIR, PROCESSED_DATA_DIR
from box_crawler import BoxCrawler
from thread_crawler import ThreadCrawler
from image_processor import ImageProcessor

# Tạo thư mục logs nếu chưa tồn tại
Path('logs').mkdir(exist_ok=True)

# Cấu hình logging - FIXED để tránh log duplicate
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Xóa tất cả handlers cũ (nếu có) để tránh duplicate
if logger.hasHandlers():
    logger.handlers.clear()

# Tạo file handler
file_handler = logging.FileHandler('logs/crawl.log')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Tạo console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Cấu hình logging root
root_logger = logging.getLogger('')
root_logger.setLevel(logging.INFO)
if root_logger.hasHandlers():
    root_logger.handlers.clear()
root_logger.addHandler(logging.FileHandler('logs/crawl.log'))
root_logger.addHandler(logging.StreamHandler())

def crawl_box(box_url, thread_limit, filename="threads_list.json", include_sticky=False):
    """Crawl danh sách thread từ box"""
    logger.info(f"Bắt đầu crawl danh sách thread từ box: {box_url}")
    logger.info(f"Giới hạn số lượng thread: {thread_limit}")
    logger.info(f"Bao gồm thread sticky: {include_sticky}")
    
    # Khởi tạo box crawler
    crawler = None
    
    try:
        crawler = BoxCrawler(box_url)
        
        # Crawl danh sách thread, không bao gồm thread sticky theo mặc định
        threads = crawler.crawl_threads_list(thread_limit, include_sticky=include_sticky)
        
        # Lưu danh sách thread (vẫn lưu thông tin thread sticky vào file để tham khảo sau này)
        crawler.save_threads_list(filename, save_sticky=True)
        
        return threads
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"Lỗi khi crawl box: {str(e)}\n{error_msg}")
        return []
    finally:
        # Đảm bảo trình duyệt được đóng
        if crawler:
            crawler.close()

def load_threads_list(filename="threads_list.json"):
    """Load danh sách thread từ file JSON"""
    file_path = RAW_DATA_DIR / filename
    
    if not file_path.exists():
        logger.error(f"File không tồn tại: {file_path}")
        return []
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('threads', [])
    except Exception as e:
        logger.error(f"Lỗi khi đọc file {file_path}: {str(e)}")
        return []

def save_checkpoint(current_index, threads_list, filename="checkpoint.json"):
    """Lưu checkpoint để có thể tiếp tục crawl sau này"""
    checkpoint_file = Path("checkpoint.json")
    
    try:
        checkpoint_data = {
            'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'current_index': current_index,
            'total_threads': len(threads_list),
            'remaining_threads': len(threads_list) - current_index
        }
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Đã lưu checkpoint tại index {current_index}/{len(threads_list)}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu checkpoint: {str(e)}")
        return False

def load_checkpoint(filename="checkpoint.json"):
    """Load checkpoint để tiếp tục crawl"""
    checkpoint_file = Path(filename)
    
    if not checkpoint_file.exists():
        return None
        
    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
            return checkpoint_data.get('current_index', 0)
    except Exception as e:
        logger.error(f"Lỗi khi đọc checkpoint: {str(e)}")
        return None

def crawl_single_thread(thread_info, max_pages=None, use_cache=True, ocr_enabled=True):
    """Crawl một thread cụ thể và xử lý OCR cho các hình ảnh"""
    thread_id = thread_info['thread_id']
    thread_url = thread_info['url']
    
    logger.info(f"Bắt đầu crawl thread {thread_id}: {thread_info['title']}")
    
    # Khởi tạo thread crawler
    thread_crawler = None
    
    try:
        thread_crawler = ThreadCrawler()
        
        # Crawl thread
        thread_data = thread_crawler.get_thread(thread_url, use_cache=use_cache, max_pages=max_pages)
        
        if not thread_data:
            logger.error(f"Không thể crawl thread {thread_id}")
            return None
            
        # Xử lý OCR cho các hình ảnh nếu được yêu cầu
        if ocr_enabled:
            image_processor = ImageProcessor(lazy_load=True)
            thread_data = image_processor.process_thread_images(thread_data)
        
        # Lưu dữ liệu thread
        output_file = PROCESSED_DATA_DIR / f"thread_{thread_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(thread_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Đã lưu dữ liệu thread {thread_id}")
        
        return thread_data
    except KeyboardInterrupt:
        logger.info("Đã nhận tín hiệu ngắt từ người dùng, dừng crawl")
        raise
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"Lỗi khi xử lý thread {thread_id}: {str(e)}\n{error_msg}")
        return None
    finally:
        # Đảm bảo trình duyệt được đóng
        if thread_crawler:
            thread_crawler.close()

def crawl_threads_list(threads_list, max_threads=None, max_pages=None, workers=1, use_cache=True, start_index=0, ocr_enabled=True):
    """Crawl nhiều thread từ danh sách với đa luồng"""
    if not threads_list:
        logger.error("Danh sách thread trống")
        return
        
    # Giới hạn số lượng thread nếu cần
    if max_threads is not None:
        threads_list = threads_list[:max_threads]
        
    # Bắt đầu từ vị trí chỉ định
    if start_index > 0:
        if start_index >= len(threads_list):
            logger.error(f"Chỉ số bắt đầu {start_index} lớn hơn số lượng thread {len(threads_list)}")
            return
            
        logger.info(f"Bắt đầu từ thread thứ {start_index}/{len(threads_list)}")
        threads_list = threads_list[start_index:]
        
    logger.info(f"Bắt đầu crawl {len(threads_list)} thread với {workers} workers")
    logger.info(f"OCR được kích hoạt: {ocr_enabled}")
    
    # Tạo thư mục đầu ra nếu chưa tồn tại
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Crawl các thread
    failed_threads = []
    current_index = start_index
    
    try:
        if workers <= 1:
            # Crawl tuần tự
            for index, thread_info in enumerate(tqdm(threads_list, desc="Crawling threads")):
                try:
                    current_index = start_index + index
                    result = crawl_single_thread(thread_info, max_pages=max_pages, use_cache=use_cache, ocr_enabled=ocr_enabled)
                    if not result:
                        failed_threads.append(thread_info)
                    
                    # Lưu checkpoint sau mỗi 5 thread hoặc khi hoàn thành
                    if (index + 1) % 5 == 0 or index == len(threads_list) - 1:
                        save_checkpoint(current_index + 1, threads_list)
                except KeyboardInterrupt:
                    logger.info("Đã nhận tín hiệu ngắt từ người dùng, dừng crawl")
                    save_checkpoint(current_index + 1, threads_list)
                    break
        else:
            # Crawl đa luồng
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {}
                
                for index, thread_info in enumerate(threads_list):
                    # Tạo future cho thread
                    future = executor.submit(
                        crawl_single_thread, 
                        thread_info, 
                        max_pages, 
                        use_cache,
                        ocr_enabled
                    )
                    futures[future] = (index, thread_info)
                
                # Xử lý kết quả khi hoàn thành
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Crawling threads"):
                    index, thread_info = futures[future]
                    current_index = start_index + index
                    
                    try:
                        result = future.result()
                        if not result:
                            failed_threads.append(thread_info)
                            
                        # Lưu checkpoint sau mỗi 5 thread hoặc khi hoàn thành
                        if (len(failed_threads) + (current_index - start_index + 1)) % 5 == 0:
                            save_checkpoint(current_index + 1, threads_list)
                    except KeyboardInterrupt:
                        logger.info("Đã nhận tín hiệu ngắt từ người dùng, dừng crawl")
                        save_checkpoint(current_index + 1, threads_list)
                        executor.shutdown(wait=False)
                        break
                    except Exception as e:
                        error_msg = traceback.format_exc()
                        logger.error(f"Thread {thread_info['thread_id']} gặp ngoại lệ: {str(e)}\n{error_msg}")
                        failed_threads.append(thread_info)
    except KeyboardInterrupt:
        logger.info("Đã nhận tín hiệu ngắt từ người dùng, dừng crawl")
        save_checkpoint(current_index + 1, threads_list)
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"Lỗi không mong đợi: {str(e)}\n{error_msg}")
    
    # Báo cáo kết quả
    logger.info(f"Đã hoàn thành crawl {len(threads_list) - len(failed_threads)}/{len(threads_list)} thread")
    logger.info(f"Thành công: {len(threads_list) - len(failed_threads)}")
    logger.info(f"Thất bại: {len(failed_threads)}")
    
    if failed_threads:
        # Lưu danh sách thread thất bại
        failed_file = RAW_DATA_DIR / "failed_threads.json"
        with open(failed_file, 'w', encoding='utf-8') as f:
            json.dump(failed_threads, f, ensure_ascii=False, indent=2)
        logger.info(f"Đã lưu danh sách thread thất bại vào {failed_file}")
    
    return failed_threads

def main():
    """Hàm chính để chạy crawler"""
    # Parse tham số từ dòng lệnh
    parser = argparse.ArgumentParser(description='VOZ Crawler')
    parser.add_argument('--box-url', type=str, default=VOZ_BOX_URL, help='URL của box cần crawl')
    parser.add_argument('--thread-limit', type=int, default=THREAD_LIMIT, help='Số lượng thread tối đa cần crawl')
    parser.add_argument('--max-pages', type=int, default=None, help='Số trang tối đa cần crawl cho mỗi thread')
    parser.add_argument('--workers', type=int, default=1, help='Số lượng worker cho đa luồng')
    parser.add_argument('--no-cache', action='store_true', help='Không sử dụng cache')
    parser.add_argument('--skip-box', action='store_true', help='Bỏ qua việc crawl danh sách thread từ box')
    parser.add_argument('--threads-file', type=str, default="threads_list.json", help='File chứa danh sách thread')
    parser.add_argument('--start-index', type=int, default=0, help='Chỉ số bắt đầu trong danh sách thread')
    parser.add_argument('--retry-failed', action='store_true', help='Thử lại các thread thất bại')
    parser.add_argument('--resume', action='store_true', help='Tiếp tục từ checkpoint')
    parser.add_argument('--no-ocr', action='store_true', help='Tắt xử lý OCR')
    
    args = parser.parse_args()
    
    # Tạo thư mục logs nếu chưa tồn tại
    Path('logs').mkdir(exist_ok=True)
    
    # Log thông tin
    logger.info("Bắt đầu quá trình crawl")
    logger.info(f"URL box: {args.box_url}")
    logger.info(f"Giới hạn thread: {args.thread_limit}")
    logger.info(f"Số lượng worker: {args.workers}")
    logger.info(f"Sử dụng cache: {not args.no_cache}")
    logger.info(f"OCR được kích hoạt: {not args.no_ocr}")
    
    # Tiếp tục từ checkpoint nếu được yêu cầu
    start_index = args.start_index
    if args.resume:
        checkpoint_index = load_checkpoint()
        if checkpoint_index is not None:
            start_index = checkpoint_index
            logger.info(f"Tiếp tục từ checkpoint: index {start_index}")
    
    # Crawl danh sách thread từ box nếu cần
    threads_list = []
    if not args.skip_box and not args.retry_failed:
        threads_list = crawl_box(args.box_url, args.thread_limit, args.threads_file)
    else:
        # Load danh sách thread từ file
        if args.retry_failed:
            logger.info("Thử lại các thread thất bại")
            threads_file = "failed_threads.json"
        else:
            threads_file = args.threads_file
            
        logger.info(f"Đang tải danh sách thread từ {threads_file}")
        threads_list = load_threads_list(threads_file)
        
    # Kiểm tra danh sách thread
    if not threads_list:
        logger.error("Không có thread nào để crawl")
        return
        
    # Cắt danh sách theo chỉ số bắt đầu
    original_list = threads_list.copy()  # Giữ nguyên danh sách gốc cho việc lưu checkpoint
    
    # Crawl các thread
    try:
        crawl_threads_list(
            threads_list, 
            max_threads=None, 
            max_pages=args.max_pages, 
            workers=args.workers, 
            use_cache=not args.no_cache,
            start_index=start_index,
            ocr_enabled=not args.no_ocr
        )
    except KeyboardInterrupt:
        logger.info("Quá trình crawl đã bị ngắt bởi người dùng")
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"Lỗi không mong đợi trong quá trình crawl: {str(e)}\n{error_msg}")
    
    logger.info("Đã hoàn thành quá trình crawl")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Quá trình crawl đã bị ngắt bởi người dùng")
        sys.exit(0)
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"Lỗi không mong đợi: {str(e)}\n{error_msg}")
        sys.exit(1)