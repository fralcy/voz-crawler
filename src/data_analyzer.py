import os
import json
import logging
import re
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
import unicodedata
import string

from config import PROCESSED_DATA_DIR, DATA_DIR

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Tạo thư mục cho dữ liệu phân tích
ANALYSIS_DIR = DATA_DIR / "analysis"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

class DataAnalyzer:
    """
    Class phân tích dữ liệu từ các thread VOZ đã crawler
    """
    def __init__(self, threads_dir=PROCESSED_DATA_DIR):
        self.threads_dir = threads_dir
        self.threads_data = []
        self.normalized_data = []
        
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
        
        # Regex patterns để tìm ngân sách
        self.budget_patterns = [
            r'ng[aâ]n\s*s[áa]ch\s*(?:kho[ảả]ng|t[ầà]m|\:|\s)\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r'bu[dđ]ge[dt]\s*(?:kho[ảả]ng|t[ầà]m|\:|\s)\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r't[ổố]ng\s*(?:chi\s*ph[íi]|gi[áa])\s*(?:kho[ảả]ng|t[ầà]m|\:|\s)\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r'kho[ảả]ng\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r't[ầà]m\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
            r'(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
        ]
        
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
        """Tiền xử lý văn bản: chuyển về chữ thường, loại bỏ ký tự đặc biệt"""
        if not text:
            return ""
            
        # Chuyển về chữ thường
        text = text.lower()
        
        # Chuẩn hóa Unicode (chuyển từ NFKD sang NFC)
        text = unicodedata.normalize('NFC', text)
        
        # Loại bỏ các ký tự không phải chữ cái, số, dấu cách và một số dấu câu cơ bản
        allowed_chars = string.ascii_lowercase + string.digits + 'áàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ. ,:-+'
        text = ''.join(c for c in text if c in allowed_chars)
        
        # Thay thế nhiều dấu cách liên tiếp bằng một dấu cách
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
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
        
    def extract_special_requirements(self, text):
        """Trích xuất các yêu cầu đặc biệt từ văn bản"""
        special_requirements = []
        
        # Từ khóa cho các yêu cầu đặc biệt
        keywords = {
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
        
        text = self.preprocess_text(text)
        
        for requirement, terms in keywords.items():
            for term in terms:
                if term in text:
                    special_requirements.append(requirement)
                    break
                    
        return special_requirements
        
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
        
        # Trích xuất thành phần từ nội dung OP
        components = self.detect_components_in_text(content)
        
        # Trích xuất yêu cầu đặc biệt
        special_requirements = self.extract_special_requirements(title + ' ' + content)
        
        # Kết hợp thông tin từ tiêu đề và nội dung
        budget = title_budget if title_budget else content_budget
        purposes = list(set(title_purposes + content_purposes))
        
        # Tạo kết quả phân tích
        result = {
            'thread_id': thread_data.get('thread_id', ''),
            'title': title,
            'budget': budget,
            'purposes': purposes,
            'components_mentioned': components,
            'special_requirements': special_requirements,
            'user': op_post.get('author', {}).get('username', ''),
            'post_date': op_post.get('created_date', '')
        }
        
        return result
        
    def analyze_reply_posts(self, thread_data):
        """Phân tích các bài trả lời để trích xuất đề xuất linh kiện"""
        if not thread_data or 'posts' not in thread_data or not thread_data['posts']:
            return []
            
        # Lấy các bài trả lời (bỏ qua bài đầu tiên)
        reply_posts = thread_data['posts'][1:]
        
        analyzed_replies = []
        
        for post in reply_posts:
            # Lấy nội dung bài viết
            content = post.get('content_text', '')
            
            # Phát hiện thành phần máy tính được đề cập
            components = self.detect_components_in_text(content)
            
            # Kiểm tra xem có đề xuất linh kiện không
            has_suggestion = len(components) > 0
            
            # Trích xuất yêu cầu đặc biệt
            special_notes = self.extract_special_requirements(content)
            
            # Tìm các nhắc tới đến giá cả
            prices = []
            price_patterns = [
                r'giá\s*(?:khoảng|tầm)?\s*(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)',
                r'(\d+[.,]?\d*)\s*(t[rỉ]|k|m|triệu|nghìn|tr|ngàn|đồng)'
            ]
            
            for pattern in price_patterns:
                matches = re.finditer(pattern, self.preprocess_text(content))
                for match in matches:
                    try:
                        value_str = match.group(1)
                        unit = match.group(2)
                        price_in_million = self.normalize_money_value(value_str, unit)
                        if price_in_million and 0.1 <= price_in_million <= 50:  # Giá từ 100k đến 50tr
                            prices.append({
                                'value': price_in_million,
                                'unit': 'triệu',
                                'original_text': match.group(0)
                            })
                    except:
                        continue
            
            # Tạo kết quả phân tích cho bài trả lời
            if has_suggestion:
                analyzed_reply = {
                    'post_id': post.get('post_id', ''),
                    'user': post.get('author', {}).get('username', ''),
                    'post_date': post.get('created_date', ''),
                    'components': components,
                    'special_notes': special_notes,
                    'prices': prices,
                    'reactions': post.get('reactions', {}),
                    'has_images': len(post.get('images', [])) > 0,
                    'content_length': len(content)
                }
                
                analyzed_replies.append(analyzed_reply)
                
        return analyzed_replies
        
    def normalize_thread_data(self, thread_data):
        """Chuẩn hóa dữ liệu của thread để có định dạng thống nhất cho phân tích"""
        if not thread_data:
            return None
            
        # Phân tích OP
        op_analysis = self.analyze_op_post(thread_data)
        
        # Phân tích replies
        replies_analysis = self.analyze_reply_posts(thread_data)
        
        # Tạo dữ liệu chuẩn hóa
        normalized_data = {
            'thread_id': thread_data.get('thread_id', ''),
            'title': thread_data.get('title', ''),
            'url': thread_data.get('url', ''),
            'op_analysis': op_analysis,
            'replies_analysis': replies_analysis,
            'total_posts': len(thread_data.get('posts', [])),
            'total_replies': len(thread_data.get('posts', [])) - 1 if len(thread_data.get('posts', [])) > 0 else 0,
            'total_suggestions': len(replies_analysis)
        }
        
        return normalized_data
        
    def run_analysis(self):
        """Chạy phân tích tất cả các threads"""
        if not self.threads_data:
            self.load_thread_files()
            
        if not self.threads_data:
            logger.error("Không có threads để phân tích")
            return None
            
        self.normalized_data = []
        
        # Phân tích từng thread
        for i, thread_data in enumerate(self.threads_data):
            try:
                logger.info(f"Đang phân tích thread {i+1}/{len(self.threads_data)}: {thread_data.get('thread_id', '')}")
                
                # Chuẩn hóa dữ liệu
                normalized = self.normalize_thread_data(thread_data)
                
                if normalized:
                    self.normalized_data.append(normalized)
                    
                # Log tiến độ
                if (i + 1) % 10 == 0 or i == len(self.threads_data) - 1:
                    logger.info(f"Đã phân tích {i+1}/{len(self.threads_data)} threads")
                    
            except Exception as e:
                logger.error(f"Lỗi khi phân tích thread {thread_data.get('thread_id', '')}: {str(e)}")
                continue
                
        logger.info(f"Đã phân tích xong {len(self.normalized_data)}/{len(self.threads_data)} threads")
        
        # Lưu dữ liệu đã phân tích
        self.save_analysis_results()
        
        return self.normalized_data
        
    def save_analysis_results(self, filename="analysis_results.json"):
        """Lưu kết quả phân tích vào file JSON"""
        if not self.normalized_data:
            logger.warning("Không có dữ liệu phân tích để lưu")
            return False
            
        try:
            # Tạo thư mục nếu chưa tồn tại
            ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Lưu dữ liệu phân tích
            output_file = ANALYSIS_DIR / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.normalized_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Đã lưu kết quả phân tích vào {output_file}")
            
            # Tạo file CSV cho phân tích
            self.create_analysis_csv()
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả phân tích: {str(e)}")
            return False
            
    def create_analysis_csv(self):
        """Tạo file CSV từ dữ liệu phân tích để dễ dàng phân tích hơn"""
        if not self.normalized_data:
            logger.warning("Không có dữ liệu phân tích để tạo CSV")
            return False
            
        try:
            # Tạo DataFrame cho thread và OP
            thread_rows = []
            
            for thread in self.normalized_data:
                op = thread.get('op_analysis', {})
                
                row = {
                    'thread_id': thread.get('thread_id', ''),
                    'title': thread.get('title', ''),
                    'url': thread.get('url', ''),
                    'total_posts': thread.get('total_posts', 0),
                    'total_replies': thread.get('total_replies', 0),
                    'total_suggestions': thread.get('total_suggestions', 0),
                    'op_user': op.get('user', ''),
                    'post_date': op.get('post_date', ''),
                    'budget': op.get('budget', {}).get('value', None),
                    'purposes': ','.join(op.get('purposes', [])),
                    'special_requirements': ','.join(op.get('special_requirements', []))
                }
                
                thread_rows.append(row)
                
            # Tạo DataFrame cho threads
            threads_df = pd.DataFrame(thread_rows)
            
            # Lưu DataFrame threads vào CSV
            threads_csv = ANALYSIS_DIR / "threads_analysis.csv"
            threads_df.to_csv(threads_csv, index=False, encoding='utf-8-sig')
            logger.info(f"Đã lưu phân tích threads vào {threads_csv}")
            
            # Tạo DataFrame cho các đề xuất linh kiện
            suggestion_rows = []
            
            for thread in self.normalized_data:
                thread_id = thread.get('thread_id', '')
                op = thread.get('op_analysis', {})
                budget = op.get('budget', {}).get('value', None)
                purposes = op.get('purposes', [])
                
                # Lấy các đề xuất từ replies
                for reply in thread.get('replies_analysis', []):
                    # Duyệt qua từng loại linh kiện được đề xuất
                    components = reply.get('components', {})
                    for component_type, mentions in components.items():
                        for mention in mentions:
                            row = {
                                'thread_id': thread_id,
                                'post_id': reply.get('post_id', ''),
                                'user': reply.get('user', ''),
                                'post_date': reply.get('post_date', ''),
                                'component_type': component_type,
                                'keyword': mention.get('keyword', ''),
                                'context': mention.get('context', ''),
                                'budget': budget,
                                'purposes': ','.join(purposes),
                                'has_images': reply.get('has_images', False),
                                'likes': reply.get('reactions', {}).get('Like', 0),
                                'thanks': reply.get('reactions', {}).get('Thanks', 0)
                            }
                            suggestion_rows.append(row)
            
            # Tạo DataFrame cho đề xuất linh kiện
            if suggestion_rows:
                suggestions_df = pd.DataFrame(suggestion_rows)
                suggestions_csv = ANALYSIS_DIR / "component_suggestions.csv"
                suggestions_df.to_csv(suggestions_csv, index=False, encoding='utf-8-sig')
                logger.info(f"Đã lưu phân tích đề xuất linh kiện vào {suggestions_csv}")
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo CSV: {str(e)}")
            return False
    
    def create_budget_distribution_csv(self):
        """Tạo phân tích phân bố ngân sách"""
        if not self.normalized_data:
            logger.warning("Không có dữ liệu phân tích để tạo phân bố ngân sách")
            return False
            
        try:
            budget_data = []
            
            for thread in self.normalized_data:
                op = thread.get('op_analysis', {})
                budget = op.get('budget', {}).get('value', None)
                
                if budget:
                    row = {
                        'thread_id': thread.get('thread_id', ''),
                        'title': thread.get('title', ''),
                        'budget': budget,
                        'purposes': ','.join(op.get('purposes', [])),
                        'total_suggestions': thread.get('total_suggestions', 0)
                    }
                    budget_data.append(row)
                    
            if budget_data:
                budget_df = pd.DataFrame(budget_data)
                budget_csv = ANALYSIS_DIR / "budget_distribution.csv"
                budget_df.to_csv(budget_csv, index=False, encoding='utf-8-sig')
                logger.info(f"Đã lưu phân tích phân bố ngân sách vào {budget_csv}")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo phân bố ngân sách: {str(e)}")
            return False
    
    def create_purpose_analysis_csv(self):
        """Tạo phân tích mục đích sử dụng"""
        if not self.normalized_data:
            logger.warning("Không có dữ liệu phân tích để tạo phân tích mục đích")
            return False
            
        try:
            # Đếm số lượng mỗi mục đích
            purpose_counts = Counter()
            
            for thread in self.normalized_data:
                op = thread.get('op_analysis', {})
                purposes = op.get('purposes', [])
                
                for purpose in purposes:
                    purpose_counts[purpose] += 1
            
            # Tạo DataFrame cho phân tích mục đích
            purpose_rows = []
            
            for purpose, count in purpose_counts.most_common():
                row = {
                    'purpose': purpose,
                    'count': count,
                    'percentage': count / len(self.normalized_data) * 100
                }
                purpose_rows.append(row)
                
            if purpose_rows:
                purpose_df = pd.DataFrame(purpose_rows)
                purpose_csv = ANALYSIS_DIR / "purpose_analysis.csv"
                purpose_df.to_csv(purpose_csv, index=False, encoding='utf-8-sig')
                logger.info(f"Đã lưu phân tích mục đích sử dụng vào {purpose_csv}")
                
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo phân tích mục đích: {str(e)}")
            return False
    
    def create_component_frequency_csv(self):
        """Tạo phân tích tần suất linh kiện"""
        if not self.normalized_data:
            logger.warning("Không có dữ liệu phân tích để tạo phân tích tần suất linh kiện")
            return False
            
        try:
            # Đếm số lượng đề cập đến từng linh kiện
            component_counts = defaultdict(Counter)
            
            for thread in self.normalized_data:
                replies = thread.get('replies_analysis', [])
                
                for reply in replies:
                    components = reply.get('components', {})
                    
                    for component_type, mentions in components.items():
                        for mention in mentions:
                            keyword = mention.get('keyword', '')
                            component_counts[component_type][keyword] += 1
            
            # Tạo DataFrame cho từng loại linh kiện
            for component_type, keyword_counts in component_counts.items():
                component_rows = []
                
                for keyword, count in keyword_counts.most_common():
                    row = {
                        'component_type': component_type,
                        'keyword': keyword,
                        'count': count,
                        'percentage': count / sum(keyword_counts.values()) * 100
                    }
                    component_rows.append(row)
                    
                if component_rows:
                    component_df = pd.DataFrame(component_rows)
                    component_csv = ANALYSIS_DIR / f"{component_type}_frequency.csv"
                    component_df.to_csv(component_csv, index=False, encoding='utf-8-sig')
                    logger.info(f"Đã lưu phân tích tần suất {component_type} vào {component_csv}")
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tạo phân tích tần suất linh kiện: {str(e)}")
            return False
    
    def run_full_analysis(self):
        """Chạy toàn bộ quá trình phân tích và tạo dataset"""
        self.load_thread_files()
        self.run_analysis()
        self.create_budget_distribution_csv()
        self.create_purpose_analysis_csv()
        self.create_component_frequency_csv()
        
        return self.normalized_data


if __name__ == "__main__":
    # Chạy phân tích dữ liệu
    analyzer = DataAnalyzer()
    analyzer.run_full_analysis()