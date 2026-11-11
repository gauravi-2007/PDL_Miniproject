
from pathlib import Path
import pandas as pd

INPUT_FILE = Path(
    r"D:\Transfer@GR\PS_20174392719_1491204439457_log.csv"
)
OUTPUT_FILE = Path("data/processed/paysim_sample.csv")

CHUNK_SIZE = 200_000
SAMPLES_PER_CLASS_PER_CHUNK = 5


def main():
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

    selected_chunks = []

    for chunk_number, chunk in enumerate(
        pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE),
        start=1,
    ):
        # Keep transfer-related transaction types.
        chunk = chunk[
            chunk["type"].isin(["TRANSFER", "CASH_OUT"])
        ]

        fraud = chunk[chunk["isFraud"] == 1]
        normal = chunk[chunk["isFraud"] == 0]

        if not fraud.empty:
            selected_chunks.append(
                fraud.sample(
                    n=min(SAMPLES_PER_CLASS_PER_CHUNK, len(fraud)),
                    random_state=42,
                )
            )

        if not normal.empty:
            selected_chunks.append(
                normal.sample(
                    n=min(SAMPLES_PER_CLASS_PER_CHUNK, len(normal)),
                    random_state=42,
                )
            )

        print(f"Processed dataset chunk {chunk_number}")

    if not selected_chunks:
        raise ValueError("No eligible transactions were found.")

    result = pd.concat(selected_chunks, ignore_index=True)

    # Convert PaySim column names to the project's common schema.
    result = result.rename(
        columns={
            "nameOrig": "sender_id",
            "nameDest": "receiver_id",
            "isFraud": "is_fraud",
            "type": "transaction_type",
        }
    )

    result.insert(
        0,
        "transaction_id",
        [f"PS{i:06d}" for i in range(1, len(result) + 1)],
    )

    # PaySim does not provide device IDs or IP addresses.
    result["device_id"] = ""
    result["ip_address"] = ""

    output_columns = [
        "transaction_id",
        "sender_id",
        "receiver_id",
        "device_id",
        "ip_address",
        "amount",
        "is_fraud",
        "transaction_type",
    ]

    result = result[output_columns]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)

    print("\nPaySim sample created successfully!")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Transactions: {len(result)}")
    print(f"Fraud-labelled: {(result['is_fraud'] == 1).sum()}")
    print(f"Non-fraud-labelled: {(result['is_fraud'] == 0).sum()}")


if __name__ == "__main__":
    main()
