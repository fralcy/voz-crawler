import logging
import argparse
from pathlib import Path
import time
import sys
import pandas as pd
import json

from data_preprocessor import DataPreprocessor
from data_analyzer import DataAnalyzer
from op_analyzer import OPAnalyzer
from reply_analyzer import ReplyAnalyzer
from config import DATA_DIR

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Thư mục phân tích
ANALYSIS_DIR = DATA_DIR / "analysis"
OP_ANALYSIS_DIR = ANALYSIS_DIR / "op_analysis"
REPLY_ANALYSIS_DIR = ANALYSIS_DIR / "reply_analysis"
BUDGET_ANALYSIS_DIR = ANALYSIS_DIR / "budget_analysis"

# Đảm bảo thư mục tồn tại
for dir_path in [ANALYSIS_DIR, OP_ANALYSIS_DIR, REPLY_ANALYSIS_DIR, BUDGET_ANALYSIS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

def create_threads_analysis_csv():
    """Tạo file threads_analysis.csv từ dữ liệu op_analysis.json"""
    op_file = OP_ANALYSIS_DIR / "op_analysis.json"
    
    if not op_file.exists():
        logger.error(f"File op_analysis.json không tồn tại: {op_file}")
        return False
    
    try:
        # Đọc dữ liệu OP
        with open(op_file, 'r', encoding='utf-8') as f:
            op_data = json.load(f)
        
        # Tạo danh sách các thread
        thread_rows = []
        
        for op in op_data:
            row = {
                'thread_id': op.get('thread_id', ''),
                'title': op.get('title', ''),
                'budget': op.get('budget', {}).get('value') if op.get('budget') else None,
                'purposes': ','.join(op.get('purposes', [])),
                'special_requirements': ','.join(op.get('special_requirements', [])),
                'user': op.get('user', ''),
                'post_date': op.get('post_date', '')
            }
            thread_rows.append(row)
        
        # Tạo DataFrame
        threads_df = pd.DataFrame(thread_rows)
        
        # Lưu vào CSV
        output_file = ANALYSIS_DIR / "threads_analysis.csv"
        threads_df.to_csv(output_file, index=False)
        
        logger.info(f"Đã tạo file threads_analysis.csv với {len(threads_df)} threads")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo file threads_analysis.csv: {str(e)}")
        return False

def create_component_suggestions_csv():
    """Tạo file component_suggestions.csv từ dữ liệu reply_analysis.json"""
    reply_file = REPLY_ANALYSIS_DIR / "reply_analysis.json"
    
    if not reply_file.exists():
        logger.error(f"File reply_analysis.json không tồn tại: {reply_file}")
        return False
    
    try:
        # Đọc dữ liệu Reply
        with open(reply_file, 'r', encoding='utf-8') as f:
            reply_data = json.load(f)
        
        # Tạo danh sách các component suggestions
        suggestion_rows = []
        
        for reply in reply_data:
            thread_id = reply.get('thread_id')
            post_id = reply.get('post_id')
            user = reply.get('user')
            post_date = reply.get('post_date', '')
            
            # Xử lý từng component trong reply
            for component_type, mentions in reply.get('components', {}).items():
                for mention in mentions:
                    row = {
                        'thread_id': thread_id,
                        'post_id': post_id,
                        'user': user,
                        'post_date': post_date,
                        'component_type': component_type,
                        'keyword': mention.get('keyword', ''),
                        'context': mention.get('context', '')[:200],  # Giới hạn độ dài
                        'has_images': reply.get('has_images', False),
                        'likes': reply.get('reactions', {}).get('Like', 0),
                        'thanks': reply.get('reactions', {}).get('Thanks', 0)
                    }
                    suggestion_rows.append(row)
        
        # Tạo DataFrame
        suggestions_df = pd.DataFrame(suggestion_rows)
        
        # Lưu vào CSV
        output_file = ANALYSIS_DIR / "component_suggestions.csv"
        suggestions_df.to_csv(output_file, index=False)
        
        logger.info(f"Đã tạo file component_suggestions.csv với {len(suggestions_df)} suggestions")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo file component_suggestions.csv: {str(e)}")
        return False

def create_budget_distribution_csv():
    """Tạo file budget_distribution.csv từ dữ liệu op_analysis.json"""
    # Đường dẫn file op_analysis.json
    op_file = OP_ANALYSIS_DIR / "op_analysis.json"
    
    if not op_file.exists():
        logger.error(f"File op_analysis.json không tồn tại: {op_file}")
        return False
    
    try:
        # Đọc dữ liệu OP
        with open(op_file, 'r', encoding='utf-8') as f:
            op_data = json.load(f)
        
        # Lọc ra các thread có thông tin ngân sách
        budget_data = []
        for op in op_data:
            if op.get('budget'):
                budget_value = op.get('budget', {}).get('value')
                if budget_value:
                    budget_data.append({
                        'thread_id': op.get('thread_id', ''),
                        'title': op.get('title', ''),
                        'budget': budget_value
                    })
        
        # Tạo DataFrame
        budget_df = pd.DataFrame(budget_data)
        
        # Tạo các khoảng ngân sách
        budget_ranges = [0, 5, 10, 15, 20, 25, 30, 40, 50, 100]
        budget_labels = ['0-5tr', '5-10tr', '10-15tr', '15-20tr', '20-25tr', '25-30tr', '30-40tr', '40-50tr', '50tr+']
        
        # Thêm cột phân loại ngân sách
        budget_df['range'] = pd.cut(
            budget_df['budget'], 
            bins=budget_ranges, 
            labels=budget_labels, 
            right=False
        )
        
        # Đếm số lượng thread theo mỗi khoảng ngân sách
        budget_counts = budget_df['range'].value_counts().reset_index()
        budget_counts.columns = ['range', 'count']
        
        # Sắp xếp theo thứ tự khoảng ngân sách
        budget_counts = budget_counts.sort_values(by='range', key=lambda x: pd.Categorical(x, categories=budget_labels, ordered=True))
        
        # Lưu kết quả
        output_file = BUDGET_ANALYSIS_DIR / "budget_distribution.csv"
        budget_counts.to_csv(output_file, index=False)
        
        # Tạo thêm file dữ liệu chi tiết
        detail_file = BUDGET_ANALYSIS_DIR / "budget_detailed.csv"
        budget_df.to_csv(detail_file, index=False)
        
        logger.info(f"Đã tạo file budget_distribution.csv với {len(budget_counts)} khoảng ngân sách")
        logger.info(f"Đã tạo file budget_detailed.csv với {len(budget_df)} threads")
        
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo file budget_distribution.csv: {str(e)}")
        return False

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
    
    # Bước 5: Tạo các file CSV cho phân tích
    logger.info("Bước 5: Tạo các file CSV cho phân tích")
    create_threads_analysis_csv()
    create_component_suggestions_csv()
    create_budget_distribution_csv()
    
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
    parser.add_argument('--csv-only', action='store_true', help='Chỉ tạo các file CSV')
    
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
        elif args.csv_only:
            logger.info("Chỉ tạo các file CSV cho phân tích")
            create_threads_analysis_csv()
            create_component_suggestions_csv()
            create_budget_distribution_csv()
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