import json
import logging
import re
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter
import unicodedata

from config import DATA_DIR, PROCESSED_DATA_DIR

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Thư mục đầu ra
OP_ANALYSIS_DIR = DATA_DIR / "analysis" / "op_analysis"
OP_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

class OPAnalyzer:
    """
    Class chuyên phân tích các bài đăng đầu tiên (OP) trong thread
    """
    def __init__(self, threads_dir=PROCESSED_DATA_DIR):
        self.threads_dir = threads_dir
        self.threads_data = []
        self.op_analysis = []
        
        # Các regex patterns để trích xuất ngân sách
        self.budget_patterns = [
            r'ng[aâ]n\s*s[áa]ch\s*(?:kho[ảả]ng|t[ầà]m|\:|\s)\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r'bu[dđ]ge[dt]\s*(?:kho[ảả]ng|t[ầà]m|\:|\s)\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r't[ổố]ng\s*(?:chi\s*ph[íi]|gi[áa])\s*(?:kho[ảả]ng|t[ầà]m|\:|\s)\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r'kho[ảả]ng\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r't[ầà]m\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r'(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
        ]
        
        # Từ khóa cho mục đích sử dụng
        self.purpose_keywords = {
            'gaming': [
                'gaming', 'game', 'chơi game', 'esport', 'fps', 'moba', 'battle royale', 'lol', 
                'liên minh', 'pubg', 'valorant', 'csgo', 'counter strike', 'dota', 'fortnite', 'rpg', 
                'single player', 'multiplayer', 'steam', 'epic', 'gaming pc', 'máy chơi game'
            ],
            'work': [
                'work', 'làm việc', 'văn phòng', 'office', 'excel', 'word', 'microsoft office', 'google docs',
                'word processing', 'spreadsheet', 'outlook', 'email', 'zoom', 'teams', 'meet',
                'remote work', 'wfh', 'tác vụ văn phòng'
            ],
            'programming': [
                'programming', 'coding', 'development', 'lập trình', 'code', 'developer', 'software', 
                'web dev', 'app dev', 'mobile dev', 'devops', 'ide', 'visual studio', 'vscode', 'pycharm',
                'intellij', 'android studio', 'xcode', 'github', 'gitlab'
            ],
            'graphics': [
                'graphics', 'design', 'đồ họa', 'thiết kế', 'photoshop', 'illustrator', 'adobe', 'gimp', 
                'figma', 'design', 'illustration', 'graphic design', 'ui', 'ux', 'indesign', 'lightroom',
                'premiere', 'after effects', 'blender', 'rendering', 'ray tracing'
            ],
            'video_editing': [
                'video', 'editing', 'biên tập', 'chỉnh sửa video', 'premiere', 'after effects', 'davinci resolve',
                'final cut', 'sony vegas', 'video production', 'youtube', 'livestream', 'stream', 'obs',
                'xsplit', 'streamlabs', 'video creator'
            ],
            '3d_rendering': [
                '3d', 'rendering', 'animation', 'blender', 'maya', '3ds max', 'cinema 4d', 'autocad', 
                'revit', 'sketchup', '3d modeling', 'archviz', 'architectural visualization', 'cad', 'render'
            ],
            'streaming': [
                'streaming', 'stream', 'broadcast', 'obs', 'streamlabs', 'xsplit', 'twitch', 'youtube live',
                'facebook live', 'streamer', 'content creator', 'influencer', 'live'
            ],
            'study': [
                'study', 'học tập', 'school', 'university', 'education', 'learning', 'research', 'thesis', 
                'assignment', 'coursework', 'student', 'e-learning', 'online learning', 'homework', 'essay'
            ]
        }
        
        # Từ khóa cho yêu cầu đặc biệt
        self.special_req_keywords = {
            'quiet': ['quiet', 'silent', 'im lặng', 'êm', 'không ồn', 'không tiếng'],
            'rgb': ['rgb', 'led', 'lighting', 'đèn', 'ánh sáng'],
            'white': ['white', 'màu trắng', 'case trắng', 'white build'],
            'black': ['black', 'màu đen', 'case đen', 'black build'],
            'small': ['itx', 'small', 'nhỏ gọn', 'mini', 'sff'],
            'upgrade': ['upgrade', 'nâng cấp', 'mở rộng', 'tương lai', 'sau này'],
            'no_gpu': ['không card', 'không gpu', 'onboard', 'igpu', 'không rời'],
            'wifi': ['wifi', 'wireless', 'không dây'],
            'bluetooth': ['bluetooth', 'bt'],
            'hackintosh': ['hackintosh', 'macos', 'mac os'],
            'overclocking': ['oc', 'overclock', 'boost', 'ép xung'],
            'low_power': ['tiết kiệm điện', 'power saving', 'low power', 'tdp thấp']
        }
    
    def load_thread_files(self):
        """Tải tất cả các file thread đã xử lý"""
        self.threads_data = []
        thread_files = list(self.threads_dir.glob("thread_*.json"))
        logger.info(f"Tìm thấy {len(thread_files)} file thread để phân tích")
        
        for file_path in thread_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    thread_data = json.load(f)
                    self.threads_data.append(thread_data)
            except Exception as e:
                logger.error(f"Lỗi khi đọc file {file_path}: {str(e)}")
                
        logger.info(f"Đã tải {len(self.threads_data)} threads để phân tích")
        return self.threads_data
    
    def preprocess_text(self, text):
        """Tiền xử lý văn bản: chuyển về chữ thường và chuẩn hóa Unicode"""
        if not text:
            return ""
            
        # Chuyển về chữ thường
        text = text.lower()
        
        # Chuẩn hóa Unicode (chuyển từ NFKD sang NFC)
        text = unicodedata.normalize('NFC', text)
        
        return text.strip()
    
    def extract_budget_from_text(self, text):
        """Trích xuất ngân sách từ văn bản"""
        if not text:
            return None
            
        # Chuẩn bị văn bản
        text = self.preprocess_text(text)
        
        # Tìm kiếm theo từng pattern
        for pattern in self.budget_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    value_str = match.group(1)
                    unit = match.group(2)
                    
                    # Chuẩn hóa về triệu đồng
                    budget_in_million = self.normalize_money_value(value_str, unit)
                    
                    # Kiểm tra mức hợp lý (từ 1 triệu đến 100 triệu)
                    if budget_in_million and 1 <= budget_in_million <= 100:
                        return {
                            'value': budget_in_million,
                            'unit': 'triệu',
                            'original_text': match.group(0)
                        }
                except Exception as e:
                    logger.error(f"Lỗi khi trích xuất ngân sách: {str(e)}")
                    continue
                    
        return None
    
    def normalize_money_value(self, value_str, unit):
        """Chuẩn hóa giá trị tiền tệ về đơn vị triệu đồng"""
        try:
            # Chuyển đổi chuỗi số thành số thực
            value = float(value_str.replace(',', '.'))
            
            # Chuyển đổi đơn vị về triệu đồng
            unit = unit.lower()
            if unit in ['tr', 'triệu', 'trieu', 'củ', 'cu', 'trĩ', 'tri']:
                return value
            elif unit in ['nghìn', 'nghin', 'ngàn', 'ngan']:
                return value / 1000
            elif unit == 'k':  # k ở đây là "nghìn" (kilo), KHÔNG phải độ phân giải
                return value / 1000
            elif unit in ['đồng', 'dong', 'vnd', 'd', 'đ']:
                return value / 1000000
            else:
                # Mặc định xem như triệu đồng
                return value
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn hóa giá trị tiền tệ: {str(e)}")
            return None
    
    def extract_purposes_from_text(self, text):
        """Trích xuất mục đích sử dụng từ văn bản"""
        if not text:
            return []
            
        # Chuẩn bị văn bản
        text = self.preprocess_text(text)
        
        # Tìm kiếm các từ khóa mục đích
        found_purposes = []
        
        for purpose, keywords in self.purpose_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    if purpose not in found_purposes:
                        found_purposes.append(purpose)
                    break
                    
        return found_purposes
    
    def extract_special_requirements(self, text):
        """Trích xuất các yêu cầu đặc biệt từ văn bản"""
        if not text:
            return []
            
        # Chuẩn bị văn bản
        text = self.preprocess_text(text)
        
        # Tìm kiếm các từ khóa yêu cầu đặc biệt
        found_requirements = []
        
        for req, keywords in self.special_req_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    if req not in found_requirements:
                        found_requirements.append(req)
                    break
                    
        return found_requirements
    
    def analyze_op_post(self, thread_data):
        """Phân tích bài đăng đầu tiên (OP) để trích xuất thông tin"""
        if not thread_data or 'posts' not in thread_data or not thread_data['posts']:
            return None
            
        # Lấy bài đăng đầu tiên
        op_post = thread_data['posts'][0]
        
        # Trích xuất thông tin từ tiêu đề thread
        title = thread_data.get('title', '')
        title_budget = self.extract_budget_from_text(title)
        title_purposes = self.extract_purposes_from_text(title)
        
        # Trích xuất thông tin từ nội dung OP
        content = op_post.get('content_text', '')
        content_budget = self.extract_budget_from_text(content)
        content_purposes = self.extract_purposes_from_text(content)
        
        # Trích xuất yêu cầu đặc biệt từ cả tiêu đề và nội dung
        special_requirements = self.extract_special_requirements(title + ' ' + content)
        
        # Kết hợp thông tin từ tiêu đề và nội dung
        budget = title_budget if title_budget else content_budget
        purposes = list(set(title_purposes + content_purposes))
        
        # Tạo kết quả phân tích
        analysis = {
            'thread_id': thread_data.get('thread_id', ''),
            'title': title,
            'budget': budget,
            'purposes': purposes,
            'special_requirements': special_requirements,
            'user': op_post.get('author', {}).get('username', ''),
            'post_date': op_post.get('created_date', ''),
            'content_length': len(content)
        }
        
        return analysis
    
    def analyze_all_ops(self):
        """Phân tích tất cả các bài đăng đầu tiên (OP)"""
        if not self.threads_data:
            self.load_thread_files()
            
        self.op_analysis = []
        
        for i, thread_data in enumerate(self.threads_data):
            try:
                logger.info(f"Đang phân tích OP của thread {i+1}/{len(self.threads_data)}: {thread_data.get('thread_id', '')}")
                
                # Phân tích OP
                op_analysis = self.analyze_op_post(thread_data)
                
                if op_analysis:
                    self.op_analysis.append(op_analysis)
                    
                # Log tiến độ
                if (i + 1) % 10 == 0 or i == len(self.threads_data) - 1:
                    logger.info(f"Đã phân tích {i+1}/{len(self.threads_data)} OPs")
                    
            except Exception as e:
                logger.error(f"Lỗi khi phân tích OP của thread {thread_data.get('thread_id', '')}: {str(e)}")
                continue
                
        logger.info(f"Đã phân tích xong {len(self.op_analysis)}/{len(self.threads_data)} OPs")
        
        return self.op_analysis
    
    def save_op_analysis(self, filename="op_analysis.json"):
        """Lưu kết quả phân tích OP vào file JSON"""
        if not self.op_analysis:
            logger.warning("Không có dữ liệu phân tích OP để lưu")
            return False
            
        try:
            # Tạo thư mục nếu chưa tồn tại
            OP_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Lưu dữ liệu phân tích
            output_file = OP_ANALYSIS_DIR / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.op_analysis, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Đã lưu kết quả phân tích OP vào {output_file}")
            
            # Tạo file CSV cho phân tích
            self.create_op_analysis_csv()
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả phân tích OP: {str(e)}")
            return False
    
    def create_op_analysis_csv(self):
        """Tạo file CSV từ dữ liệu phân tích OP để dễ dàng phân tích hơn"""
        if not self.op_analysis:
            logger.warning("Không có dữ liệu phân tích OP để tạo CSV")
            return False
            
        try:
            # Tạo DataFrame cho OP
            op_rows = []
            
            for op in self.op_analysis:
                row = {
                    'thread_id': op.get('thread_id', ''),
                    'title': op.get('title', ''),
                    'budget': op.get('budget', {}).get('value', None),
                    'budget_original': op.get('budget', {}).get('original_text', ''),
                    'purposes': ','.join(op.get('purposes', [])),
                    'special_requirements': ','.join(op.get('special_requirements', [])),
                    'user': op.get('user', ''),
                    'post_date': op.get('post_date', ''),
                    'content_length': op.get('content_length', 0)
                }
                
                op_rows.append(row)
                
            # Tạo DataFrame cho OP
            op_df = pd.DataFrame(op_rows)
            
            # Lưu DataFrame OP vào CSV
            op_csv = OP_ANALYSIS_DIR / "op_analysis.csv"
            op_df.to_csv(op_csv, index=False, encoding='utf-8-sig')
            logger.info(f"Đã lưu phân tích OP vào {op_csv}")
            
            # Tạo DataFrame cho phân bố ngân sách
            budget_rows = []
            budget_data = [op.get('budget', {}).get('value', None) for op in self.op_analysis if op.get('budget')]
            
            if budget_data:
                # Tạo DataFrame cho phân bố ngân sách
                budget_df = pd.DataFrame(budget_data, columns=['budget'])
                budget_df['count'] = 1
                
                # Gom nhóm theo khoảng ngân sách
                budget_ranges = [0, 5, 10, 15, 20, 25, 30, 40, 50, 100]
                budget_labels = ['0-5tr', '5-10tr', '10-15tr', '15-20tr', '20-25tr', '25-30tr', '30-40tr', '40-50tr', '50tr+']
                budget_df['range'] = pd.cut(budget_df['budget'], budget_ranges, labels=budget_labels, right=False)
                
                # Tính tổng cho mỗi khoảng
                budget_range_counts = budget_df.groupby('range')['count'].sum().reset_index()
                
                # Lưu DataFrame phân bố ngân sách vào CSV
                budget_csv = OP_ANALYSIS_DIR / "budget_distribution.csv"
                budget_range_counts.to_csv(budget_csv, index=False, encoding='utf-8-sig')
                logger.info(f"Đã lưu phân bố ngân sách vào {budget_csv}")
            
            # Tạo DataFrame cho phân bố mục đích sử dụng
            purpose_counter = Counter()
            for op in self.op_analysis:
                for purpose in op.get('purposes', []):
                    purpose_counter[purpose] += 1
                    
            if purpose_counter:
                purpose_rows = [{'purpose': purpose, 'count': count} for purpose, count in purpose_counter.most_common()]
                purpose_df = pd.DataFrame(purpose_rows)
                
                # Lưu DataFrame phân bố mục đích sử dụng vào CSV
                purpose_csv = OP_ANALYSIS_DIR / "purpose_distribution.csv"
                purpose_df.to_csv(purpose_csv, index=False, encoding='utf-8-sig')
                logger.info(f"Đã lưu phân bố mục đích sử dụng vào {purpose_csv}")
            
            # Tạo DataFrame cho phân bố yêu cầu đặc biệt
            req_counter = Counter()
            for op in self.op_analysis:
                for req in op.get('special_requirements', []):
                    req_counter[req] += 1
                    
            if req_counter:
                req_rows = [{'requirement': req, 'count': count} for req, count in req_counter.most_common()]
                req_df = pd.DataFrame(req_rows)
                
                # Lưu DataFrame phân bố yêu cầu đặc biệt vào CSV
                req_csv = OP_ANALYSIS_DIR / "special_req_distribution.csv"
                req_df.to_csv(req_csv, index=False, encoding='utf-8-sig')
                logger.info(f"Đã lưu phân bố yêu cầu đặc biệt vào {req_csv}")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo CSV cho phân tích OP: {str(e)}")
            return False
        
    def create_purpose_distribution_file(self):
        """Tạo file phân tích phân bố mục đích sử dụng từ dữ liệu đã phân tích"""
        if not self.op_analysis:
            if not self.run_analysis():
                logger.error("Không thể tạo file purpose_distribution.csv: không có dữ liệu phân tích OP")
                return False
        
        try:
            # Đếm số lượng mỗi mục đích
            purpose_counter = Counter()
            for op in self.op_analysis:
                for purpose in op.get('purposes', []):
                    purpose_counter[purpose] += 1
            
            # Tạo danh sách hàng cho DataFrame
            purpose_rows = [{'purpose': purpose, 'count': count} 
                            for purpose, count in purpose_counter.most_common()]
            
            # Tạo DataFrame
            purpose_df = pd.DataFrame(purpose_rows)
            
            # Thư mục đầu ra
            output_file = OP_ANALYSIS_DIR / "purpose_distribution.csv"
            
            # Lưu vào CSV
            purpose_df.to_csv(output_file, index=False)
            
            logger.info(f"Đã tạo file purpose_distribution.csv với {len(purpose_rows)} mục đích sử dụng")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo file purpose_distribution.csv: {str(e)}")
            return False
    
    def run_analysis(self):
        """Chạy toàn bộ quá trình phân tích OP"""
        self.load_thread_files()
        self.analyze_all_ops()
        self.save_op_analysis()
        
        self.create_purpose_distribution_file()
        return self.op_analysis


if __name__ == "__main__":
    # Chạy phân tích OP
    analyzer = OPAnalyzer()
    analyzer.run_analysis()