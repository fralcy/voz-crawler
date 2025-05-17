import os
import logging
import argparse
import time
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import các module phân tích
from config import DATA_DIR
from detailed_analyzer import DetailedAnalyzer
from network_analyzer import NetworkAnalyzer
from sentiment_analyzer import SentimentAnalyzer
from visualization_creator import VisualizationCreator

def run_detailed_analysis(args):
    """Chạy phân tích chi tiết dữ liệu VOZ"""
    start_time = time.time()
    
    logger.info("=== Bắt đầu Ngày 4: Phân tích chi tiết dữ liệu ===")
    
    # 1. Chạy phân tích chi tiết
    if not args.skip_analysis:
        logger.info("Bước 1: Thực hiện phân tích định lượng và định tính chi tiết")
        analyzer = DetailedAnalyzer()
        analyzer.run_all_analyses()
    else:
        logger.info("Đã bỏ qua bước phân tích chi tiết theo yêu cầu")
    
    # 2. Thực hiện phân tích mạng lưới người dùng
    if not args.skip_network:
        logger.info("Bước 2: Phân tích mạng lưới tương tác người dùng")
        network = NetworkAnalyzer()
        network.run_full_network_analysis()
    else:
        logger.info("Đã bỏ qua bước phân tích mạng lưới theo yêu cầu")
    
    # 3. Thực hiện phân tích sentiment
    if not args.skip_sentiment:
        logger.info("Bước 3: Phân tích cảm xúc trong các bài đăng")
        sentiment = SentimentAnalyzer()
        sentiment.run_full_sentiment_analysis()
    else:
        logger.info("Đã bỏ qua bước phân tích cảm xúc theo yêu cầu")
    
    # 4. Tạo các biểu đồ và trực quan hóa nâng cao
    if not args.skip_visualization:
        logger.info("Bước 4: Tạo các biểu đồ và trực quan hóa nâng cao")
        visualizer = VisualizationCreator()
        visualizer.create_all_visualizations()
    else:
        logger.info("Đã bỏ qua bước tạo biểu đồ theo yêu cầu")
    
    # Tính thời gian thực hiện
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"=== Đã hoàn thành phân tích chi tiết sau {execution_time:.2f} giây ===")

def main():
    """Hàm chính để chạy phân tích chi tiết"""
    # Parse tham số từ dòng lệnh
    parser = argparse.ArgumentParser(description='VOZ Box - Phân tích chi tiết dữ liệu')
    
    # Các tùy chọn bỏ qua các bước
    parser.add_argument('--skip-analysis', action='store_true', help='Bỏ qua bước phân tích chi tiết')
    parser.add_argument('--skip-network', action='store_true', help='Bỏ qua bước phân tích mạng lưới')
    parser.add_argument('--skip-sentiment', action='store_true', help='Bỏ qua bước phân tích sentiment')
    parser.add_argument('--skip-visualization', action='store_true', help='Bỏ qua bước tạo biểu đồ')
    parser.add_argument('--skip-report', action='store_true', help='Bỏ qua bước tạo báo cáo')
    
    # Các tùy chọn chỉ chạy một bước cụ thể
    parser.add_argument('--analysis-only', action='store_true', help='Chỉ chạy bước phân tích chi tiết')
    parser.add_argument('--network-only', action='store_true', help='Chỉ chạy bước phân tích mạng lưới')
    parser.add_argument('--sentiment-only', action='store_true', help='Chỉ chạy bước phân tích sentiment')
    parser.add_argument('--visualization-only', action='store_true', help='Chỉ chạy bước tạo biểu đồ')
    parser.add_argument('--report-only', action='store_true', help='Chỉ chạy bước tạo báo cáo')
    
    args = parser.parse_args()
    
    try:
        # Kiểm tra xem có cần chạy các bước riêng lẻ không
        if args.analysis_only:
            logger.info("Chỉ chạy bước phân tích chi tiết")
            analyzer = DetailedAnalyzer()
            analyzer.run_all_analyses()
        elif args.network_only:
            logger.info("Chỉ chạy bước phân tích mạng lưới")
            network = NetworkAnalyzer()
            network.run_full_network_analysis()
        elif args.sentiment_only:
            logger.info("Chỉ chạy bước phân tích sentiment")
            sentiment = SentimentAnalyzer()
            sentiment.run_full_sentiment_analysis()
        elif args.visualization_only:
            logger.info("Chỉ chạy bước tạo biểu đồ")
            visualizer = VisualizationCreator()
            visualizer.create_all_visualizations()
        else:
            # Chạy toàn bộ quy trình, với các bước có thể bỏ qua tùy theo tham số
            run_detailed_analysis(args)
    except Exception as e:
        logger.error(f"Lỗi khi chạy phân tích chi tiết: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    main()