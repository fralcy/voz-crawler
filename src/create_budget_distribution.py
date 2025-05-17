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

def create_budget_distribution_csv():
    """Tạo file budget_distribution.csv từ dữ liệu op_analysis.json"""
    # Đường dẫn thư mục
    DATA_DIR = Path('data')
    ANALYSIS_DIR = DATA_DIR / "analysis"
    OP_ANALYSIS_DIR = ANALYSIS_DIR / "op_analysis"
    BUDGET_ANALYSIS_DIR = ANALYSIS_DIR / "bubget_analysis"

    # Đảm bảo thư mục tồn tại
    BUDGET_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    
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
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Đang tạo file phân bố ngân sách...")
    success = create_budget_distribution_csv()
    
    if success:
        print("Đã tạo file phân bố ngân sách thành công")
    else:
        print("Không thể tạo file phân bố ngân sách")