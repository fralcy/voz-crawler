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
REPLY_ANALYSIS_DIR = DATA_DIR / "analysis" / "reply_analysis"
REPLY_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

class ReplyAnalyzer:
    """
    Class chuyên phân tích các bài trả lời (reply) trong thread
    """
    def __init__(self, threads_dir=PROCESSED_DATA_DIR):
        self.threads_dir = threads_dir
        self.threads_data = []
        self.reply_analysis = []
        
        # Dictionary cho các thành phần máy tính phổ biến
        self.component_keywords = {
            'cpu': [
                'cpu', 'processor', 'intel', 'amd', 'ryzen', 'core i', 'i3', 'i5', 'i7', 'i9', 
                'threadripper', 'xeon', 'athlon', 'pentium', 'celeron', 'phenom'
            ],
            'mainboard': [
                'mainboard', 'motherboard', 'mobo', 'main', 'bo mạch', 'bo mạch chủ', 
                'asus', 'msi', 'gigabyte', 'asrock', 'b660', 'b760', 'z690', 'z790', 'b550', 'x570',
                'h610', 'h770'
            ],
            'ram': [
                'ram', 'memory', 'bộ nhớ', 'corsair', 'kingston', 'g.skill', 'crucial', 
                'ddr4', 'ddr5', 'dimm', 'mhz', '16gb', '32gb', '8gb'
            ],
            'gpu': [
                'gpu', 'graphics card', 'card màn hình', 'vga', 'display card', 'rtx', 'gtx', 'rx', 
                'nvidia', 'amd', 'geforce', 'radeon', '3050', '3060', '3070', '4060', '6600', '6700'
            ],
            'ssd': [
                'ssd', 'solid state drive', 'ổ cứng', 'wd', 'western digital', 'samsung', 'kingston', 'crucial',
                'nvme', 'm.2', 'sata', '500gb', '1tb', '2tb'
            ],
            'hdd': [
                'hdd', 'hard disk', 'hard drive', 'ổ cứng', 'seagate', 'toshiba', 'wd', 'western digital',
                '1tb', '2tb', '4tb', '7200rpm'
            ],
            'psu': [
                'psu', 'power supply', 'nguồn', 'corsair', 'cooler master', 'evga', 'seasonic', 
                'thermaltake', 'fsp', 'xigmatek', 'deepcool', 'antec',
                '550w', '650w', '750w', '850w', '1000w', 'gold', 'bronze', 'platinum'
            ],
            'case': [
                'case', 'vỏ máy', 'vỏ case', 'thùng máy', 'chassis', 'nzxt', 'lian li', 'corsair', 
                'cooler master', 'thermaltake', 'deepcool', 'sama'
            ],
            'cooling': [
                'cooling', 'cooler', 'tản nhiệt', 'aio', 'water cooling', 'liquid cooling', 'air cooling', 
                'fan', 'quạt', 'heatsink', 'radiator', 'noctua', 'deepcool', 'cooler master', 'corsair'
            ],
            'monitor': [
                'monitor', 'màn hình', 'display', 'lg', 'dell', 'samsung', 'aoc', 'asus', 'viewsonic',
                'benq', 'msi', 'gigabyte', 'acer', 'alienware', 'inch', '24"', '27"', '32"',
                '75hz', '144hz', '165hz', '240hz', 'fullhd', 'qhd', '4k', 'hdr', 'ips', 'va', 'tn'
            ]
        }
        
        # Regex patterns để tìm giá tiền
        self.price_patterns = [
            r'gi[áa]\s*(?:kho[ảả]ng|t[ầà]m)?\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r'(?:kho[ảả]ng|t[ầà]m)?\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r'(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)'
        ]
        
        # Thương hiệu linh kiện phổ biến
        self.brand_keywords = {
            'intel': ['intel', 'core i', 'pentium', 'celeron', 'xeon'],
            'amd': ['amd', 'ryzen', 'threadripper', 'athlon', 'phenom'],
            'nvidia': ['nvidia', 'rtx', 'gtx', 'geforce'],
            'radeon': ['radeon', 'rx', 'amd graphics'],
            'asus': ['asus', 'rog', 'tuf', 'prime', 'strix'],
            'gigabyte': ['gigabyte', 'aorus'],
            'msi': ['msi', 'meg', 'mpg', 'mag'],
            'asrock': ['asrock', 'taichi', 'phantom gaming'],
            'corsair': ['corsair', 'vengeance', 'dominator'],
            'kingston': ['kingston', 'hyperx', 'fury'],
            'samsung': ['samsung', 'evo', 'pro', 'qvo'],
            'western_digital': ['western digital', 'wd', 'blue', 'black', 'green'],
            'seagate': ['seagate', 'barracuda', 'firecuda'],
            'gskill': ['g.skill', 'trident', 'ripjaws'],
            'crucial': ['crucial', 'ballistix', 'mx'],
            'nzxt': ['nzxt', 'h510', 'h710', 'kraken'],
            'cooler_master': ['cooler master', 'cm', 'masterbox', 'hyper'],
            'thermaltake': ['thermaltake', 'view', 'core', 'versa'],
            'lian_li': ['lian li', 'lancool', 'o11', 'dynamic'],
            'deepcool': ['deepcool', 'matrexx', 'gammaxx'],
            'seasonic': ['seasonic', 'focus', 'prime'],
            'evga': ['evga', 'supernova', 'g2', 'g3', 'p2'],
            'noctua': ['noctua', 'nh-d15', 'nh-u12', 'nh-l9'],
            'arctic': ['arctic', 'freezer', 'mx', 'liquid'],
            'logitech': ['logitech', 'g502', 'g305', 'g pro', 'gpro'],
            'steelseries': ['steelseries', 'rival', 'sensei', 'apex'],
            'razer': ['razer', 'deathadder', 'viper', 'blackwidow', 'hunstman'],
            'hyperx': ['hyperx', 'alloy', 'cloud'],
            'be_quiet': ['be quiet', 'dark rock', 'pure rock', 'silent wings'],
            'phanteks': ['phanteks', 'p500', 'p400', 'enthoo']
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
    
    def detect_components_in_text(self, text):
        """Phát hiện các thành phần máy tính trong văn bản"""
        if not text:
            return {}
            
        # Chuẩn bị văn bản
        text = self.preprocess_text(text)
        
        # Tìm kiếm các từ khóa thành phần
        found_components = {}
        
        for component, keywords in self.component_keywords.items():
            component_mentions = []
            for keyword in keywords:
                # Tìm tất cả các vị trí của từ khóa
                for match in re.finditer(r'\b' + re.escape(keyword) + r'\b', text):
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(text), match.end() + 100)
                    context = text[start_pos:end_pos]
                    component_mentions.append({
                        'keyword': keyword,
                        'context': context,
                        'position': match.start()
                    })
                    
            if component_mentions:
                # Sắp xếp theo vị trí trong văn bản
                component_mentions.sort(key=lambda x: x['position'])
                found_components[component] = component_mentions
                
        return found_components
    
    def extract_prices_from_text(self, text):
        """Trích xuất giá tiền từ văn bản"""
        if not text:
            return []
            
        # Chuẩn bị văn bản
        text = self.preprocess_text(text)
        
        # Tìm kiếm giá tiền theo các patterns
        prices = []
        
        for pattern in self.price_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    value_str = match.group(1)
                    unit = match.group(2)
                    
                    # Chuẩn hóa về triệu đồng
                    price_in_million = self.normalize_money_value(value_str, unit)
                    
                    # Kiểm tra mức hợp lý (từ 0.1 triệu đến 50 triệu)
                    if price_in_million and 0.1 <= price_in_million <= 50:
                        prices.append({
                            'value': price_in_million,
                            'unit': 'triệu',
                            'original_text': match.group(0)
                        })
                except Exception as e:
                    logger.error(f"Lỗi khi trích xuất giá tiền: {str(e)}")
                    continue
                    
        return prices
    
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
    
    def detect_brands_in_text(self, text):
        """Phát hiện các thương hiệu trong văn bản"""
        if not text:
            return {}
            
        # Chuẩn bị văn bản
        text = self.preprocess_text(text)
        
        # Tìm kiếm các từ khóa thương hiệu
        found_brands = {}
        
        for brand, keywords in self.brand_keywords.items():
            brand_mentions = []
            for keyword in keywords:
                # Tìm tất cả các vị trí của từ khóa
                for match in re.finditer(r'\b' + re.escape(keyword) + r'\b', text):
                    start_pos = max(0, match.start() - 30)
                    end_pos = min(len(text), match.end() + 70)
                    context = text[start_pos:end_pos]
                    brand_mentions.append({
                        'keyword': keyword,
                        'context': context,
                        'position': match.start()
                    })
                    
            if brand_mentions:
                # Sắp xếp theo vị trí trong văn bản
                brand_mentions.sort(key=lambda x: x['position'])
                found_brands[brand] = brand_mentions
                
        return found_brands
    
    def analyze_reply_post(self, post, thread_id):
        """Phân tích một bài trả lời để trích xuất đề xuất linh kiện"""
        if not post:
            return None
            
        # Lấy nội dung bài viết
        content = post.get('content_text', '')
        
        # Phát hiện thành phần máy tính được đề cập
        components = self.detect_components_in_text(content)
        
        # Trích xuất giá tiền
        prices = self.extract_prices_from_text(content)
        
        # Phát hiện thương hiệu
        brands = self.detect_brands_in_text(content)
        
        # Kiểm tra xem có đề xuất linh kiện không
        has_suggestion = len(components) > 0
        
        # Tạo kết quả phân tích cho bài trả lời nếu có đề xuất
        if has_suggestion:
            analysis = {
                'thread_id': thread_id,
                'post_id': post.get('post_id', ''),
                'user': post.get('author', {}).get('username', ''),
                'post_date': post.get('created_date', ''),
                'components': components,
                'prices': prices,
                'brands': brands,
                'reactions': post.get('reactions', {}),
                'has_images': len(post.get('images', [])) > 0,
                'content_length': len(content)
            }
            
            return analysis
            
        return None
    
    def analyze_thread_replies(self, thread_data):
        """Phân tích tất cả các bài trả lời trong một thread"""
        if not thread_data or 'posts' not in thread_data or len(thread_data['posts']) <= 1:
            return []
            
        thread_id = thread_data.get('thread_id', '')
        
        # Lấy các bài trả lời (bỏ qua bài đầu tiên)
        reply_posts = thread_data['posts'][1:]
        
        thread_analyses = []
        
        for post in reply_posts:
            analysis = self.analyze_reply_post(post, thread_id)
            if analysis:
                thread_analyses.append(analysis)
                
        return thread_analyses
    
    def analyze_all_replies(self):
        """Phân tích tất cả các bài trả lời trong tất cả các thread"""
        if not self.threads_data:
            self.load_thread_files()
            
        self.reply_analysis = []
        total_replies = 0
        total_with_suggestions = 0
        
        for i, thread_data in enumerate(self.threads_data):
            try:
                logger.info(f"Đang phân tích replies của thread {i+1}/{len(self.threads_data)}: {thread_data.get('thread_id', '')}")
                
                # Đếm số lượng bài trả lời trong thread này
                if 'posts' in thread_data and len(thread_data['posts']) > 1:
                    thread_reply_count = len(thread_data['posts']) - 1
                    total_replies += thread_reply_count
                    
                    # Phân tích replies
                    thread_analyses = self.analyze_thread_replies(thread_data)
                    
                    if thread_analyses:
                        self.reply_analysis.extend(thread_analyses)
                        total_with_suggestions += len(thread_analyses)
                        
                # Log tiến độ
                if (i + 1) % 10 == 0 or i == len(self.threads_data) - 1:
                    logger.info(f"Đã phân tích {i+1}/{len(self.threads_data)} threads")
                    
            except Exception as e:
                logger.error(f"Lỗi khi phân tích replies của thread {thread_data.get('thread_id', '')}: {str(e)}")
                continue
                
        logger.info(f"Đã phân tích xong {total_with_suggestions}/{total_replies} replies có đề xuất")
        
        return self.reply_analysis
    
    def save_reply_analysis(self, filename="reply_analysis.json"):
        """Lưu kết quả phân tích replies vào file JSON"""
        if not self.reply_analysis:
            logger.warning("Không có dữ liệu phân tích replies để lưu")
            return False
            
        try:
            # Tạo thư mục nếu chưa tồn tại
            REPLY_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Lưu dữ liệu phân tích
            output_file = REPLY_ANALYSIS_DIR / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.reply_analysis, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Đã lưu kết quả phân tích replies vào {output_file}")
            
            # Tạo file CSV cho phân tích
            self.create_reply_analysis_csv()
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả phân tích replies: {str(e)}")
            return False
    
    def create_reply_analysis_csv(self):
        """Tạo file CSV từ dữ liệu phân tích replies để dễ dàng phân tích hơn"""
        if not self.reply_analysis:
            logger.warning("Không có dữ liệu phân tích replies để tạo CSV")
            return False
            
        try:
            # Tạo DataFrame cho tổng quan về replies
            reply_rows = []
            
            for reply in self.reply_analysis:
                # Đếm số lượng thành phần được đề cập
                component_counts = {component: len(mentions) for component, mentions in reply.get('components', {}).items()}
                
                # Đếm số lượng thương hiệu được đề cập
                brand_counts = {brand: len(mentions) for brand, mentions in reply.get('brands', {}).items()}
                
                # Tổng hợp các giá trị khác
                row = {
                    'thread_id': reply.get('thread_id', ''),
                    'post_id': reply.get('post_id', ''),
                    'user': reply.get('user', ''),
                    'post_date': reply.get('post_date', ''),
                    'component_count': sum(len(mentions) for mentions in reply.get('components', {}).values()),
                    'price_count': len(reply.get('prices', [])),
                    'brand_count': sum(len(mentions) for mentions in reply.get('brands', {}).values()),
                    'has_images': reply.get('has_images', False),
                    'content_length': reply.get('content_length', 0),
                    'likes': reply.get('reactions', {}).get('Like', 0),
                    'thanks': reply.get('reactions', {}).get('Thanks', 0)
                }
                
                # Thêm số lượng từng loại thành phần
                for component_type in self.component_keywords.keys():
                    row[f'has_{component_type}'] = component_type in reply.get('components', {})
                    row[f'{component_type}_count'] = component_counts.get(component_type, 0)
                
                reply_rows.append(row)
                
            # Tạo DataFrame cho tổng quan về replies
            reply_df = pd.DataFrame(reply_rows)
            
            # Lưu DataFrame tổng quan vào CSV
            reply_csv = REPLY_ANALYSIS_DIR / "reply_overview.csv"
            reply_df.to_csv(reply_csv, index=False, encoding='utf-8-sig')
            logger.info(f"Đã lưu tổng quan replies vào {reply_csv}")
            
            # Tạo DataFrame cho thành phần được đề xuất
            component_rows = []
            
            for reply in self.reply_analysis:
                thread_id = reply.get('thread_id', '')
                post_id = reply.get('post_id', '')
                user = reply.get('user', '')
                
                # Duyệt qua từng loại thành phần
                for component_type, mentions in reply.get('components', {}).items():
                    for mention in mentions:
                        row = {
                            'thread_id': thread_id,
                            'post_id': post_id,
                            'user': user,
                            'component_type': component_type,
                            'keyword': mention.get('keyword', ''),
                            'context': mention.get('context', ''),
                            'has_images': reply.get('has_images', False),
                            'likes': reply.get('reactions', {}).get('Like', 0),
                            'thanks': reply.get('reactions', {}).get('Thanks', 0)
                        }
                        
                        component_rows.append(row)
                        
            # Tạo DataFrame cho thành phần được đề xuất
            if component_rows:
                component_df = pd.DataFrame(component_rows)
                component_csv = REPLY_ANALYSIS_DIR / "component_suggestions.csv"
                component_df.to_csv(component_csv, index=False, encoding='utf-8-sig')
                logger.info(f"Đã lưu đề xuất thành phần vào {component_csv}")
            
            # Tạo DataFrame cho giá tiền được đề xuất
            price_rows = []
            
            for reply in self.reply_analysis:
                thread_id = reply.get('thread_id', '')
                post_id = reply.get('post_id', '')
                user = reply.get('user', '')
                
                # Duyệt qua từng giá tiền
                for price in reply.get('prices', []):
                    row = {
                        'thread_id': thread_id,
                        'post_id': post_id,
                        'user': user,
                        'price_value': price.get('value', 0),
                        'original_text': price.get('original_text', ''),
                        'has_images': reply.get('has_images', False),
                        'likes': reply.get('reactions', {}).get('Like', 0),
                        'thanks': reply.get('reactions', {}).get('Thanks', 0)
                    }
                    
                    price_rows.append(row)
                    
            # Tạo DataFrame cho giá tiền được đề xuất
            if price_rows:
                price_df = pd.DataFrame(price_rows)
                price_csv = REPLY_ANALYSIS_DIR / "price_suggestions.csv"
                price_df.to_csv(price_csv, index=False, encoding='utf-8-sig')
                logger.info(f"Đã lưu đề xuất giá tiền vào {price_csv}")
            
            # Tạo DataFrame cho tần suất thành phần
            component_counter = Counter()
            for reply in self.reply_analysis:
                for component_type in reply.get('components', {}).keys():
                    component_counter[component_type] += 1
                    
            if component_counter:
                freq_rows = [{'component_type': comp, 'count': count, 'percentage': count / len(self.reply_analysis) * 100}
                              for comp, count in component_counter.most_common()]
                freq_df = pd.DataFrame(freq_rows)
                freq_csv = REPLY_ANALYSIS_DIR / "component_frequency.csv"
                freq_df.to_csv(freq_csv, index=False, encoding='utf-8-sig')
                logger.info(f"Đã lưu tần suất thành phần vào {freq_csv}")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo CSV cho phân tích replies: {str(e)}")
            return False
    
    def run_analysis(self):
        """Chạy toàn bộ quá trình phân tích replies"""
        self.load_thread_files()
        self.analyze_all_replies()
        self.save_reply_analysis()
        
        return self.reply_analysis


if __name__ == "__main__":
    # Chạy phân tích replies
    analyzer = ReplyAnalyzer()
    analyzer.run_analysis()