# 🏦 CloudWalk Operations Intelligence

AI-powered analytics agent for financial transaction data analysis.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)
![Llama](https://img.shields.io/badge/LLM-Llama%203.3-green.svg)

## 📋 Overview

This project implements an **Operations Intelligence** system that allows users to:

1. **Ask Questions in Natural Language**: "What was the TPV yesterday?" → SQL → Answer
2. **Detect Anomalies Automatically**: Z-score based monitoring for unusual patterns
3. **Visualize Data Interactively**: Charts and dashboards for data exploration

Built for the **CloudWalk Data Analyst Challenge**.

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Navigate to project
cd cloudwalk

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file with your Groq API key:

```bash
GROQ_API_KEY=gsk_your_api_key_here
```

Get a free API key at: https://console.groq.com/keys

### 3. Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 📊 Features

### 💬 Natural Language Q&A

Ask questions about the data in plain English:

| Question | What It Does |
|----------|--------------|
| "What was the total TPV?" | Calculates sum of all transactions |
| "Which product has highest revenue?" | Ranks products by TPV |
| "Compare PJ vs PF" | Breaks down by entity type |
| "Show TPV trend for last week" | Time series analysis |

The AI agent translates your question into SQL, executes it, and returns the answer.

### 🚨 Anomaly Detection

Automatic monitoring using **Z-score statistics**:

```
Z-score = (Current Value - Historical Mean) / Standard Deviation

Interpretation:
- Z < -2: Significant drop (Warning ⚠️)
- Z < -3: Critical drop (Alert 🔴)
- Z > 2: Significant spike (Warning ⚠️)
- Z > 3: Critical spike (Alert 🔴)
```

The system monitors:
- Total TPV
- Transaction count
- TPV by product (PIX, POS, TAP, etc.)

### 📈 Visualizations

- **Daily TPV Trend**: Line chart of transaction volume over time
- **TPV by Product**: Bar chart comparing payment products
- **Entity Distribution**: Pie chart of Business vs Individual

---

## 🏗️ Architecture

```
cloudwalk/
├── app.py                    # Streamlit web interface
├── notebooks/
│   └── 01_eda.ipynb         # Exploratory Data Analysis
├── src/
│   ├── __init__.py
│   ├── database.py          # SQLite database handler
│   ├── agent.py             # AI Agent (NL2SQL)
│   ├── prompts.py           # LLM system prompts
│   └── alerts.py            # Anomaly detection
├── requirements.txt
├── .env                     # API keys (gitignored)
└── Operations_analyst_data.csv
```

### Data Flow

```
User Question
      │
      ▼
┌─────────────────┐
│   AI Agent      │ ← System Prompt (data dictionary)
│  (Llama 3.3)    │
└────────┬────────┘
         │ SQL Query
         ▼
┌─────────────────┐
│    SQLite       │ ← Operations_analyst_data.csv
│   Database      │
└────────┬────────┘
         │ Results
         ▼
┌─────────────────┐
│   Streamlit     │ → User sees answer + charts
│   Interface     │
└─────────────────┘
```

---

## 📊 Dataset

**File**: `Operations_analyst_data.csv`

| Column | Type | Description |
|--------|------|-------------|
| day | DATE | Transaction date |
| entity | TEXT | 'PJ' (Business) or 'PF' (Individual) |
| product | TEXT | pix, pos, tap, link, bank_slip |
| price_tier | TEXT | normal, intermediary, aggressive, domination |
| anticipation_method | TEXT | Pix, D1Anticipation, D0/Nitro, Bank Slip |
| payment_method | TEXT | credit, debit, uninformed |
| installments | INT | Number of installments |
| amount_transacted | REAL | **TPV** - Transaction amount in BRL |
| quantity_transactions | INT | Number of transactions |
| quantity_of_merchants | INT | Number of unique merchants |

### Key Metrics

- **TPV (Total Payment Volume)**: `SUM(amount_transacted)` = R$ 19.4B
- **Transaction Count**: `SUM(quantity_transactions)` = 146.5M
- **Average Ticket**: `TPV / Transactions` = R$ 132.68
- **Date Range**: January 1 - March 31, 2025 (90 days)

---

## 🔧 Technical Stack

| Component | Technology | Why |
|-----------|------------|-----|
| **LLM** | Llama 3.3 70B via Groq | Free, fast (500+ tokens/sec), open source |
| **Database** | SQLite | LLM generates SQL more reliably than Pandas |
| **Framework** | Streamlit | Rapid prototyping, professional UI |
| **Charts** | Plotly | Interactive visualizations |
| **Statistics** | NumPy/Pandas | Z-score anomaly detection |

---

## 📈 Anomaly Detection Methodology

### Z-Score Algorithm

```python
def detect_anomaly(current_value, rolling_mean, rolling_std, threshold=2.0):
    """
    Calculate Z-score and determine if value is anomalous.

    Args:
        current_value: Today's metric value
        rolling_mean: 30-day rolling average
        rolling_std: 30-day rolling standard deviation
        threshold: Z-score threshold for alerts (default: 2.0)

    Returns:
        dict with z_score, is_anomaly, severity
    """
    z_score = (current_value - rolling_mean) / rolling_std

    if abs(z_score) >= 3.0:
        severity = "critical"
    elif abs(z_score) >= 2.0:
        severity = "warning"
    else:
        severity = "normal"

    return {
        "z_score": z_score,
        "is_anomaly": abs(z_score) >= threshold,
        "severity": severity
    }
```

### Why Z-Score?

1. **Statistically rigorous**: Based on normal distribution properties
2. **Easy to explain**: "More than 2 standard deviations from average"
3. **Configurable**: Adjust threshold based on business needs
4. **Fast**: O(n) computation with rolling window

---

## 🧪 Testing

### Run EDA Notebook

```bash
jupyter notebook notebooks/01_eda.ipynb
```

### Test Database Module

```bash
python -m src.database
```

### Test AI Agent

```bash
python -m src.agent
```

### Test Anomaly Detection

```bash
python -m src.alerts
```

---

## 📝 Example Questions

Try these questions in the chat interface:

1. **Basic Metrics**
   - "What is the total TPV?"
   - "How many transactions were processed?"
   - "What's the average ticket value?"

2. **Product Analysis**
   - "Which product has the highest TPV?"
   - "Compare PIX vs POS revenue"
   - "Show me TPV by product"

3. **Entity Analysis**
   - "Compare Business vs Individual transactions"
   - "What percentage of TPV comes from PJ?"

4. **Time Analysis**
   - "What was the TPV yesterday?"
   - "Show me the daily trend for last week"
   - "Which day had the highest TPV?"

5. **Payment Methods**
   - "Compare credit vs debit transactions"
   - "What's the average ticket for credit cards?"

---

## 👤 Author

**Gabriel Milhardo**

- LinkedIn: [Gabriel Milhardo](https://linkedin.com/in/gabriel-milhardo)
- GitHub: [GabrielMilhardo1](https://github.com/GabrielMilhardo1)
- Portfolio: [gabrielmilhardo1.github.io](https://gabrielmilhardo1.github.io)

---

## 📄 License

This project was created for the CloudWalk Data Analyst technical challenge.

---

## 🙏 Acknowledgments

- **CloudWalk** for the challenge dataset and opportunity
- **Groq** for free Llama 3 API access
- **Streamlit** for the excellent web framework
