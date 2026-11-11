
import pandas as pd
from pathlib import Path


def analyze_relationships(csv_file_path="transactions.csv"):
    df = pd.read_csv(csv_file_path)

    # Identify accounts sharing devices and IP addresses.
    shared_devices = set()
    shared_ips = set()

    for _, group in df.dropna(subset=["device_id"]).groupby("device_id"):
        users = set(group["sender_id"].astype(str))
        if len(users) > 1:
            shared_devices.update(users)

    for _, group in df.dropna(subset=["ip_address"]).groupby("ip_address"):
        users = set(group["sender_id"].astype(str))
        if len(users) > 1:
            shared_ips.update(users)

    print("\n=== Shared Device Analysis ===")
    for device, group in df.dropna(subset=["device_id"]).groupby("device_id"):
        users = sorted(set(group["sender_id"].astype(str)))
        if len(users) > 1:
            print(f"Device {device}: {', '.join(users)}")

    print("\n=== Shared IP Analysis ===")
    for ip, group in df.dropna(subset=["ip_address"]).groupby("ip_address"):
        users = sorted(set(group["sender_id"].astype(str)))
        if len(users) > 1:
            print(f"IP {ip}: {', '.join(users)}")

    print("\n=== Fraudulent Transactions ===")
    fraud = df[df["is_fraud"] == 1]

    if fraud.empty:
        print("No transactions labelled as fraudulent.")
    else:
        print(
            fraud[
                ["transaction_id", "sender_id", "receiver_id", "amount"]
            ].to_string(index=False)
        )

    # Build an account-level summary.
    account_risk = df.groupby("sender_id").agg(
        total_transactions=("transaction_id", "count"),
        total_amount=("amount", "sum"),
        labelled_fraud_count=("is_fraud", "sum"),
    )

    account_risk["shared_device"] = [
        account in shared_devices for account in account_risk.index
    ]
    account_risk["shared_ip"] = [
        account in shared_ips for account in account_risk.index
    ]

    # Simple review flag, not a trained fraud prediction.
    account_risk["review_flag"] = account_risk.apply(
        lambda row: (
            "Review"
            if row["labelled_fraud_count"] > 0
            or row["shared_device"]
            or row["shared_ip"]
            else "No flag"
        ),
        axis=1,
    )

    account_risk.index.name = "account_id"

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "account_risk.csv"
    account_risk.to_csv(output_file)

    print(f"\n=== Account Risk Report ===\n{account_risk.to_string()}")
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    analyze_relationships()
