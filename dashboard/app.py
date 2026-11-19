
from pathlib import Path

import pandas as pd
import networkx as nx
from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parent

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

CANDIDATES = [
    PROJECT / "transactions.csv",
    PROJECT / "data" / "processed" / "paysim_sample.csv",
    BASE / "transactions.csv",
    BASE / "data" / "processed" / "paysim_sample.csv",
]

current_upload = None


def locate_data():
    if current_upload and Path(current_upload).exists():
        return Path(current_upload)

    for path in CANDIDATES:
        if path.exists() and path.stat().st_size > 0:
            return path

    return None


def read_data():
    path = locate_data()

    if path is None:
        return pd.DataFrame(), None

    try:
        return pd.read_csv(path, nrows=50000, low_memory=False), path
    except Exception as exc:
        raise ValueError(f"Could not read CSV: {exc}")


def find_column(df, candidates):
    columns = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for name in candidates:
        if name.lower() in columns:
            return columns[name.lower()]

    for column in df.columns:
        if any(name.lower() in str(column).lower()
               for name in candidates):
            return column

    return None


def is_fraud(value):
    return str(value).strip().lower() in {
        "1", "true", "yes", "fraud"
    }


def make_payload():
    df, path = read_data()

    if df.empty:
        return {
            "configured": False,
            "message": (
                "No usable CSV found. Add transactions.csv "
                "to the project root or place paysim_sample.csv "
                "inside data/processed."
            ),
            "columns": [],
            "transactions": [],
            "risk": [],
            "nodes": [],
            "edges": [],
            "stats": {}
        }

    sender = find_column(
        df, ["nameOrig", "sender", "source",
             "from_account", "sender_id", "account"]
    )
    receiver = find_column(
        df, ["nameDest", "receiver", "target",
             "to_account", "receiver_id"]
    )
    amount = find_column(
        df, ["amount", "transaction_amount", "value"]
    )
    fraud = find_column(
        df, ["isFraud", "is_fraud", "fraud",
             "fraud_label", "label"]
    )
    txid = find_column(
        df, ["transaction_id", "transactionid",
             "txn_id", "id"]
    )
    device = find_column(df, ["device_id", "device"])
    ip = find_column(df, ["ip_address", "ip"])

    work = df.copy()

    work["_amount"] = (
        pd.to_numeric(work[amount], errors="coerce").fillna(0)
        if amount else 0
    )

    work["_fraud"] = (
        work[fraud].map(is_fraud)
        if fraud else False
    )

    work["_sender"] = (
        work[sender].fillna("Unknown sender").astype(str)
        if sender else "Unknown sender"
    )

    work["_receiver"] = (
        work[receiver].fillna("Unknown receiver").astype(str)
        if receiver else "Unknown receiver"
    )

    work["_txid"] = (
        work[txid].astype(str)
        if txid else [
            f"TXN-{i + 1}" for i in range(len(work))
        ]
    )

    work["_device"] = (
        work[device].fillna("").astype(str).str.strip()
        if device else ""
    )

    work["_ip"] = (
        work[ip].fillna("").astype(str).str.strip()
        if ip else ""
    )

    risk = []

    for account, group in work.groupby("_sender", dropna=False):
        devices = set(
            group.loc[group["_device"] != "", "_device"]
        )
        ips = set(
            group.loc[group["_ip"] != "", "_ip"]
        )

        fraud_count = int(group["_fraud"].sum())

        shared_device = any(
            (work["_device"] == value).sum() > 1
            for value in devices
        )

        shared_ip = any(
            (work["_ip"] == value).sum() > 1
            for value in ips
        )

        score = min(
            100,
            fraud_count * 45
            + int(shared_device) * 20
            + int(shared_ip) * 20
            + (15 if group["_amount"].sum() > 100000 else 0)
        )

        risk.append({
            "account": str(account),
            "transactions": int(len(group)),
            "total_amount": round(
                float(group["_amount"].sum()), 2
            ),
            "fraud_count": fraud_count,
            "shared_device": bool(shared_device),
            "shared_ip": bool(shared_ip),
            "risk_score": score,
            "risk_level": (
                "High" if score >= 60
                else "Review" if score >= 25
                else "Low"
            )
        })

    risk.sort(
        key=lambda item: (
            item["risk_score"], item["total_amount"]
        ),
        reverse=True
    )

    transactions = []

    for _, row in work.head(1000).iterrows():
        transactions.append({
            "id": str(row["_txid"]),
            "sender": str(row["_sender"]),
            "receiver": str(row["_receiver"]),
            "amount": round(float(row["_amount"]), 2),
            "fraud": bool(row["_fraud"]),
            "device": str(row["_device"]),
            "ip": str(row["_ip"])
        })

    # Build a relationship graph for the first 250 transactions.
    graph_df = work.head(250)
    nodes = []
    edges = []
    seen = set()

    for _, row in graph_df.iterrows():
        for key in ["_sender", "_receiver"]:
            value = str(row[key])

            if value not in seen:
                seen.add(value)
                nodes.append({
                    "data": {
                        "id": value,
                        "label": value,
                        "kind": "account"
                    }
                })

        edges.append({
            "data": {
                "id": str(row["_txid"]),
                "source": str(row["_sender"]),
                "target": str(row["_receiver"]),
                "amount": round(float(row["_amount"]), 2),
                "fraud": bool(row["_fraud"])
            }
        })

        for field, kind in [
            ("_device", "device"),
            ("_ip", "ip")
        ]:
            value = str(row[field]).strip()

            if value and value.lower() not in {"nan", "none"}:
                node_id = f"{kind}:{value}"

                if node_id not in seen:
                    seen.add(node_id)
                    nodes.append({
                        "data": {
                            "id": node_id,
                            "label": value,
                            "kind": kind
                        }
                    })

                edges.append({
                    "data": {
                        "id": f"{kind}-{row['_txid']}-{row['_sender']}",
                        "source": str(row["_sender"]),
                        "target": node_id,
                        "amount": 0,
                        "fraud": False,
                        "relation": kind
                    }
                })

    return {
        "configured": True,
        "source": path.name if path else "uploaded CSV",
        "columns": list(map(str, df.columns)),
        "transactions": transactions,
        "risk": risk,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total": int(len(df)),
            "fraud": int(work["_fraud"].sum()),
            "nonfraud": int(
                len(work) - work["_fraud"].sum()
            ),
            "amount": round(
                float(work["_amount"].sum()), 2
            ),
            "accounts": int(work["_sender"].nunique())
        },
        "fields": {
            "sender": str(sender) if sender else None,
            "receiver": str(receiver) if receiver else None,
            "amount": str(amount) if amount else None,
            "fraud": str(fraud) if fraud else None
        }
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    try:
        return jsonify(make_payload())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/upload", methods=["POST"])
def upload():
    global current_upload

    file = request.files.get("file")

    if not file or not file.filename.lower().endswith(".csv"):
        return jsonify({
            "error": "Please choose a CSV file."
        }), 400

    filename = secure_filename(file.filename)
    destination = UPLOAD_DIR / filename
    file.save(destination)

    current_upload = str(destination)

    return jsonify({
        "ok": True,
        "filename": filename
    })


@app.route("/api/export/transactions")
def export_transactions():
    payload = make_payload()

    if not payload.get("configured"):
        return jsonify({
            "error": payload.get("message", "No dataset")
        }), 404

    return send_file(
        locate_data(),
        as_attachment=True,
        download_name="transactions_export.csv"
    )


@app.route("/api/export/risk")
def export_risk():
    payload = make_payload()

    if not payload.get("configured"):
        return jsonify({
            "error": payload.get("message", "No dataset")
        }), 404

    output = BASE / "account_risk_dashboard.csv"

    pd.DataFrame(payload["risk"]).to_csv(
        output, index=False
    )

    return send_file(
        output,
        as_attachment=True,
        download_name="account_risk.csv"
    )


if __name__ == "__main__":
    print("Fraud dashboard: http://127.0.0.1:5000")
    app.run(debug=True)
