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
        self.detailed_analysis_dir = analysis_dir / "detailed_analysis"
        
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
            return None
    
    def create_user_network_visualization(self):
        """Create an enhanced visualization of the user interaction network"""
        try:
            # Load data
            network_file = self.detailed_analysis_dir / "user_degree_centrality.csv"
            if not network_file.exists():
                logger.warning(f"File not found: {network_file}")
                return None
                
            user_centrality = pd.read_csv(network_file)
            
            # Load betweenness centrality for additional information
            betweenness_file = self.detailed_analysis_dir / "user_betweenness_centrality.csv"
            betweenness_data = None
            if betweenness_file.exists():
                betweenness_data = pd.read_csv(betweenness_file)
            
            # Create a simplified network visualization focusing on top users
            top_n = 30  # Top users to include
            top_users = user_centrality['username'].head(top_n).tolist()
            
            # Create a simple example network (for demonstration purposes)
            G = nx.Graph()
            
            # Add nodes
            for user in top_users:
                G.add_node(user)
            
            # Add some edges (In a real implementation, this would come from actual data)
            # This is a placeholder - in practice, you would get edges from the actual analysis data
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
            return None
    
    def create_component_wordcloud(self):
        """Create wordclouds for component suggestions"""
        try:
            # Load data
            file_path = self.analysis_dir / "component_suggestions.csv"
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
                
            data = pd.read_csv(file_path)
            
            # Create separate wordclouds for major component types
            component_types = ['cpu', 'gpu', 'ram', 'ssd', 'mainboard', 'psu']
            
            for component in component_types:
                # Filter data for this component
                component_data = data[data['component_type'] == component]
                
                if len(component_data) < 10:
                    continue
                
                # Combine all contexts
                text = ' '.join(component_data['context'].dropna().tolist())
                
                # Generate wordcloud
                wordcloud = WordCloud(
                    width=1000, 
                    height=600,
                    background_color='white',
                    colormap='viridis',
                    max_words=100,
                    contour_width=1,
                    contour_color='steelblue'
                ).generate(text)
                
                # Create figure
                plt.figure(figsize=(16, 10), dpi=self.default_dpi)
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.title(f'{component.upper()} Component Suggestions - Word Cloud', 
                          fontsize=self.title_fontsize, pad=20)
                plt.axis('off')
                plt.tight_layout()
                plt.savefig(VISUALIZATION_DIR / f"{component}_wordcloud.png")
                plt.close()
            
            logger.info("Created component wordclouds")
            return True
            
        except Exception as e:
            logger.error(f"Error creating component wordclouds: {str(e)}")
            return None
    
    def create_budget_distribution_visualization(self):
        """Create an enhanced visualization of budget distribution"""
        try:
            # Load data
            file_path = self.analysis_dir / "budget_distribution.csv"
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
                
            data = pd.read_csv(file_path)
            
            # Create figure
            plt.figure(figsize=(14, 10), dpi=self.default_dpi)
            
            # Main histogram
            ax1 = plt.subplot(2, 1, 1)
            sns.histplot(
                data=data,
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
            median = data['budget'].median()
            mean = data['budget'].mean()
            mode = data['budget'].mode().iloc[0]
            
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
            
            # Create budget ranges for bar chart
            budget_ranges = [(0, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 40), (40, 50), (50, 100)]
            budget_labels = ['<10tr', '10-15tr', '15-20tr', '20-25tr', '25-30tr', '30-40tr', '40-50tr', '50tr+']
            
            # Count threads in each range
            range_counts = []
            for min_val, max_val in budget_ranges:
                count = len(data[(data['budget'] >= min_val) & (data['budget'] < max_val)])
                range_counts.append(count)
            
            # Create bar chart
            ax2 = plt.subplot(2, 1, 2)
            bars = ax2.bar(budget_labels, range_counts, color=self.budget_cmap, alpha=0.8)
            
            # Add value labels on top of bars
            for bar, count in zip(bars, range_counts):
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
            total = sum(range_counts)
            percentage_positions = [bar.get_height() / 2 for bar in bars]
            
            for i, (count, position) in enumerate(zip(range_counts, percentage_positions)):
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
            return None
    
    def create_all_visualizations(self):
        """Create all enhanced visualizations"""
        logger.info("Creating all enhanced visualizations...")
        
        self.create_budget_component_heatmap()
        self.create_component_trend_chart()
        self.create_user_network_visualization()
        self.create_component_wordcloud()
        self.create_budget_distribution_visualization()
        
        logger.info("Completed creating all enhanced visualizations")
        return True


if __name__ == "__main__":
    viz_creator = VisualizationCreator()
    viz_creator.create_all_visualizations()