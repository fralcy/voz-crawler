import os
import logging
import argparse
from pathlib import Path
import time
import sys

from data_preprocessor import DataPreprocessor
from data_analyzer import DataAnalyzer
from op_analyzer import OPAnalyzer
from reply_analyzer import ReplyAnalyzer

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_analysis_datasets():
    """Tạo dataset phân tích từ dữ liệu đã crawl"""
    start_time = time.time()
    
    logger.info("=== Bắt đầu quá trình tạo dataset phân tích ===")
    
    # Bước 1: Tiền xử lý dữ liệu
    logger.info("Bước 1: Tiền xử lý dữ liệu")
    preprocessor = DataPreprocessor()
    preprocessor.run_preprocessing()
    
    # Bước 2: Phân tíchimport os
import logging
import argparse
from pathlib import Path
import time
import sys

from data_preprocessor import DataPreprocessor
from data_analyzer import DataAnalyzer
from op_analyzer import OPAnalyzer
from reply_analyzer import ReplyAnalyzer

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_analysis_datasets():
    """Tạo dataset phân tích từ dữ liệu đã crawl"""
    start_time = time.time()
    
    logger.info("=== Bắt đầu quá trình tạo dataset phân tích ===")
    
    # Bước 1: Tiền xử lý dữ liệu
    logger.info("Bước 1: Tiền xử lý dữ liệu")
    preprocessor = DataPreprocessor()
    preprocessor.run_preprocessing()
    
    # Bước 2: Phân tích tổng quát
    logger.info("Bước 2: Phân tích tổng quát")
    analyzer = DataAnalyzer()
    analyzer.run_full_analysis()
    
    # Bước 3: Phân tích chi tiết các bài đăng đầu tiên (OP)
    logger.info("Bước 3: Phân tích chi tiết OP")
    op_analyzer = OPAnalyzer()
    op_analyzer.run_analysis()
    
    # Bước 4: Phân tích chi tiết các bài trả lời (reply)
    logger.info("Bước 4: Phân tích chi tiết replies")
    reply_analyzer = ReplyAnalyzer()
    reply_analyzer.run_analysis()
    
    # Tính thời gian thực hiện
    elapsed_time = time.time() - start_time
    logger.info(f"=== Hoàn thành tạo dataset phân tích trong {elapsed_time:.2f} giây ===")
    
    return True

def main():
    # Parse tham số từ dòng lệnh
    parser = argparse.ArgumentParser(description='Tạo dataset phân tích từ dữ liệu VOZ đã crawl')
    parser.add_argument('--preprocessor-only', action='store_true', help='Chỉ chạy bước tiền xử lý')
    parser.add_argument('--analyzer-only', action='store_true', help='Chỉ chạy bước phân tích tổng quát')
    parser.add_argument('--op-only', action='store_true', help='Chỉ chạy bước phân tích OP')
    parser.add_argument('--reply-only', action='store_true', help='Chỉ chạy bước phân tích replies')
    
    args = parser.parse_args()
    
    try:
        # Nếu chỉ định chạy một bước cụ thể
        if args.preprocessor_only:
            logger.info("Chạy riêng bước tiền xử lý dữ liệu")
            preprocessor = DataPreprocessor()
            preprocessor.run_preprocessing()
        elif args.analyzer_only:
            logger.info("Chạy riêng bước phân tích tổng quát")
            analyzer = DataAnalyzer()
            analyzer.run_full_analysis()
        elif args.op_only:
            logger.info("Chạy riêng bước phân tích OP")
            op_analyzer = OPAnalyzer()
            op_analyzer.run_analysis()
        elif args.reply_only:
            logger.info("Chạy riêng bước phân tích replies")
            reply_analyzer = ReplyAnalyzer()
            reply_analyzer.run_analysis()
        else:
            # Chạy tất cả các bước
            create_analysis_datasets()
    except KeyboardInterrupt:
        logger.info("Quá trình tạo dataset bị ngắt bởi người dùng")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()