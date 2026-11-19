py -m venv .venv-dashboard
# FraudLens - Fraud Transaction Relationship Detection

A Python Flask dashboard for exploring transaction records, identifying suspicious account relationships, and reviewing rule-based risk scores.

## Features

- Transaction statistics
- Fraud versus non-fraud chart
- Transaction amount distribution chart
- Account relationship graph
- Account risk analysis table
- CSV dataset upload
- CSV exports
- Transaction search

## Project Structure

```text
dashboard/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
```

## Requirements

- Python 3.14, if compatible with all installed dependencies
- A web browser
- An internet connection for Chart.js and Cytoscape.js CDN libraries

## Installation

Open PowerShell in the main project directory.

Create a virtual environment:

```powershell
py -3.14 -m venv .venv-dashboard
```

Install the dependencies:

```powershell
.\.venv-dashboard\Scripts\python.exe -m pip install -r .\dashboard\requirements.txt
```

## Dataset

The dashboard searches for a CSV file in these locations:

1. `transactions.csv` in the project root
2. `data/processed/paysim_sample.csv`
3. `dashboard/transactions.csv`
4. `dashboard/data/processed/paysim_sample.csv`

You can also upload a CSV using the dashboard interface.

The CSV should contain transaction fields such as sender, receiver, amount, and fraud status. The application attempts to recognize common column names automatically.

## Run the Dashboard

From the main project directory:

```powershell
.\.venv-dashboard\Scripts\python.exe .\dashboard\app.py
```

Open this address in your browser:

http://127.0.0.1:5000

Stop the server with `Ctrl + C` in the terminal.

## Important Notes

- Risk scores are heuristic indicators, not machine-learning predictions.
- Missing device or IP information limits relationship analysis.
- The graph displays a limited sample of transactions to improve performance.
- This project is intended for academic demonstration, not real-world fraud decisions.
