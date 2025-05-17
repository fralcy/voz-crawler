# sentiment_analyzer.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import logging
import re
import string
import unicodedata
from pathlib import Path
from textblob import TextBlob
from collections import Counter

from config import DATA_DIR

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create directory for sentiment analysis
SENTIMENT_DIR = DATA_DIR / "analysis" / "sentiment_analysis"
SENTIMENT_DIR.mkdir(parents=True, exist_ok=True)

class SentimentAnalyzer:
    """
    Class for analyzing sentiment in VOZ replies
    """
    def __init__(self, analysis_dir=DATA_DIR / "analysis"):
        self.analysis_dir = analysis_dir
        self.reply_analysis_path = analysis_dir / "reply_analysis" / "reply_analysis.json"
        self.component_suggestions_path = analysis_dir / "component_suggestions.csv"
        
        # Sentiment data
        self.sentiment_data = None
        self.component_sentiment = None
        
    def load_data(self):
        """Load data from analysis files"""
        try:
            # Load reply data
            if not self.reply_analysis_path.exists():
                logger.warning(f"Reply analysis file not found: {self.reply_analysis_path}")
                return False
                
            with open(self.reply_analysis_path, 'r', encoding='utf-8') as f:
                self.reply_data = json.load(f)
                
            # Load component suggestions if available
            if Path(self.component_suggestions_path).exists():
                self.component_suggestions = pd.read_csv(self.component_suggestions_path)
                logger.info(f"Loaded {len(self.component_suggestions)} component suggestions")
            else:
                self.component_suggestions = None
                logger.warning(f"Component suggestions file not found: {self.component_suggestions_path}")
                
            logger.info(f"Loaded {len(self.reply_data)} replies")
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return False
    
    def preprocess_text(self, text):
        """Preprocess text for sentiment analysis"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Normalize Unicode
        text = unicodedata.normalize('NFC', text)
        
        # Remove URLs
        text = re.sub(r'http\S+', '', text)
        
        # Remove numbers
        text = re.sub(r'\d+', '', text)
        
        # Remove punctuation
        translator = str.maketrans('', '', string.punctuation)
        text = text.translate(translator)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def analyze_reply_sentiment(self):
        """Analyze sentiment in replies"""
        if not hasattr(self, 'reply_data'):
            if not self.load_data():
                return None
                
        try:
            sentiment_rows = []
            
            for reply in self.reply_data:
                # Extract component contexts
                component_texts = []
                
                for component_type, mentions in reply.get('components', {}).items():
                    for mention in mentions:
                        component_texts.append({
                            'component_type': component_type,
                            'keyword': mention.get('keyword', ''),
                            'context': mention.get('context', '')
                        })
                
                # Skip if no component mentions
                if not component_texts:
                    continue
                
                # Basic reply info
                reply_info = {
                    'thread_id': reply.get('thread_id'),
                    'post_id': reply.get('post_id'),
                    'user': reply.get('user'),
                    'has_images': reply.get('has_images', False),
                    'like_count': reply.get('reactions', {}).get('Like', 0),
                    'thanks_count': reply.get('reactions', {}).get('Thanks', 0)
                }
                
                # Analyze sentiment for each component context
                for component in component_texts:
                    # Clean text for sentiment analysis
                    text = self.preprocess_text(component['context'])
                    
                    # Skip if text is too short
                    if len(text) < 10:
                        continue
                    
                    # Analyze sentiment
                    blob = TextBlob(text)
                    polarity = blob.sentiment.polarity
                    subjectivity = blob.sentiment.subjectivity
                    
                    # Create sentiment category
                    if polarity > 0.1:
                        sentiment_category = 'positive'
                    elif polarity < -0.1:
                        sentiment_category = 'negative'
                    else:
                        sentiment_category = 'neutral'
                    
                    # Create row
                    row = {
                        **reply_info,
                        'component_type': component['component_type'],
                        'keyword': component['keyword'],
                        'context': component['context'][:200] + '...' if len(component['context']) > 200 else component['context'],
                        'sentiment_score': polarity,
                        'subjectivity_score': subjectivity,
                        'sentiment_category': sentiment_category
                    }
                    
                    sentiment_rows.append(row)
            
            # Create DataFrame
            self.sentiment_data = pd.DataFrame(sentiment_rows)
            
            # Save to CSV
            self.sentiment_data.to_csv(SENTIMENT_DIR / "reply_sentiment.csv", index=False)
            
            logger.info(f"Analyzed sentiment in {len(self.sentiment_data)} component contexts")
            return self.sentiment_data
            
        except Exception as e:
            logger.error(f"Error analyzing reply sentiment: {str(e)}")
            return None
    
    def analyze_component_sentiment(self):
        """Analyze sentiment by component type"""
        if self.sentiment_data is None:
            self.analyze_reply_sentiment()
            
        if self.sentiment_data is None:
            logger.error("Cannot analyze component sentiment: sentiment data not available")
            return None
            
        try:
            # Group by component type
            component_sentiment = self.sentiment_data.groupby('component_type').agg({
                'sentiment_score': ['mean', 'median', 'std', 'count'],
                'subjectivity_score': ['mean', 'median', 'std'],
                'sentiment_category': lambda x: x.value_counts().to_dict()
            })
            
            # Flatten multi-index columns
            component_sentiment.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] 
                                           for col in component_sentiment.columns]
            
            # Reset index
            component_sentiment = component_sentiment.reset_index()
            
            # Save to CSV
            component_sentiment.to_csv(SENTIMENT_DIR / "component_sentiment_stats.csv", index=False)
            
            # Create visualization
            plt.figure(figsize=(12, 8), dpi=300)
            
            # Sort by average sentiment
            sorted_df = component_sentiment.sort_values('sentiment_score_mean')
            
            # Create color map based on sentiment score
            colors = ['#ff6666' if score < 0 else '#66ff66' if score > 0 else '#f2f2f2' 
                      for score in sorted_df['sentiment_score_mean']]
            
            # Create bar chart
            ax = plt.bar(
                sorted_df['component_type'], 
                sorted_df['sentiment_score_mean'],
                yerr=sorted_df['sentiment_score_std'],
                color=colors,
                alpha=0.8,
                capsize=5
            )
            
            # Add count labels
            for i, (_, row) in enumerate(sorted_df.iterrows()):
                plt.text(
                    i, 
                    row['sentiment_score_mean'] + 0.01, 
                    f"n={int(row['sentiment_score_count'])}",
                    ha='center'
                )
            
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.title('Average Sentiment Score by Component Type')
            plt.xlabel('Component Type')
            plt.ylabel('Average Sentiment Score')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            plt.savefig(SENTIMENT_DIR / "component_sentiment.png")
            plt.close()
            
            # Create a more detailed visualization showing positive/neutral/negative distribution
            plt.figure(figsize=(14, 8), dpi=300)
            
            # Prepare data for stacked bar chart
            sentiment_categories = ['positive', 'neutral', 'negative']
            stacked_data = []
            
            for _, row in component_sentiment.iterrows():
                categories = row['sentiment_category']
                component = row['component_type']
                
                for category in sentiment_categories:
                    count = categories.get(category, 0)
                    percentage = count / row['sentiment_score_count'] * 100
                    
                    stacked_data.append({
                        'component_type': component,
                        'sentiment': category,
                        'count': count,
                        'percentage': percentage
                    })
            
            # Create DataFrame
            stacked_df = pd.DataFrame(stacked_data)
            
            # Create pivot table for plotting
            pivot_df = stacked_df.pivot(
                index='component_type',
                columns='sentiment',
                values='percentage'
            )
            
            # Fill NaN with 0
            pivot_df = pivot_df.fillna(0)
            
            # Ensure all categories exist
            for category in sentiment_categories:
                if category not in pivot_df.columns:
                    pivot_df[category] = 0
            
            # Sort by positive percentage
            pivot_df = pivot_df.sort_values('positive', ascending=False)
            
            # Create stacked bar chart
            ax = pivot_df.plot(
                kind='bar',
                stacked=True,
                figsize=(14, 8),
                color=['#66ff66', '#f2f2f2', '#ff6666']  # green, grey, red
            )
            
            plt.title('Sentiment Distribution by Component Type')
            plt.xlabel('Component Type')
            plt.ylabel('Percentage (%)')
            plt.legend(title='Sentiment')
            plt.xticks(rotation=45)
            
            # Add percentage labels
            for i, component in enumerate(pivot_df.index):
                positive_pct = pivot_df.loc[component, 'positive']
                neutral_pct = pivot_df.loc[component, 'neutral']
                negative_pct = pivot_df.loc[component, 'negative']
                
                # Label positive percentage if significant
                if positive_pct > 10:
                    plt.text(
                        i, 
                        positive_pct / 2, 
                        f"{positive_pct:.0f}%", 
                        ha='center', 
                        color='black', 
                        fontweight='bold'
                    )
                
                # Label neutral percentage if significant
                if neutral_pct > 10:
                    plt.text(
                        i, 
                        positive_pct + neutral_pct / 2, 
                        f"{neutral_pct:.0f}%", 
                        ha='center', 
                        color='black', 
                        fontweight='bold'
                    )
                
                # Label negative percentage if significant
                if negative_pct > 10:
                    plt.text(
                        i, 
                        positive_pct + neutral_pct + negative_pct / 2, 
                        f"{negative_pct:.0f}%", 
                        ha='center', 
                        color='black', 
                        fontweight='bold'
                    )
            
            plt.tight_layout()
            plt.savefig(SENTIMENT_DIR / "component_sentiment_distribution.png")
            plt.close()
            
            self.component_sentiment = component_sentiment
            
            logger.info("Analyzed sentiment by component type")
            return component_sentiment
            
        except Exception as e:
            logger.error(f"Error analyzing component sentiment: {str(e)}")
            return None
    
    def analyze_sentiment_by_reception(self):
        """Phân tích mối quan hệ giữa sentiment và phản ứng người dùng (likes/thanks)"""
        if self.sentiment_data is None:
            self.analyze_reply_sentiment()
            
        if self.sentiment_data is None:
            logger.error("Không thể phân tích sentiment theo phản ứng: thiếu dữ liệu")
            return None
            
        try:
            # Tạo các nhóm phản ứng
            self.sentiment_data['has_likes'] = self.sentiment_data['like_count'] > 0
            self.sentiment_data['has_thanks'] = self.sentiment_data['thanks_count'] > 0
            
            # Tính giá trị sentiment trung bình theo nhóm phản ứng
            reception_sentiment = self.sentiment_data.groupby(['has_likes', 'has_thanks']).agg({
                'sentiment_score': ['mean', 'median', 'std', 'count'],
                'subjectivity_score': ['mean', 'median', 'std']
            })
            
            # Làm phẳng các cột chỉ mục kép
            reception_sentiment.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] 
                                          for col in reception_sentiment.columns]
            
            # Đặt lại chỉ mục
            reception_sentiment = reception_sentiment.reset_index()
            
            # Lưu vào CSV
            reception_sentiment.to_csv(SENTIMENT_DIR / "sentiment_by_reception.csv", index=False)
            
            # Tạo biểu đồ đơn giản hơn để tránh lỗi
            plt.figure(figsize=(10, 8))

            # Nếu có đủ dữ liệu
            if len(reception_sentiment) > 0:
                # Chuẩn bị dữ liệu
                categories = []
                values = []
                
                for _, row in reception_sentiment.iterrows():
                    category = f"Likes: {'Yes' if row['has_likes'] else 'No'}, Thanks: {'Yes' if row['has_thanks'] else 'No'}"
                    categories.append(category)
                    values.append(row['sentiment_score_mean'])
                
                # Vẽ biểu đồ dạng cột đơn giản
                plt.bar(range(len(categories)), values)
                plt.xticks(range(len(categories)), categories, rotation=45)
                plt.title('Average Sentiment Score by User Reception')
                plt.ylabel('Average Sentiment Score')
            else:
                plt.text(0.5, 0.5, 'No data available', ha='center', va='center')

            plt.tight_layout()
            plt.savefig(SENTIMENT_DIR / "sentiment_by_reception.png")
            plt.close()
            
            logger.info("Đã hoàn thành phân tích sentiment theo phản ứng người dùng")
            return reception_sentiment
        except Exception as e:
            logger.error(f"Lỗi khi phân tích sentiment theo phản ứng: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def analyze_common_words_by_sentiment(self):
        """Analyze most common words for each sentiment category"""
        if self.sentiment_data is None:
            self.analyze_reply_sentiment()
            
        if self.sentiment_data is None:
            logger.error("Cannot analyze common words: sentiment data not available")
            return None
            
        try:
            # Vietnamese stopwords
            stopwords = [
                'và', 'là', 'có', 'của', 'không', 'trong', 'đến', 'được', 'cho', 'những',
                'với', 'các', 'để', 'này', 'người', 'còn', 'về', 'từ', 'lên', 'nhưng',
                'đã', 'ra', 'nếu', 'cũng', 'khi', 'vào', 'như', 'một', 'cái', 'nên',
                'lại', 'rất', 'mà', 'thì', 'tôi', 'bạn', 'mình', 'hơn', 'bị'
            ]
            
            # English stopwords
            stopwords += [
                'the', 'and', 'to', 'of', 'a', 'in', 'is', 'that', 'it', 'with',
                'for', 'as', 'are', 'on', 'be', 'this', 'by', 'an', 'not', 'at',
                'from', 'but', 'or', 'if', 'you', 'can', 'will', 'has', 'have', 'had',
                'they', 'their', 'them', 'there', 'than', 'then', 'some', 'all', 'would',
                'what', 'which', 'when', 'who', 'how', 'any', 'should', 'could', 'was', 'were',
                'your', 'my', 'more', 'less', 'just', 'very', 'also', 'much', 'many', 'most'
            ]
            
            # Analyze words by sentiment category
            word_data = {}
            
            for sentiment in ['positive', 'neutral', 'negative']:
                # Filter data by sentiment
                subset = self.sentiment_data[self.sentiment_data['sentiment_category'] == sentiment]
                
                # Skip if no data
                if len(subset) == 0:
                    continue
                
                # Combine all context texts
                all_text = ' '.join(subset['context'].astype(str).tolist())
                
                # Preprocess text
                all_text = self.preprocess_text(all_text)
                
                # Split into words
                words = all_text.split()
                
                # Remove stopwords
                words = [word for word in words if word not in stopwords and len(word) > 2]
                
                # Count words
                word_counts = Counter(words)
                
                # Get top 50 words
                top_words = word_counts.most_common(50)
                
                # Store data
                word_data[sentiment] = top_words
            
            # Save to JSON
            with open(SENTIMENT_DIR / "common_words_by_sentiment.json", 'w', encoding='utf-8') as f:
                json.dump(word_data, f, ensure_ascii=False, indent=2)
            
            # Create visualization
            for sentiment, words in word_data.items():
                plt.figure(figsize=(12, 8), dpi=300)
                
                # Prepare data for bar chart
                word_df = pd.DataFrame(words, columns=['word', 'count'])
                
                # Take top 20 words
                word_df = word_df.head(20)
                
                # Sort by count
                word_df = word_df.sort_values('count')
                
                # Create horizontal bar chart
                ax = plt.barh(
                    word_df['word'],
                    word_df['count'],
                    color='skyblue' if sentiment == 'positive' else 'lightcoral' if sentiment == 'negative' else 'lightgray'
                )
                
                # Add count labels
                for i, p in enumerate(ax.patches):
                    width = p.get_width()
                    plt.text(
                        width + 1,
                        p.get_y() + p.get_height() / 2.,
                        f'{width}',
                        ha='left',
                        va='center'
                    )
                
                plt.title(f'Most Common Words in {sentiment.capitalize()} Sentiment Contexts')
                plt.xlabel('Count')
                plt.ylabel('Word')
                plt.tight_layout()
                
                plt.savefig(SENTIMENT_DIR / f"common_words_{sentiment}.png")
                plt.close()
            
            logger.info("Analyzed common words by sentiment category")
            return word_data
            
        except Exception as e:
            logger.error(f"Error analyzing common words by sentiment: {str(e)}")
            return None
    
    def run_full_sentiment_analysis(self):
        """Run all sentiment analysis methods"""
        logger.info("Starting full sentiment analysis...")
        
        # Load data
        self.load_data()
        
        # Analyze reply sentiment
        self.analyze_reply_sentiment()
        
        # Analyze component sentiment
        self.analyze_component_sentiment()
        
        # Analyze sentiment by reception
        self.analyze_sentiment_by_reception()
        
        # Analyze common words by sentiment
        self.analyze_common_words_by_sentiment()
        
        logger.info("Completed full sentiment analysis")
        return True


if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    analyzer.run_full_sentiment_analysis()