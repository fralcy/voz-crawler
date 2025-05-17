import pandas as pd
import json
import logging
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Đường dẫn thư mục
DATA_DIR = Path('data')
ANALYSIS_DIR = DATA_DIR / "analysis"
OP_ANALYSIS_DIR = ANALYSIS_DIR / "op_analysis"
DETAILED_ANALYSIS_DIR = ANALYSIS_DIR / "detailed_analysis"

# Đảm bảo thư mục tồn tại
DETAILED_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

def create_budget_distribution():
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
        output_file = DETAILED_ANALYSIS_DIR / "budget_distribution.csv"
        budget_counts.to_csv(output_file, index=False)
        
        # Tạo thêm file dữ liệu chi tiết
        detail_file = DETAILED_ANALYSIS_DIR / "budget_detailed.csv"
        budget_df.to_csv(detail_file, index=False)
        
        logger.info(f"Đã tạo file budget_distribution.csv với {len(budget_counts)} khoảng ngân sách")
        logger.info(f"Đã tạo file budget_detailed.csv với {len(budget_df)} threads")
        
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo file budget_distribution.csv: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def create_budget_distribution_chart():
    """Tạo biểu đồ phân bố ngân sách"""
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # Đường dẫn file budget_distribution.csv
    budget_file = DETAILED_ANALYSIS_DIR / "budget_distribution.csv"
    
    if not budget_file.exists():
        logger.error(f"File budget_distribution.csv không tồn tại: {budget_file}")
        return False
    
    try:
        # Đọc dữ liệu
        budget_df = pd.read_csv(budget_file)
        
        # Tạo thư mục cho biểu đồ
        VISUALIZATION_DIR = DETAILED_ANALYSIS_DIR / "visualizations"
        VISUALIZATION_DIR.mkdir(parents=True, exist_ok=True)
        
        # Tạo biểu đồ cột
        plt.figure(figsize=(12, 8))
        
        # Vẽ biểu đồ cột với màu gradient
        ax = sns.barplot(
            x='range', 
            y='count', 
            data=budget_df,
            palette='viridis'
        )
        
        # Thêm số lượng trên đầu mỗi cột
        for i, p in enumerate(ax.patches):
            ax.annotate(
                f'{int(p.get_height())}', 
                (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', 
                va='bottom',
                fontsize=11,
                fontweight='bold'
            )
        
        # Tính phần trăm
        total = budget_df['count'].sum()
        for i, p in enumerate(ax.patches):
            percentage = p.get_height() / total * 100
            ax.annotate(
                f'{percentage:.1f}%', 
                (p.get_x() + p.get_width() / 2., p.get_height() / 2),
                ha='center', 
                va='center',
                fontsize=10,
                fontweight='bold',
                color='white'
            )
        
        # Thêm tiêu đề và nhãn
        plt.title('Phân bố ngân sách trong các thread "Tư vấn cấu hình"', fontsize=16, pad=20)
        plt.xlabel('Khoảng ngân sách (triệu VNĐ)', fontsize=12)
        plt.ylabel('Số lượng thread', fontsize=12)
        plt.xticks(rotation=45)
        
        # Thêm lưới và định dạng
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Lưu biểu đồ
        plt.tight_layout()
        plt.savefig(VISUALIZATION_DIR / "budget_distribution.png", dpi=300)
        plt.close()
        
        # Tạo thêm biểu đồ histogram cho phân bố chi tiết
        detail_file = DETAILED_ANALYSIS_DIR / "budget_detailed.csv"
        if detail_file.exists():
            # Đọc dữ liệu chi tiết
            detail_df = pd.read_csv(detail_file)
            
            # Tạo histogram
            plt.figure(figsize=(12, 8))
            
            # Vẽ histogram với kernel density
            sns.histplot(
                data=detail_df,
                x='budget',
                bins=20,
                kde=True,
                color='steelblue'
            )
            
            # Thêm đường dọc cho giá trị trung bình và trung vị
            mean_budget = detail_df['budget'].mean()
            median_budget = detail_df['budget'].median()
            mode_budget = detail_df['budget'].value_counts().index[0]
            
            plt.axvline(mean_budget, color='red', linestyle='--', linewidth=2, label=f'Trung bình: {mean_budget:.1f}tr')
            plt.axvline(median_budget, color='green', linestyle='--', linewidth=2, label=f'Trung vị: {median_budget:.1f}tr')
            plt.axvline(mode_budget, color='purple', linestyle='--', linewidth=2, label=f'Mode: {mode_budget:.1f}tr')
            
            # Thêm tiêu đề và nhãn
            plt.title('Phân bố chi tiết ngân sách PC', fontsize=16, pad=20)
            plt.xlabel('Ngân sách (triệu VNĐ)', fontsize=12)
            plt.ylabel('Số lượng thread', fontsize=12)
            plt.legend()
            
            # Thêm lưới và định dạng
            plt.grid(linestyle='--', alpha=0.7)
            
            # Lưu biểu đồ
            plt.tight_layout()
            plt.savefig(VISUALIZATION_DIR / "budget_histogram.png", dpi=300)
            plt.close()
        
        logger.info("Đã tạo biểu đồ phân bố ngân sách")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ phân bố ngân sách: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Đang tạo file phân bố ngân sách...")
    success = create_budget_distribution()
    
    if success:
        print("Đang tạo biểu đồ phân bố ngân sách...")
        create_budget_distribution_chart()
    else:
        print("Không thể tạo biểu đồ vì không có dữ liệu phân bố ngân sách")