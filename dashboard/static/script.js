
const $ = (id) => document.getElementById(id);

let fraudChart = null;
let amountChart = null;
let allTransactions = [];
let allRisk = [];
let graphInstance = null;

const money = (value) =>
    new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2
    }).format(Number(value) || 0);

function showMessage(message, type = "") {
    const element = $("message");
    element.textContent = message;
    element.className = "message visible";

    if (type) {
        element.classList.add(type);
    }
}

function hideMessage() {
    $("message").className = "message";
    $("message").textContent = "";
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

async function fetchDashboard() {
    $("refreshBtn").disabled = true;
    showMessage("Loading transaction data...");

    try {
        const response = await fetch("/api/dashboard");
        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || "Unable to load dashboard.");
        }

        if (!data.configured) {
            allTransactions = [];
            allRisk = [];
            renderTransactions([]);
            renderRisk([]);
            updateStats({});
            drawCharts({});
            drawGraph([], []);
            showMessage(data.message || "No dataset found.", "error");
            return;
        }

        hideMessage();

        allTransactions = data.transactions || [];
        allRisk = data.risk || [];

        updateStats(data.stats || {});
        drawCharts(data.stats || {});
        renderTransactions(allTransactions);
        renderRisk(allRisk);
        drawGraph(data.nodes || [], data.edges || []);

        showMessage(
            `Loaded ${Number(data.stats?.total || 0).toLocaleString("en-IN")} transactions from ${data.source || "CSV"}.`,
            "success"
        );
    } catch (error) {
        showMessage(error.message, "error");
    } finally {
        $("refreshBtn").disabled = false;
    }
}

function updateStats(stats) {
    $("totalTransactions").textContent =
        Number(stats.total || 0).toLocaleString("en-IN");

    $("fraudTransactions").textContent =
        Number(stats.fraud || 0).toLocaleString("en-IN");

    $("normalTransactions").textContent =
        Number(stats.nonfraud || 0).toLocaleString("en-IN");

    $("totalAmount").textContent = money(stats.amount);

    $("totalAccounts").textContent =
        Number(stats.accounts || 0).toLocaleString("en-IN");
}

function drawCharts(stats) {
    if (fraudChart) fraudChart.destroy();
    if (amountChart) amountChart.destroy();

    const fraudCanvas = $("fraudChart");
    const amountCanvas = $("amountChart");

    if (!fraudCanvas || !amountCanvas) return;

    fraudChart = new Chart(fraudCanvas, {
        type: "doughnut",
        data: {
            labels: ["Fraud", "Non-Fraud"],
            datasets: [{
                data: [
                    Number(stats.fraud || 0),
                    Number(stats.nonfraud || 0)
                ],
                backgroundColor: ["#dc2626", "#16a34a"],
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });

    const buckets = [0, 0, 0, 0, 0];
    const labels = [
        "0–1K",
        "1K–10K",
        "10K–50K",
        "50K–100K",
        "100K+"
    ];

    allTransactions.forEach((transaction) => {
        const amount = Number(transaction.amount) || 0;

        if (amount <= 1000) buckets[0]++;
        else if (amount <= 10000) buckets[1]++;
        else if (amount <= 50000) buckets[2]++;
        else if (amount <= 100000) buckets[3]++;
        else buckets[4]++;
    });

    amountChart = new Chart(amountCanvas, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Transactions in loaded records",
                data: buckets,
                backgroundColor: "#6366f1",
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

function renderTransactions(transactions) {
    const tbody = $("transactionTable");

    if (!transactions.length) {
        tbody.innerHTML =
            '<tr><td colspan="5">No transaction records available.</td></tr>';
        return;
    }

    tbody.innerHTML = transactions.map((transaction) => {
        const status = transaction.fraud ? "Fraud" : "Non-Fraud";
        const badge = transaction.fraud ? "fraud" : "normal";

        return `
            <tr>
                <td>${escapeHTML(transaction.id)}</td>
                <td>${escapeHTML(transaction.sender)}</td>
                <td>${escapeHTML(transaction.receiver)}</td>
                <td>${escapeHTML(money(transaction.amount))}</td>
                <td><span class="badge ${badge}">${status}</span></td>
            </tr>
        `;
    }).join("");
}

function renderRisk(risk) {
    const tbody = $("riskTable");

    if (!risk.length) {
        tbody.innerHTML =
            '<tr><td colspan="8">No risk records available.</td></tr>';
        return;
    }

    tbody.innerHTML = risk.map((account) => {
        const level = String(account.risk_level || "Low").toLowerCase();
        const badge = ["high", "review", "low"].includes(level)
            ? level
            : "low";

        return `
            <tr>
                <td>${escapeHTML(account.account)}</td>
                <td>${Number(account.transactions || 0)}</td>
                <td>${escapeHTML(money(account.total_amount))}</td>
                <td>${Number(account.fraud_count || 0)}</td>
                <td>${account.shared_device ? "Yes" : "No"}</td>
                <td>${account.shared_ip ? "Yes" : "No"}</td>
                <td>${Number(account.risk_score || 0)}/100</td>
                <td><span class="badge ${badge}">${escapeHTML(account.risk_level)}</span></td>
            </tr>
        `;
    }).join("");
}

function drawGraph(nodes, edges) {
    const container = $("relationshipGraph");

    if (!container || typeof cytoscape === "undefined") {
        showMessage(
            "Graph library did not load. Check your internet connection.",
            "error"
        );
        return;
    }

    if (graphInstance) {
        graphInstance.destroy();
        graphInstance = null;
    }

    if (!nodes.length) {
        container.innerHTML = "";
        container.textContent = "No relationships to display.";
        return;
    }

    graphInstance = cytoscape({
        container,
        elements: [...nodes, ...edges],
        layout: {
            name: "cose",
            animate: false,
            padding: 30
        },
        style: [
            {
                selector: "node",
                style: {
                    "label": "data(label)",
                    "font-size": 10,
                    "text-wrap": "wrap",
                    "text-max-width": 90,
                    "text-valign": "bottom",
                    "text-halign": "center",
                    "background-color": "#6366f1",
                    "color": "#1f2937",
                    "width": 28,
                    "height": 28
                }
            },
            {
                selector: 'node[kind = "device"]',
                style: {
                    "background-color": "#f59e0b",
                    "shape": "diamond"
                }
            },
            {
                selector: 'node[kind = "ip"]',
                style: {
                    "background-color": "#0891b2",
                    "shape": "round-rectangle"
                }
            },
            {
                selector: "edge",
                style: {
                    "width": 1.5,
                    "line-color": "#a5b4fc",
                    "target-arrow-color": "#a5b4fc",
                    "target-arrow-shape": "triangle",
                    "curve-style": "bezier"
                }
            },
            {
                selector: 'edge[fraud = true]',
                style: {
                    "line-color": "#dc2626",
                    "target-arrow-color": "#dc2626",
                    "width": 3
                }
            }
        ]
    });
}

function filterTransactions() {
    const query = $("searchInput").value.trim().toLowerCase();

    const filtered = allTransactions.filter((transaction) => {
        return [
            transaction.id,
            transaction.sender,
            transaction.receiver,
            transaction.device,
            transaction.ip
        ].some((value) => String(value ?? "").toLowerCase().includes(query));
    });

    renderTransactions(filtered);
}

async function uploadCSV(event) {
    event.preventDefault();

    const fileInput = $("csvFile");
    const file = fileInput.files[0];

    if (!file) {
        showMessage("Please select a CSV file first.", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    showMessage("Uploading CSV...");

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Upload failed.");
        }

        fileInput.value = "";
        await fetchDashboard();

        showMessage(`Successfully uploaded ${result.filename}.`, "success");
    } catch (error) {
        showMessage(error.message, "error");
    }
}

$("refreshBtn").addEventListener("click", fetchDashboard);
$("searchInput").addEventListener("input", filterTransactions);
$("uploadForm").addEventListener("submit", uploadCSV);

fetchDashboard();
