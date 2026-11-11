import networkx as nx
import pandas as pd


def load_and_build_graph(csv_file_path):
  # Load a sample or chunk of the large dataset to keep it fast for your mini-project
  # (Using nrows=1000 ensures it doesn't lag your local machine)
  df = pd.read_csv(csv_file_path, nrows=1000)

  # Initialize an empty NetworkX Graph
  G = nx.Graph()

  # Add nodes and edges based on transactions
  for _, row in df.iterrows():
    sender = row["nameOrig"]
    receiver = row["nameDest"]
    amount = row["amount"]
    is_fraud = row["isFraud"]

    # Transaction edge linking sender and receiver
    G.add_edge(
        sender,
        receiver,
        relation="transaction",
        amount=amount,
        is_fraud=is_fraud,
    )

  print(
      f"Kaggle Graph successfully built! Total nodes: {G.number_of_nodes()},"
      f" Total edges: {G.number_of_edges()}"
  )
  return G, df


if __name__ == "__main__":
  # Replace with the exact filename of the downloaded CSV from Kaggle
  load_and_build_graph("PS_20174392719_1491204439457_log.csv")