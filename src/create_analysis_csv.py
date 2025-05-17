import json
import pandas as pd
from pathlib import Path
import logging

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Đường dẫn thư mục
DATA_DIR = Path('data')
ANALYSIS_DIR = DATA_DIR / "analysis"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

def create_threads_analysis_csv():
    """Tạo file threads_analysis.csv từ dữ liệu op_analysis.json"""
    op_file = ANALYSIS_DIR / "op_analysis" / "op_analysis.json"
    
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
    reply_file = ANALYSIS_DIR / "reply_analysis" / "reply_analysis.json"
    
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
            post_date = reply.get('post_date', '')  # Đảm bảo có lấy post_date
            
            # Xử lý từng component trong reply
            for component_type, mentions in reply.get('components', {}).items():
                for mention in mentions:
                    row = {
                        'thread_id': thread_id,
                        'post_id': post_id,
                        'user': user,
                        'post_date': post_date,  # Thêm post_date vào mỗi hàng
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

if __name__ == "__main__":
    logger.info("Bắt đầu tạo các file CSV cho phân tích...")
    create_threads_analysis_csv()
    create_component_suggestions_csv()
    logger.info("Đã hoàn thành tạo các file CSV")