import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.ticker as ticker
import logging
from wordcloud import WordCloud

from config import DATA_DIR

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set visualization style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("viridis")

# Create directory for visualizations
VISUALIZATION_DIR = DATA_DIR / "analysis" / "visualizations"
VISUALIZATION_DIR.mkdir(parents=True, exist_ok=True)

class VisualizationCreator:
    """
    Class to create advanced visualizations from the analysis data
    """
    def __init__(self, analysis_dir=DATA_DIR / "analysis"):
        self.analysis_dir = analysis_dir
        self.op_analysis_dir = analysis_dir / "op_analysis"
        self.reply_analysis_dir = analysis_dir / "reply_analysis"
        self.budget_analysis_dir = analysis_dir / "budget_analysis"
        self.detailed_analysis_dir = analysis_dir / "detailed_analysis"
        self.network_analysis_dir = analysis_dir / "network_analysis"
        self.sentiment_analysis_dir = analysis_dir / "sentiment_analysis"
        
        # Ensure all directories exist
        for dir_path in [
            self.op_analysis_dir,
            self.reply_analysis_dir,
            self.budget_analysis_dir,
            self.detailed_analysis_dir,
            self.network_analysis_dir,
            self.sentiment_analysis_dir,
            VISUALIZATION_DIR
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Default figure parameters
        self.default_figsize = (12, 8)
        self.default_dpi = 300
        self.title_fontsize = 16
        self.label_fontsize = 12
        self.tick_fontsize = 10
        
        # Custom color palettes
        self.budget_cmap = sns.color_palette("YlGnBu", 8)
        self.component_cmap = sns.color_palette("viridis", 10)
        self.sentiment_cmap = LinearSegmentedColormap.from_list(
            "sentiment", ["#ff6666", "#f2f2f2", "#66ff66"]
        )
        
    def create_budget_component_heatmap(self):
        """Create an enhanced heatmap of budget-component correlation"""
        try:
            # Load data
            file_path = self.detailed_analysis_dir / "budget_component_percentage.csv"
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
                
            data = pd.read_csv(file_path, index_col=0)
            
            # Create figure
            plt.figure(figsize=self.default_figsize, dpi=self.default_dpi)
            
            # Create heatmap with improved styling
            ax = sns.heatmap(
                data,
                annot=True,
                fmt=".1f",
                cmap="YlGnBu",
                linewidths=0.5,
                linecolor='white',
                cbar_kws={'label': 'Percentage (%)'},
                vmin=0,
                vmax=data.values.max() * 1.2  # Set max to 120% of actual max for better color distribution
            )
            
            # Style improvements
            plt.title('Component Distribution by Budget Range', fontsize=self.title_fontsize, pad=20)
            plt.xlabel('Component Type', fontsize=self.label_fontsize)
            plt.ylabel('Budget Range', fontsize=self.label_fontsize)
            plt.xticks(rotation=45, ha='right', fontsize=self.tick_fontsize)
            plt.yticks(fontsize=self.tick_fontsize)
            
            # Add border
            for _, spine in ax.spines.items():
                spine.set_visible(True)
                spine.set_color('black')
                spine.set_linewidth(1)
            
            plt.tight_layout()
            plt.savefig(VISUALIZATION_DIR / "budget_component_heatmap_enhanced.png")
            plt.close()
            
            logger.info("Created enhanced budget-component heatmap")
            return True
            
        except Exception as e:
            logger.error(f"Error creating budget-component heatmap: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_component_trend_chart(self):
        """Create an enhanced chart of component trends over time"""
        try:
            # Load data
            file_path = self.detailed_analysis_dir / "monthly_component_percentage.csv"
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
                
            data = pd.read_csv(file_path, index_col=0)
            
            # Convert index to datetime
            data.index = pd.to_datetime(data.index)
            
            # Create figure
            plt.figure(figsize=(14, 8), dpi=self.default_dpi)
            
            # Select key components
            key_components = ['cpu', 'gpu', 'ram', 'ssd', 'mainboard', 'psu']
            
            # Create color palette for components
            colors = sns.color_palette("viridis", len(key_components))
            
            # Plot each component with enhanced styling
            for i, component in enumerate(key_components):
                if component in data.columns:
                    plt.plot(
                        data.index, 
                        data[component], 
                        label=component.upper(), 
                        linewidth=3, 
                        marker='o',
                        markersize=8,
                        markeredgecolor='white',
                        markeredgewidth=1,
                        color=colors[i]
                    )
            
            # Style improvements
            plt.title('Component Popularity Trends Over Time', fontsize=self.title_fontsize, pad=20)
            plt.xlabel('Date', fontsize=self.label_fontsize)
            plt.ylabel('Percentage of Suggestions (%)', fontsize=self.label_fontsize)
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # Add legend with better positioning and styling
            legend = plt.legend(
                loc='upper right', 
                fontsize=self.label_fontsize,
                frameon=True,
                framealpha=0.9,
                edgecolor='gray'
            )
            
            # Improve tick formatting
            plt.xticks(fontsize=self.tick_fontsize)
            plt.yticks(fontsize=self.tick_fontsize)
            
            # Add annotations for significant events or peaks
            for component in key_components:
                if component in data.columns:
                    # Find the peak
                    peak_idx = data[component].idxmax()
                    peak_value = data[component].max()
                    
                    # Annotate the peak
                    plt.annotate(
                        f"{component.upper()} peak: {peak_value:.1f}%",
                        xy=(peak_idx, peak_value),
                        xytext=(10, 10),
                        textcoords='offset points',
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=.2')
                    )
            
            plt.tight_layout()
            plt.savefig(VISUALIZATION_DIR / "component_trends_enhanced.png")
            plt.close()
            
            logger.info("Created enhanced component trend chart")
            return True
            
        except Exception as e:
            logger.error(f"Error creating component trend chart: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_user_network_visualization(self):
        """Create an enhanced visualization of the user interaction network"""
        try:
            # Load data
            network_file = self.network_analysis_dir / "user_degree_centrality.csv"
            if not network_file.exists():
                # Try alternative location if file not found
                network_file = self.detailed_analysis_dir / "user_degree_centrality.csv"
                if not network_file.exists():
                    logger.warning(f"User network data not found in any expected location")
                    return None
                    
            user_centrality = pd.read_csv(network_file)
            
            # Load betweenness centrality for additional information
            betweenness_file = self.network_analysis_dir / "user_betweenness_centrality.csv"
            if not betweenness_file.exists():
                betweenness_file = self.detailed_analysis_dir / "user_betweenness_centrality.csv"
                
            betweenness_data = None
            if betweenness_file.exists():
                betweenness_data = pd.read_csv(betweenness_file)
            
            # Create a simplified network visualization focusing on top users
            top_n = min(30, len(user_centrality))  # Top users to include, but limit to data available
            top_users = user_centrality['username'].head(top_n).tolist()
            
            # Create a simple example network (for demonstration purposes)
            G = nx.Graph()
            
            # Add nodes
            for user in top_users:
                G.add_node(user)
            
            # Add some edges (In a real implementation, this would come from actual data)
            for i in range(len(top_users) - 1):
                G.add_edge(top_users[i], top_users[i+1])
                # Add some cross-connections
                if i < len(top_users) - 3:
                    G.add_edge(top_users[i], top_users[i+2])
            
            # Create the figure
            plt.figure(figsize=(14, 14), dpi=self.default_dpi)
            
            # Create a spring layout
            pos = nx.spring_layout(G, k=0.5, seed=42)
            
            # Set node sizes based on centrality
            node_sizes = []
            for user in G.nodes():
                size = user_centrality[user_centrality['username'] == user]['degree_centrality'].values
                node_sizes.append(2000 * (size[0] if len(size) > 0 else 0.1))
            
            # Draw nodes
            nx.draw_networkx_nodes(
                G, pos, 
                node_size=node_sizes,
                node_color=range(len(G.nodes())),
                cmap='viridis',
                alpha=0.8,
                edgecolors='white',
                linewidths=1
            )
            
            # Draw edges
            nx.draw_networkx_edges(
                G, pos,
                width=1.5,
                alpha=0.5,
                edge_color='lightgray'
            )
            
            # Draw labels with white background for readability
            labels = {user: user for user in G.nodes()}
            label_pos = {k: (v[0], v[1] + 0.02) for k, v in pos.items()}
            nx.draw_networkx_labels(
                G, label_pos,
                labels=labels,
                font_size=10,
                font_weight='bold',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1),
                horizontalalignment='center'
            )
            
            plt.title('User Interaction Network (Top Contributors)', fontsize=self.title_fontsize, pad=20)
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(VISUALIZATION_DIR / "user_network_enhanced.png")
            plt.close()
            
            logger.info("Created enhanced user network visualization")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user network visualization: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_component_keyword_charts(self):
        """Create bar charts for component keywords instead of wordclouds"""
        try:
            # Load data
            file_path = self.analysis_dir / "component_suggestions.csv"
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
                
            data = pd.read_csv(file_path)
            
            # Create separate bar charts for major component types
            component_types = ['cpu', 'gpu', 'ram', 'ssd', 'mainboard', 'psu']
            
            for component in component_types:
                # Filter data for this component
                component_data = data[data['component_type'] == component]
                
                if len(component_data) < 10:
                    logger.info(f"Skipping keyword chart for {component}: not enough data")
                    continue
                
                # Count keyword frequencies
                keyword_counts = component_data['keyword'].value_counts().reset_index()
                keyword_counts.columns = ['keyword', 'count']
                
                # Take top 15 keywords
                top_keywords = keyword_counts.head(15)
                
                # Sort by count for better visualization
                top_keywords = top_keywords.sort_values('count')
                
                # Create figure
                plt.figure(figsize=(12, 8), dpi=self.default_dpi)
                
                # Create horizontal bar chart
                bars = plt.barh(
                    top_keywords['keyword'],
                    top_keywords['count'],
                    color=sns.color_palette("viridis", len(top_keywords)),
                    alpha=0.8
                )
                
                # Add count labels
                for bar in bars:
                    width = bar.get_width()
                    plt.text(
                        width + 0.5,
                        bar.get_y() + bar.get_height()/2,
                        f'{int(width)}',
                        va='center',
                        fontweight='bold'
                    )
                
                # Add percentage labels inside bars
                total = top_keywords['count'].sum()
                for bar in bars:
                    width = bar.get_width()
                    percentage = width / total * 100
                    if percentage > 5:  # Only show percentage for significant values
                        plt.text(
                            width/2,
                            bar.get_y() + bar.get_height()/2,
                            f'{percentage:.1f}%',
                            va='center',
                            ha='center',
                            color='white',
                            fontweight='bold'
                        )
                
                # Style improvements
                plt.title(f'Top {component.upper()} Keywords in Component Suggestions', 
                         fontsize=self.title_fontsize, pad=20)
                plt.xlabel('Count', fontsize=self.label_fontsize)
                plt.ylabel('Keyword', fontsize=self.label_fontsize)
                plt.grid(axis='x', linestyle='--', alpha=0.7)
                
                plt.tight_layout()
                plt.savefig(VISUALIZATION_DIR / f"{component}_keywords_chart.png")
                plt.close()
            
            logger.info("Created component keyword bar charts")
            return True
            
        except Exception as e:
            logger.error(f"Error creating component keyword charts: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_budget_distribution_visualization(self):
        """Create an enhanced visualization of budget distribution"""
        try:
            # Load budget distribution data
            file_path = self.budget_analysis_dir / "budget_distribution.csv"
            if not file_path.exists():
                logger.warning(f"Budget distribution file not found: {file_path}")
                return None
                
            data = pd.read_csv(file_path)
            
            # Load detailed budget data
            detail_path = self.budget_analysis_dir / "budget_detailed.csv"
            if not detail_path.exists():
                logger.warning(f"Detailed budget file not found: {detail_path}")
                return None
                
            budget_details = pd.read_csv(detail_path)
            
            # Create figure
            plt.figure(figsize=(14, 10), dpi=self.default_dpi)
            
            # Main histogram
            ax1 = plt.subplot(2, 1, 1)
            sns.histplot(
                data=budget_details,
                x="budget",
                bins=20,
                kde=True,
                color='steelblue',
                alpha=0.7,
                ax=ax1
            )
            
            ax1.set_title('Distribution of Budgets in VOZ Threads', fontsize=self.title_fontsize, pad=20)
            ax1.set_xlabel('Budget (Million VND)', fontsize=self.label_fontsize)
            ax1.set_ylabel('Count', fontsize=self.label_fontsize)
            
            # Add major budget points annotation
            median = budget_details['budget'].median()
            mean = budget_details['budget'].mean()
            mode = budget_details['budget'].mode().iloc[0]
            
            ax1.axvline(median, color='red', linestyle='--', linewidth=2, alpha=0.7)
            ax1.axvline(mean, color='green', linestyle='--', linewidth=2, alpha=0.7)
            ax1.axvline(mode, color='purple', linestyle='--', linewidth=2, alpha=0.7)
            
            ax1.annotate(f'Median: {median:.1f}M', 
                        xy=(median, 0), 
                        xytext=(median, ax1.get_ylim()[1]*0.9),
                        color='red',
                        weight='bold',
                        ha='center')
            
            ax1.annotate(f'Mean: {mean:.1f}M', 
                        xy=(mean, 0), 
                        xytext=(mean, ax1.get_ylim()[1]*0.8),
                        color='green',
                        weight='bold',
                        ha='center')
            
            ax1.annotate(f'Mode: {mode:.1f}M', 
                        xy=(mode, 0), 
                        xytext=(mode, ax1.get_ylim()[1]*0.7),
                        color='purple',
                        weight='bold',
                        ha='center')
            
            # Create bar chart of budget ranges
            ax2 = plt.subplot(2, 1, 2)
            bars = ax2.bar(data['range'], data['count'], color=self.budget_cmap, alpha=0.8)
            
            # Add value labels on top of bars
            for bar, count in zip(bars, data['count']):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width()/2., 
                    height + 0.5, 
                    f'{count}',
                    ha='center', 
                    va='bottom',
                    fontsize=10,
                    fontweight='bold'
                )
            
            ax2.set_title('Count of Threads by Budget Range', fontsize=self.title_fontsize, pad=20)
            ax2.set_xlabel('Budget Range (Million VND)', fontsize=self.label_fontsize)
            ax2.set_ylabel('Count', fontsize=self.label_fontsize)
            
            # Add percentage annotations
            total = data['count'].sum()
            percentage_positions = [bar.get_height() / 2 for bar in bars]
            
            for i, (count, position) in enumerate(zip(data['count'], percentage_positions)):
                percentage = count / total * 100
                ax2.text(
                    bars[i].get_x() + bars[i].get_width()/2., 
                    position, 
                    f'{percentage:.1f}%', 
                    ha='center', 
                    va='center',
                    fontsize=12,
                    fontweight='bold', 
                    color='white'
                )
            
            plt.tight_layout()
            plt.savefig(VISUALIZATION_DIR / "budget_distribution_enhanced.png")
            plt.close()
            
            logger.info("Created enhanced budget distribution visualization")
            return True
            
        except Exception as e:
            logger.error(f"Error creating budget distribution visualization: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_sentiment_analysis_visualization(self):
        """Create visualizations for sentiment analysis results"""
        try:
            # Load sentiment data
            file_path = self.sentiment_analysis_dir / "component_sentiment.csv"
            if not file_path.exists():
                # Try alternative location
                file_path = self.detailed_analysis_dir / "component_sentiment.csv"
                if not file_path.exists():
                    logger.warning(f"Sentiment data not found in any expected location")
                    return None
                
            sentiment_data = pd.read_csv(file_path)
            
            # Create visualization for sentiment distribution
            plt.figure(figsize=(12, 8), dpi=self.default_dpi)
            
            # Create sentiment distribution plot
            sns.histplot(
                sentiment_data['sentiment_score'],
                bins=30,
                kde=True,
                color='steelblue'
            )
            
            # Add vertical lines for sentiment categories
            plt.axvline(x=0.1, color='green', linestyle='--', alpha=0.7, label='Positive threshold')
            plt.axvline(x=-0.1, color='red', linestyle='--', alpha=0.7, label='Negative threshold')
            plt.axvline(x=0, color='gray', linestyle='-', alpha=0.5, label='Neutral')
            
            # Add styling
            plt.title('Distribution of Sentiment Scores in Component Mentions', fontsize=self.title_fontsize, pad=20)
            plt.xlabel('Sentiment Score', fontsize=self.label_fontsize)
            plt.ylabel('Count', fontsize=self.label_fontsize)
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend()
            
            # Save the visualization
            plt.tight_layout()
            plt.savefig(VISUALIZATION_DIR / "sentiment_distribution.png")
            plt.close()
            
            # Create component-wise sentiment visualization if possible
            try:
                if 'component_type' in sentiment_data.columns:
                    # Group by component type and calculate average sentiment
                    component_sentiment = sentiment_data.groupby('component_type')['sentiment_score'].agg(['mean', 'count']).reset_index()
                    component_sentiment = component_sentiment.sort_values('mean')
                    
                    # Only proceed if we have enough components
                    if len(component_sentiment) >= 3:
                        plt.figure(figsize=(12, 8), dpi=self.default_dpi)
                        
                        # Create horizontal bar chart
                        bars = plt.barh(
                            component_sentiment['component_type'],
                            component_sentiment['mean'],
                            color=[
                                'red' if x < -0.1 else 'green' if x > 0.1 else 'gray'
                                for x in component_sentiment['mean']
                            ],
                            alpha=0.7
                        )
                        
                        # Add count annotations
                        for i, (_, row) in enumerate(component_sentiment.iterrows()):
                            plt.text(
                                row['mean'] + 0.01 * (1 if row['mean'] >= 0 else -1),
                                i,
                                f"n={int(row['count'])}",
                                va='center',
                                fontsize=10,
                                fontweight='bold'
                            )
                        
                        # Add styling
                        plt.axvline(x=0, color='gray', linestyle='-', alpha=0.5)
                        plt.title('Average Sentiment Score by Component Type', fontsize=self.title_fontsize, pad=20)
                        plt.xlabel('Average Sentiment Score', fontsize=self.label_fontsize)
                        plt.ylabel('Component Type', fontsize=self.label_fontsize)
                        plt.grid(True, linestyle='--', alpha=0.7)
                        
                        # Save the visualization
                        plt.tight_layout()
                        plt.savefig(VISUALIZATION_DIR / "component_sentiment.png")
                        plt.close()
            except Exception as e:
                logger.error(f"Error creating component sentiment chart: {str(e)}")
            
            logger.info("Created sentiment analysis visualizations")
            return True
            
        except Exception as e:
            logger.error(f"Error creating sentiment analysis visualization: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_purpose_distribution_visualization(self):
        """Create visualization for purpose distribution"""
        try:
            # Load purpose distribution data
            file_path = self.op_analysis_dir / "purpose_distribution.csv"
            if not file_path.exists():
                logger.warning(f"Purpose distribution file not found: {file_path}")
                return None
                
            data = pd.read_csv(file_path)
            
            # Sort by count
            data = data.sort_values('count', ascending=False)
            
            # Create figure
            plt.figure(figsize=(12, 8), dpi=self.default_dpi)
            
            # Create bar chart with enhanced styling
            bars = plt.bar(
                data['purpose'],
                data['count'],
                color=sns.color_palette("viridis", len(data)),
                alpha=0.8
            )
            
            # Add value labels on top of bars
            for bar, count in zip(bars, data['count']):
                height = bar.get_height()
                plt.text(
                    bar.get_x() + bar.get_width()/2., 
                    height + 0.5, 
                    f'{count}',
                    ha='center', 
                    va='bottom',
                    fontsize=10,
                    fontweight='bold'
                )
            
            # Add percentage inside bars
            total = data['count'].sum()
            for i, (bar, count) in enumerate(zip(bars, data['count'])):
                percentage = count / total * 100
                plt.text(
                    bar.get_x() + bar.get_width()/2., 
                    bar.get_height() / 2, 
                    f'{percentage:.1f}%', 
                    ha='center', 
                    va='center',
                    fontsize=12,
                    fontweight='bold', 
                    color='white'
                )
            
            # Style improvements
            plt.title('Distribution of Usage Purposes', fontsize=self.title_fontsize, pad=20)
            plt.xlabel('Purpose', fontsize=self.label_fontsize)
            plt.ylabel('Count', fontsize=self.label_fontsize)
            plt.xticks(rotation=45, ha='right', fontsize=self.tick_fontsize)
            plt.yticks(fontsize=self.tick_fontsize)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(VISUALIZATION_DIR / "purpose_distribution.png")
            plt.close()
            
            logger.info("Created purpose distribution visualization")
            return True
            
        except Exception as e:
            logger.error(f"Error creating purpose distribution visualization: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    def create_purpose_analysis_visualizations(self):
        """Tạo các biểu đồ phân tích mục đích sử dụng"""
        try:
            # Tìm file purpose_distribution.csv trong nhiều vị trí có thể có
            potential_paths = [
                self.op_analysis_dir / "purpose_distribution.csv",
                self.analysis_dir / "purpose_distribution.csv",
                self.detailed_analysis_dir / "purpose_distribution.csv"
            ]
            
            purpose_file = None
            for path in potential_paths:
                if path.exists():
                    purpose_file = path
                    break
                    
            if purpose_file is None:
                logger.warning("Không tìm thấy file purpose_distribution.csv")
                return None
                
            # Đọc dữ liệu
            purpose_data = pd.read_csv(purpose_file)
            
            if purpose_data.empty:
                logger.warning("File purpose_distribution.csv không có dữ liệu")
                return None
            
            # 1. Biểu đồ phân bố mục đích sử dụng (đã cải tiến)
            # ------------------------------------------------
            # Sắp xếp theo số lượng giảm dần
            purpose_data = purpose_data.sort_values('count', ascending=False)
            
            # Tạo biểu đồ dạng cột (ngang)
            plt.figure(figsize=(14, 10), dpi=self.default_dpi)
            
            # Biểu đồ cột với màu sắc gradient
            colors = sns.color_palette("viridis", len(purpose_data))
            bars = plt.barh(purpose_data['purpose'], purpose_data['count'], color=colors)
            
            # Thêm số lượng và phần trăm vào biểu đồ
            total = purpose_data['count'].sum()
            
            for i, bar in enumerate(bars):
                count = purpose_data['count'].iloc[i]
                percent = 100 * count / total
                
                # Số lượng (bên phải cột)
                plt.text(
                    bar.get_width() + 1, 
                    bar.get_y() + bar.get_height()/2,
                    f"{count} ({percent:.1f}%)",
                    va='center',
                    fontweight='bold'
                )
                
                # Thêm nhãn trong cột nếu có đủ không gian
                if bar.get_width() > 5:
                    plt.text(
                        bar.get_width()/2,
                        bar.get_y() + bar.get_height()/2,
                        purpose_data['purpose'].iloc[i],
                        va='center',
                        ha='center',
                        color='white',
                        fontweight='bold'
                    )
            
            # Định dạng và nhãn
            plt.title('Phân bố mục đích sử dụng máy tính', fontsize=self.title_fontsize, pad=20)
            plt.xlabel('Số lượng', fontsize=self.label_fontsize)
            # Không hiển thị nhãn y vì đã hiển thị tên trong cột
            plt.ylabel('')
            plt.yticks([])
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            
            # Lưu biểu đồ
            plt.tight_layout()
            plt.savefig(VISUALIZATION_DIR / "purpose_distribution_horizontal.png")
            plt.close()
            
            # 2. Biểu đồ tròn phân bố mục đích sử dụng
            # ----------------------------------------
            plt.figure(figsize=(12, 10), dpi=self.default_dpi)
            
            # Tính toán phần trăm cho mỗi mục đích
            purpose_data['percentage'] = 100 * purpose_data['count'] / total
            
            # Nhóm các mục đích nhỏ (dưới 5%) vào "Others"
            threshold = 5  # phần trăm
            small_purposes = purpose_data[purpose_data['percentage'] < threshold]
            large_purposes = purpose_data[purpose_data['percentage'] >= threshold]
            
            # Tạo danh mục "Others" nếu cần
            if not small_purposes.empty:
                others = {
                    'purpose': 'Others',
                    'count': small_purposes['count'].sum(),
                    'percentage': small_purposes['percentage'].sum()
                }
                # Thêm "Others" vào danh sách các mục đích lớn
                large_purposes = pd.concat([large_purposes, pd.DataFrame([others])])
            
            # Tạo biểu đồ tròn
            wedges, texts, autotexts = plt.pie(
                large_purposes['count'],
                labels=large_purposes['purpose'],
                autopct='%1.1f%%',
                startangle=90,
                shadow=False,
                colors=sns.color_palette("viridis", len(large_purposes)),
                wedgeprops={'edgecolor': 'white', 'linewidth': 1},
                textprops={'fontsize': 12, 'fontweight': 'bold'}
            )
            
            # Định dạng phần trăm bên trong biểu đồ
            for autotext in autotexts:
                autotext.set_fontsize(10)
                autotext.set_fontweight('bold')
                autotext.set_color('white')
            
            # Thêm tiêu đề và legend
            plt.title('Phân bố mục đích sử dụng máy tính (%)', fontsize=self.title_fontsize, pad=20)
            plt.legend(
                loc='upper right',
                bbox_to_anchor=(1.15, 1.0),
                fontsize=10
            )
            
            # Lưu biểu đồ
            plt.tight_layout()
            plt.savefig(VISUALIZATION_DIR / "purpose_distribution_pie.png")
            plt.close()
            
            # 3. Biểu đồ kết hợp mục đích và ngân sách
            # ---------------------------------------
            # Tìm file kết hợp purpose-budget nếu có
            budget_purpose_file = self.detailed_analysis_dir / "budget_purpose_correlation.csv"
            
            if budget_purpose_file.exists():
                try:
                    # Đọc dữ liệu
                    budget_purpose_data = pd.read_csv(budget_purpose_file, index_col=0)
                    
                    if not budget_purpose_data.empty:
                        plt.figure(figsize=(14, 8), dpi=self.default_dpi)
                        
                        # Tạo heatmap
                        ax = sns.heatmap(
                            budget_purpose_data,
                            annot=True,
                            fmt=".1f",
                            cmap="YlGnBu",
                            linewidths=0.5,
                            linecolor='white',
                            cbar_kws={'label': 'Tỉ lệ (%)'}
                        )
                        
                        # Định dạng biểu đồ
                        plt.title('Phân bố mục đích sử dụng theo ngân sách', fontsize=self.title_fontsize, pad=20)
                        plt.ylabel('Khoảng ngân sách', fontsize=self.label_fontsize)
                        plt.xlabel('Mục đích sử dụng', fontsize=self.label_fontsize)
                        
                        # Xoay các nhãn để dễ đọc hơn
                        plt.xticks(rotation=45, ha='right')
                        plt.yticks(rotation=0)
                        
                        # Lưu biểu đồ
                        plt.tight_layout()
                        plt.savefig(VISUALIZATION_DIR / "budget_purpose_heatmap.png")
                        plt.close()
                except Exception as e:
                    logger.error(f"Lỗi khi tạo biểu đồ kết hợp mục đích-ngân sách: {str(e)}")
            
            logger.info("Đã tạo biểu đồ phân tích mục đích sử dụng")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân tích mục đích sử dụng: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_all_visualizations(self):
        """Create all enhanced visualizations"""
        logger.info("Creating all enhanced visualizations...")
        
        # Budget and component visualizations
        self.create_budget_distribution_visualization()
        self.create_budget_component_heatmap()
        self.create_component_trend_chart()
        self.create_component_keyword_charts()  # Use bar charts instead of wordcloud
        self.create_purpose_analysis_visualizations()
        
        # User and sentiment visualizations
        self.create_user_network_visualization()
        self.create_sentiment_analysis_visualization()
        self.create_purpose_distribution_visualization()
        
        logger.info("Completed creating all enhanced visualizations")
        return True


if __name__ == "__main__":
    viz_creator = VisualizationCreator()
    viz_creator.create_all_visualizations()