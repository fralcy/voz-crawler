import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import logging
from pathlib import Path

from config import DATA_DIR

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create directory for network analysis
NETWORK_DIR = DATA_DIR / "analysis" / "network_analysis"
NETWORK_DIR.mkdir(parents=True, exist_ok=True)

class NetworkAnalyzer:
    """
    Class for advanced network analysis of user interactions
    """
    def __init__(self, analysis_dir=DATA_DIR / "analysis"):
        self.analysis_dir = analysis_dir
        self.op_analysis_path = analysis_dir / "op_analysis" / "op_analysis.json"
        self.reply_analysis_path = analysis_dir / "reply_analysis" / "reply_analysis.json"
        
        # Network data
        self.user_graph = None
        self.thread_graph = None
        self.community_data = None
        
    def load_data(self):
        """Load data from analysis files"""
        try:
            # Load OP data
            if not self.op_analysis_path.exists():
                logger.warning(f"OP analysis file not found: {self.op_analysis_path}")
                return False
                
            with open(self.op_analysis_path, 'r', encoding='utf-8') as f:
                self.op_data = json.load(f)
                
            # Load reply data
            if not self.reply_analysis_path.exists():
                logger.warning(f"Reply analysis file not found: {self.reply_analysis_path}")
                return False
                
            with open(self.reply_analysis_path, 'r', encoding='utf-8') as f:
                self.reply_data = json.load(f)
                
            logger.info(f"Loaded data: {len(self.op_data)} OPs and {len(self.reply_data)} replies")
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return False
            
    def build_user_interaction_network(self):
        """Build a network of user interactions"""
        if not hasattr(self, 'op_data') or not hasattr(self, 'reply_data'):
            if not self.load_data():
                return None
                
        try:
            # Create directed graph for user interactions
            G = nx.DiGraph()
            
            # Map thread_id to OP user
            thread_authors = {}
            for op in self.op_data:
                thread_id = op.get('thread_id')
                user = op.get('user')
                if thread_id and user:
                    thread_authors[thread_id] = user
            
            # Add edges for replies to OP
            for reply in self.reply_data:
                thread_id = reply.get('thread_id')
                reply_user = reply.get('user')
                
                if not thread_id or not reply_user:
                    continue
                    
                op_user = thread_authors.get(thread_id)
                if not op_user:
                    continue
                    
                # Skip self-loops
                if reply_user == op_user:
                    continue
                    
                # Add edge from reply user to OP
                if G.has_edge(reply_user, op_user):
                    G[reply_user][op_user]['weight'] += 1
                else:
                    G.add_edge(reply_user, op_user, weight=1)
                    
                # Also add edge from OP to reply user if replying to their own thread
                # (This creates a bidirectional relationship for thread participation)
                if G.has_edge(op_user, reply_user):
                    G[op_user][reply_user]['weight'] += 0.5  # Lower weight for thread owner replies
                else:
                    G.add_edge(op_user, reply_user, weight=0.5)
            
            # Calculate node metrics
            in_degree = dict(G.in_degree(weight='weight'))
            out_degree = dict(G.out_degree(weight='weight'))
            
            # Add node attributes
            for node in G.nodes():
                G.nodes[node]['in_degree'] = in_degree.get(node, 0)
                G.nodes[node]['out_degree'] = out_degree.get(node, 0)
                G.nodes[node]['total_degree'] = in_degree.get(node, 0) + out_degree.get(node, 0)
            
            # Store the graph
            self.user_graph = G
            
            # Save basic network statistics
            stats = {
                'node_count': G.number_of_nodes(),
                'edge_count': G.number_of_edges(),
                'average_degree': sum(dict(G.degree()).values()) / G.number_of_nodes(),
                'density': nx.density(G),
                'is_connected': nx.is_strongly_connected(G),
                'largest_component_size': len(max(nx.strongly_connected_components(G), key=len))
            }
            
            # Save stats to file
            with open(NETWORK_DIR / "user_network_stats.json", 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Built user interaction network with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
            return G
            
        except Exception as e:
            logger.error(f"Error building user interaction network: {str(e)}")
            return None
            
    def detect_communities(self):
        """Detect communities in the user network"""
        if self.user_graph is None:
            self.build_user_interaction_network()
            
        if self.user_graph is None:
            logger.error("Cannot detect communities: user graph not available")
            return None
            
        try:
            # Create undirected graph for community detection
            G_undirected = self.user_graph.to_undirected()
            
            # Detect communities using Louvain method
            from community import best_partition
            partition = best_partition(G_undirected)
            
            # Count communities
            communities = {}
            for node, community_id in partition.items():
                if community_id not in communities:
                    communities[community_id] = []
                communities[community_id].append(node)
            
            # Sort communities by size
            sorted_communities = sorted(communities.items(), key=lambda x: len(x[1]), reverse=True)
            
            # Create community data
            community_data = []
            for community_id, members in sorted_communities:
                # Skip communities with fewer than 3 members
                if len(members) < 3:
                    continue
                    
                # Calculate community metrics
                subgraph = self.user_graph.subgraph(members)
                density = nx.density(subgraph)
                
                # Find central members
                central_members = sorted(members, 
                                       key=lambda x: self.user_graph.nodes[x]['total_degree'], 
                                       reverse=True)[:5]
                
                community_data.append({
                    'community_id': community_id,
                    'size': len(members),
                    'density': density,
                    'central_members': central_members
                })
            
            # Store community data
            self.community_data = community_data
            
            # Save community data to file
            with open(NETWORK_DIR / "community_data.json", 'w', encoding='utf-8') as f:
                json.dump(community_data, f, ensure_ascii=False, indent=2)
                
            # Add community as node attribute
            nx.set_node_attributes(self.user_graph, partition, 'community')
            
            logger.info(f"Detected {len(community_data)} communities with at least 3 members")
            return community_data
            
        except Exception as e:
            logger.error(f"Error detecting communities: {str(e)}")
            return None
            
    def visualize_network(self, max_nodes=100):
        """Create a visualization of the user network"""
        if self.user_graph is None:
            self.build_user_interaction_network()
            
        if self.user_graph is None:
            logger.error("Cannot visualize network: user graph not available")
            return None
            
        try:
            # For large networks, filter to top nodes by degree
            G = self.user_graph
            if G.number_of_nodes() > max_nodes:
                # Get top nodes by total degree
                top_nodes = sorted(G.nodes(), 
                                  key=lambda x: G.nodes[x]['total_degree'], 
                                  reverse=True)[:max_nodes]
                
                # Create subgraph
                G = G.subgraph(top_nodes)
                
            # Detect communities if not already done
            if not hasattr(self, 'community_data') or self.community_data is None:
                self.detect_communities()
            
            # Create figure
            plt.figure(figsize=(20, 20), dpi=300)
            
            # Get node positions using force-directed layout
            pos = nx.spring_layout(G, k=0.2, iterations=50, seed=42)
            
            # Determine node colors by community
            node_colors = []
            communities = nx.get_node_attributes(G, 'community')
            unique_communities = set(communities.values())
            color_map = plt.cm.tab20(np.linspace(0, 1, len(unique_communities)))
            community_to_color = {comm: color_map[i] for i, comm in enumerate(unique_communities)}
            
            for node in G.nodes():
                comm = communities.get(node, 0)
                node_colors.append(community_to_color.get(comm, 'gray'))
            
            # Determine node sizes by total degree
            node_sizes = []
            for node in G.nodes():
                size = G.nodes[node]['total_degree'] * 50 + 100
                node_sizes.append(min(size, 2000))  # Cap size
            
            # Determine edge widths by weight
            edge_widths = []
            for u, v, data in G.edges(data=True):
                width = data.get('weight', 1) * 0.5
                edge_widths.append(width)
            
            # Draw the network
            nx.draw_networkx_nodes(
                G, pos, 
                node_size=node_sizes,
                node_color=node_colors,
                alpha=0.8,
                edgecolors='white',
                linewidths=0.5
            )
            
            nx.draw_networkx_edges(
                G, pos,
                width=edge_widths,
                alpha=0.3,
                edge_color='gray',
                arrows=True,
                arrowsize=10,
                connectionstyle='arc3,rad=0.1'
            )
            
            # Draw labels for top nodes only
            top_node_labels = {}
            top_nodes_by_degree = sorted(G.nodes(), 
                                        key=lambda x: G.nodes[x]['total_degree'], 
                                        reverse=True)[:20]
            
            for node in top_nodes_by_degree:
                top_node_labels[node] = node
                
            nx.draw_networkx_labels(
                G, pos,
                labels=top_node_labels,
                font_size=8,
                font_weight='bold',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.3')
            )
            
            plt.title('User Interaction Network', fontsize=24, pad=20)
            plt.axis('off')
            plt.tight_layout()
            
            # Save the visualization
            plt.savefig(NETWORK_DIR / "user_network_visualization.png")
            plt.close()
            
            logger.info(f"Created user network visualization with {G.number_of_nodes()} nodes")
            return True
            
        except Exception as e:
            logger.error(f"Error visualizing network: {str(e)}")
            return False
            
    def analyze_network_centrality(self):
        """Analyze network centrality measures"""
        if self.user_graph is None:
            self.build_user_interaction_network()
            
        if self.user_graph is None:
            logger.error("Cannot analyze network centrality: user graph not available")
            return None
            
        try:
            # Calculate centrality measures
            G = self.user_graph
            
            # Degree centrality
            in_degree_centrality = nx.in_degree_centrality(G)
            out_degree_centrality = nx.out_degree_centrality(G)
            
            # Betweenness centrality (for top nodes only to save time)
            top_nodes = sorted(G.nodes(), 
                              key=lambda x: G.nodes[x]['total_degree'], 
                              reverse=True)[:100]
            
            subgraph = G.subgraph(top_nodes)
            betweenness_centrality = nx.betweenness_centrality(subgraph)
            
            # Eigenvector centrality
            try:
                eigenvector_centrality = nx.eigenvector_centrality(G, max_iter=500)
            except:
                # Fall back to power iteration with more iterations for convergence issues
                eigenvector_centrality = nx.eigenvector_centrality_numpy(G)
            
            # Create DataFrame with centrality measures
            centrality_data = []
            
            for node in G.nodes():
                data = {
                    'username': node,
                    'in_degree': G.nodes[node]['in_degree'],
                    'out_degree': G.nodes[node]['out_degree'],
                    'total_degree': G.nodes[node]['total_degree'],
                    'in_degree_centrality': in_degree_centrality[node],
                    'out_degree_centrality': out_degree_centrality[node],
                    'eigenvector_centrality': eigenvector_centrality[node],
                    'betweenness_centrality': betweenness_centrality.get(node, 0)
                }
                
                if 'community' in G.nodes[node]:
                    data['community'] = G.nodes[node]['community']
                    
                centrality_data.append(data)
            
            # Create DataFrame
            centrality_df = pd.DataFrame(centrality_data)
            
            # Sort by total degree
            centrality_df = centrality_df.sort_values('total_degree', ascending=False)
            
            # Save to CSV
            centrality_df.to_csv(NETWORK_DIR / "user_centrality.csv", index=False)
            
            # Create visualization of top users by various centrality measures
            plt.figure(figsize=(14, 10), dpi=300)
            
            # Get top 20 users by total degree
            top_users = centrality_df.head(20)
            
            # Create subplot for different centrality measures
            fig, axes = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
            
            # In-degree centrality
            axes[0, 0].barh(top_users['username'], top_users['in_degree_centrality'], color='skyblue')
            axes[0, 0].set_title('Top Users by In-Degree Centrality')
            axes[0, 0].set_xlabel('In-Degree Centrality')
            axes[0, 0].set_ylabel('Username')
            
            # Out-degree centrality
            axes[0, 1].barh(top_users['username'], top_users['out_degree_centrality'], color='lightgreen')
            axes[0, 1].set_title('Top Users by Out-Degree Centrality')
            axes[0, 1].set_xlabel('Out-Degree Centrality')
            axes[0, 1].set_ylabel('Username')
            
            # Eigenvector centrality
            axes[1, 0].barh(top_users['username'], top_users['eigenvector_centrality'], color='coral')
            axes[1, 0].set_title('Top Users by Eigenvector Centrality')
            axes[1, 0].set_xlabel('Eigenvector Centrality')
            axes[1, 0].set_ylabel('Username')
            
            # Betweenness centrality
            btw_df = centrality_df.sort_values('betweenness_centrality', ascending=False).head(20)
            axes[1, 1].barh(btw_df['username'], btw_df['betweenness_centrality'], color='violet')
            axes[1, 1].set_title('Top Users by Betweenness Centrality')
            axes[1, 1].set_xlabel('Betweenness Centrality')
            axes[1, 1].set_ylabel('Username')
            
            plt.tight_layout()
            plt.savefig(NETWORK_DIR / "user_centrality_measures.png")
            plt.close()
            
            logger.info("Completed network centrality analysis")
            return centrality_df
            
        except Exception as e:
            logger.error(f"Error analyzing network centrality: {str(e)}")
            return None
    
    def run_full_network_analysis(self):
        """Run all network analysis methods"""
        logger.info("Starting full network analysis...")
        
        # Load data
        self.load_data()
        
        # Build network
        self.build_user_interaction_network()
        
        # Detect communities
        self.detect_communities()
        
        # Analyze centrality
        self.analyze_network_centrality()
        
        # Visualize network
        self.visualize_network()
        
        logger.info("Completed full network analysis")
        return True


if __name__ == "__main__":
    analyzer = NetworkAnalyzer()
    analyzer.run_full_network_analysis()