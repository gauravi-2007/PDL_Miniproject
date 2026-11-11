import networkx as nx
import pandas as pd

def load_and_build_graph(csv_file_path):
    # Load transaction data using pandas
    df = pd.read_csv(csv_file_path)
    
    # Initialize an empty NetworkX Graph
    G = nx.Graph()
    
    # Add nodes and edges based on relationships
    for _, row in df.iterrows():
        sender = row['sender_id']
        receiver = row['receiver_id']
        device = row['device_id']
        ip = row['ip_address']
        
        # Transaction edge between users
        G.add_edge(sender, receiver, relation='transaction', amount=row['amount'], is_fraud=row['is_fraud'])
        
        # Shared infrastructure edges (Linking users to devices and IPs)
        G.add_edge(sender, device, relation='shared_device')
        G.add_edge(receiver, device, relation='shared_device')
        G.add_edge(sender, ip, relation='shared_ip')
        
    print(f"Graph successfully built! Total nodes: {G.number_of_nodes()}, Total edges: {G.number_of_edges()}")
    return G, df

if __name__ == "__main__":
    load_and_build_graph("transactions.csv")

