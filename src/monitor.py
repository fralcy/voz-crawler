import os
import json
import logging
import time
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, THREAD_LIMIT

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

def load_thread_data(thread_id):
    """Load dữ liệu của một thread từ file JSON"""
    file_path = PROCESSED_DATA_DIR / f"thread_{thread_id}.json"
    
    if not file_path.exists():
        return None
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi đọc file {file_path}: {str(e)}")
        return None

def analyze_progress(threads_list):
    """Phân tích tiến độ crawl"""
    if not threads_list:
        logger.error("Danh sách thread trống")
        return None
        
    total_threads = len(threads_list)
    processed_threads = 0
    total_posts = 0
    total_images = 0
    total_images_processed = 0
    
    thread_stats = []
    
    for thread_info in threads_list:
        thread_id = thread_info['thread_id']
        thread_data = load_thread_data(thread_id)
        
        if thread_data:
            processed_threads += 1
            posts = thread_data.get('posts', [])
            total_posts += len(posts)
            
            # Đếm số lượng hình ảnh và số hình ảnh đã xử lý OCR
            thread_images = 0
            thread_images_processed = 0
            
            for post in posts:
                images = post.get('images', [])
                thread_images += len(images)
                
                for image in images:
                    if image.get('ocr_text') is not None:
                        thread_images_processed += 1
            
            total_images += thread_images
            total_images_processed += thread_images_processed
            
            # Thêm vào danh sách thống kê
            thread_stats.append({
                'thread_id': thread_id,
                'title': thread_data.get('title', ''),
                'post_count': len(posts),
                'image_count': thread_images,
                'image_processed': thread_images_processed
            })
    
    # Tính toán tỉ lệ
    thread_progress = processed_threads / total_threads * 100 if total_threads > 0 else 0
    image_progress = total_images_processed / total_images * 100 if total_images > 0 else 0
    
    # Tạo kết quả
    result = {
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        'total_threads': total_threads,
        'processed_threads': processed_threads,
        'thread_progress': thread_progress,
        'total_posts': total_posts,
        'total_images': total_images,
        'total_images_processed': total_images_processed,
        'image_progress': image_progress,
        'thread_stats': thread_stats
    }
    
    return result

def save_progress_report(progress_data, filename="progress_report.json"):
    """Lưu báo cáo tiến độ vào file JSON"""
    if not progress_data:
        return False
        
    # Tạo thư mục báo cáo nếu chưa tồn tại
    report_dir = Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Tạo tên file với timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_path = report_dir / f"{timestamp}_{filename}"
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Đã lưu báo cáo tiến độ vào {file_path}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu báo cáo tiến độ: {str(e)}")
        return False

def create_progress_charts(progress_data, save_dir="reports"):
    """Tạo biểu đồ tiến độ"""
    if not progress_data:
        return False
        
    # Tạo thư mục báo cáo nếu chưa tồn tại
    report_dir = Path(save_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Tạo timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    try:
        # Tạo biểu đồ tiến độ thread
        plt.figure(figsize=(10, 6))
        labels = ['Đã xử lý', 'Chưa xử lý']
        values = [progress_data['processed_threads'], 
                 progress_data['total_threads'] - progress_data['processed_threads']]
        colors = ['#4CAF50', '#F44336']
        
        plt.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        plt.title('Tiến độ xử lý thread')
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(report_dir / f"{timestamp}_thread_progress.png")
        plt.close()
        
        # Tạo biểu đồ tiến độ xử lý OCR hình ảnh
        plt.figure(figsize=(10, 6))
        labels = ['Đã OCR', 'Chưa OCR']
        values = [progress_data['total_images_processed'], 
                 progress_data['total_images'] - progress_data['total_images_processed']]
        
        plt.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        plt.title('Tiến độ xử lý OCR hình ảnh')
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(report_dir / f"{timestamp}_image_ocr_progress.png")
        plt.close()
        
        # Tạo biểu đồ top 10 thread có nhiều hình ảnh nhất
        thread_stats = progress_data['thread_stats']
        thread_stats.sort(key=lambda x: x['image_count'], reverse=True)
        top_threads = thread_stats[:10]
        
        plt.figure(figsize=(12, 8))
        
        thread_titles = [t['title'][:30] + '...' if len(t['title']) > 30 else t['title'] for t in top_threads]
        image_counts = [t['image_count'] for t in top_threads]
        
        plt.barh(thread_titles, image_counts, color='#2196F3')
        plt.xlabel('Số lượng hình ảnh')
        plt.ylabel('Thread')
        plt.title('Top 10 thread có nhiều hình ảnh nhất')
        plt.tight_layout()
        plt.savefig(report_dir / f"{timestamp}_top_threads_by_images.png")
        plt.close()
        
        logger.info(f"Đã tạo các biểu đồ tiến độ trong thư mục {report_dir}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ tiến độ: {str(e)}")
        return False

def monitor_progress(threads_file="threads_list.json", interval=300):
    """Theo dõi tiến độ crawl theo chu kỳ"""
    logger.info(f"Bắt đầu theo dõi tiến độ (kiểm tra mỗi {interval} giây)")
    
    while True:
        # Load danh sách thread
        threads_list = load_threads_list(threads_file)
        
        if not threads_list:
            logger.error("Không thể tải danh sách thread")
            break
            
        # Phân tích tiến độ
        progress_data = analyze_progress(threads_list)
        
        if not progress_data:
            logger.error("Không thể phân tích tiến độ")
            break
            
        # Hiển thị thông tin tiến độ
        logger.info(f"Tiến độ xử lý thread: {progress_data['processed_threads']}/{progress_data['total_threads']} ({progress_data['thread_progress']:.2f}%)")
        logger.info(f"Tiến độ xử lý OCR: {progress_data['total_images_processed']}/{progress_data['total_images']} ({progress_data['image_progress']:.2f}%)")
        
        # Lưu báo cáo và tạo biểu đồ
        save_progress_report(progress_data)
        create_progress_charts(progress_data)
        
        # Kiểm tra xem đã hoàn thành chưa
        if progress_data['processed_threads'] >= progress_data['total_threads'] and progress_data['total_images_processed'] >= progress_data['total_images']:
            logger.info("Đã hoàn thành tất cả các thread và xử lý OCR")
            break
            
        # Đợi đến chu kỳ tiếp theo
        logger.info(f"Đợi {interval} giây đến lần kiểm tra tiếp theo...")
        time.sleep(interval)
    
    logger.info("Kết thúc theo dõi tiến độ")

def main():
    """Hàm chính để chạy monitor"""
    # Parse tham số từ dòng lệnh
    parser = argparse.ArgumentParser(description='VOZ Crawler Monitor')
    parser.add_argument('--threads-file', type=str, default="threads_list.json", help='File chứa danh sách thread')
    parser.add_argument('--interval', type=int, default=300, help='Khoảng thời gian (giây) giữa các lần kiểm tra')
    parser.add_argument('--one-time', action='store_true', help='Chỉ kiểm tra một lần')
    
    args = parser.parse_args()
    
    # Tạo thư mục reports nếu chưa tồn tại
    Path("reports").mkdir(parents=True, exist_ok=True)
    
    if args.one_time:
        # Chỉ kiểm tra một lần
        logger.info("Chế độ kiểm tra một lần")
        
        # Load danh sách thread
        threads_list = load_threads_list(args.threads_file)
        
        if not threads_list:
            logger.error("Không thể tải danh sách thread")
            return
            
        # Phân tích tiến độ
        progress_data = analyze_progress(threads_list)
        
        if not progress_data:
            logger.error("Không thể phân tích tiến độ")
            return
            
        # Hiển thị thông tin tiến độ
        logger.info(f"Tiến độ xử lý thread: {progress_data['processed_threads']}/{progress_data['total_threads']} ({progress_data['thread_progress']:.2f}%)")
        logger.info(f"Tiến độ xử lý OCR: {progress_data['total_images_processed']}/{progress_data['total_images']} ({progress_data['image_progress']:.2f}%)")
        
        # Lưu báo cáo và tạo biểu đồ
        save_progress_report(progress_data)
        create_progress_charts(progress_data)
    else:
        # Theo dõi theo chu kỳ
        monitor_progress(args.threads_file, args.interval)

if __name__ == "__main__":
    main()