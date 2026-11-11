
import pandas as pd
import networkx as nx


REQUIRED_COLUMNS = {
    "transaction_id",
    "sender_id",
    "receiver_id",
    "device_id",
    "ip_address",
    "amount",
    "is_fraud",
}


def load_and_build_graph(csv_file_path="transactions.csv"):
    df = pd.read_csv(csv_file_path)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.dropna(subset=["sender_id", "receiver_id"]).copy()

    graph = nx.MultiDiGraph()

    for _, row in df.iterrows():
        sender = str(row["sender_id"])
        receiver = str(row["receiver_id"])
        transaction_id = str(row["transaction_id"])

        graph.add_node(sender, node_type="account")
        graph.add_node(receiver, node_type="account")

        graph.add_edge(
            sender,
            receiver,
            key=transaction_id,
            relation="transaction",
            transaction_id=transaction_id,
            amount=float(row["amount"]),
            is_fraud=int(row["is_fraud"]),
        )

        for column, relation in [
            ("device_id", "uses_device"),
            ("ip_address", "uses_ip"),
        ]:
            value = row[column]

            if pd.notna(value) and str(value).strip():
                related_node = f"{relation}:{value}"
                graph.add_node(related_node, node_type=relation)
                graph.add_edge(
                    sender,
                    related_node,
                    relation=relation,
                    transaction_id=transaction_id,
                )

    print("Transaction graph built successfully!")
    print(f"Transactions loaded: {len(df)}")
    print(f"Total nodes: {graph.number_of_nodes()}")
    print(f"Total edges: {graph.number_of_edges()}")

    return graph, df



if __name__ == "__main__":
    from relationship_analysis import analyze_relationships

    dataset_path = "data/processed/paysim_sample.csv"

    graph, transactions = load_and_build_graph(dataset_path)

    analyze_relationships(dataset_path)
