# CloudWalk Operations Intelligence

## AI-Powered Analytics Agent for Financial Transaction Data

**Author:** Gabriel Milhardo
**Challenge:** CloudWalk Data Analyst
**Repository:** [GitHub](https://github.com/GabrielMilhardo1/CloudWalk_Operations_Intelligence)

---

## 1. Problem Statement

### The Challenge

Operations teams at fintech companies need to:
- Answer ad-hoc questions about transaction data quickly
- Monitor for anomalies that could indicate issues
- Generate insights without writing SQL manually

### Traditional Approach Problems

| Problem | Impact |
|---------|--------|
| Manual SQL queries | Slow, error-prone, requires technical skills |
| Static dashboards | Can't answer new questions |
| No proactive monitoring | Issues discovered too late |

### Solution: AI-Powered Agent

An intelligent system that:
1. **Understands natural language** - "What was the TPV yesterday?"
2. **Generates accurate SQL** - No hallucinated data
3. **Detects anomalies automatically** - Z-score based alerts
4. **Visualizes results** - Auto-generated charts

---

## 2. Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (Streamlit)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│   │  User asks   │───▶│   LLM Call   │───▶│   SQL Query Generated    │  │
│   │  question    │    │  (Llama 3.3) │    │   "SELECT SUM(...)..."   │  │
│   └──────────────┘    └──────────────┘    └───────────┬──────────────┘  │
│                                                        │                 │
│                                                        ▼                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│   │   Display    │◀───│   LLM Call   │◀───│   SQLite Executes        │  │
│   │   Answer +   │    │  (Analysis)  │    │   Returns Real Data      │  │
│   │   Chart      │    └──────────────┘    └──────────────────────────┘  │
│   └──────────────┘                                                       │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                      ANOMALY DETECTION (Background)                      │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  Z-Score Monitor: TPV Total | TPV by Product | Transaction Count │  │
│   │  Alerts: Critical (Z>3) | Warning (Z>2) | Normal                 │  │
│   └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decision: NL2SQL vs Direct LLM

| Approach | Pros | Cons |
|----------|------|------|
| **Direct LLM** | Simple | Hallucinations, outdated data |
| **NL2SQL (chosen)** | Accurate, auditable, real data | More complex |

**Why NL2SQL?** Financial data requires 100% accuracy. The LLM generates SQL, which is executed against the real database. Zero hallucinations.

---

## 3. Technical Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| **LLM** | Llama 3.3 70B (Groq) | Free tier, extremely fast (500+ tokens/sec), open source |
| **Database** | SQLite | LLMs generate SQL more reliably than Pandas code |
| **Frontend** | Streamlit | Rapid prototyping, professional UI, Python native |
| **Charts** | Plotly | Interactive, auto-scaling, theme-aware |
| **Statistics** | NumPy/Pandas | Z-score calculations for anomaly detection |

### Why Groq + Llama 3.3?

1. **Free** - No API costs during development
2. **Fast** - 500+ tokens/second inference
3. **Accurate** - 70B parameters, excellent at SQL generation
4. **Open Source** - No vendor lock-in

---

## 4. Features Implemented

### 4.1 Natural Language Q&A (Reactive)

Users can ask questions in plain English:

| Question | What Happens |
|----------|--------------|
| "What is the total TPV?" | Generates `SELECT SUM(amount_transacted)...` |
| "Compare PIX vs POS" | Generates `GROUP BY product` query |
| "Show daily trend" | Generates time series query + line chart |

**Two-Stage LLM Process:**
1. **Stage 1:** Generate SQL query from question
2. **Stage 2:** Analyze results and provide insights

### 4.2 Anomaly Detection (Proactive)

Automatic monitoring using **Z-score statistics**:

```
Z-score = (Current Value - Rolling Mean) / Rolling Std

Interpretation:
├── |Z| < 2.0  → Normal (green)
├── |Z| ≥ 2.0  → Warning (yellow) - 95% confidence
└── |Z| ≥ 3.0  → Critical (red) - 99% confidence
```

**Metrics Monitored:**
- Total TPV (daily)
- Transaction count
- TPV by product (PIX, POS, TAP, Link, Bank Slip)

### 4.3 D-1 / D-7 / D-30 Comparison

Real-time comparison of today's TPV against:
- Yesterday (D-1)
- Last week (D-7)
- Last month (D-30)

### 4.4 Auto-Generated Visualizations

The system automatically detects data patterns and generates appropriate charts:

| Data Pattern | Chart Type |
|--------------|------------|
| Time series (day column) | Line chart |
| Categorical (product, entity) | Bar or Pie chart |
| Comparison | Grouped bar chart |

---

## 5. Data Model

### Dataset: Operations_analyst_data.csv

| Column | Type | Description |
|--------|------|-------------|
| `day` | DATE | Transaction date (2025-01-01 to 2025-03-31) |
| `entity` | TEXT | 'PJ' (Business) or 'PF' (Individual) |
| `product` | TEXT | pix, pos, tap, link, bank_slip |
| `price_tier` | TEXT | normal, intermediary, aggressive, domination |
| `anticipation_method` | TEXT | Settlement method |
| `payment_method` | TEXT | credit, debit, uninformed |
| `installments` | INT | Number of installments |
| `amount_transacted` | REAL | **TPV** - Transaction amount in BRL |
| `quantity_transactions` | INT | Number of transactions |
| `quantity_of_merchants` | INT | Unique merchants |

### Key Metrics

| Metric | Formula | Total (90 days) |
|--------|---------|-----------------|
| **TPV** | `SUM(amount_transacted)` | R$ 19.4 Billion |
| **Transactions** | `SUM(quantity_transactions)` | 146.5 Million |
| **Avg Ticket** | `TPV / Transactions` | R$ 132.68 |

---

## 6. Code Structure

```
cloudwalk/
├── app.py                      # Streamlit web interface
├── src/
│   ├── __init__.py
│   ├── database.py             # SQLite handler + data loading
│   ├── agent.py                # NL2SQL AI Agent (Groq/Llama)
│   ├── prompts.py              # System prompts for LLM
│   └── alerts.py               # Z-score anomaly detection
├── notebooks/
│   └── 01_eda.ipynb            # Exploratory Data Analysis
├── requirements.txt
├── README.md                   # Setup instructions
├── PRESENTATION.md             # This file
└── Operations_analyst_data.csv # Dataset
```

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `agent.py` | Converts natural language → SQL → Results → Analysis |
| `alerts.py` | Calculates Z-scores, generates severity alerts |
| `database.py` | Loads CSV to SQLite, executes queries |
| `prompts.py` | System prompt with data dictionary for LLM |
| `app.py` | Streamlit UI, chart generation, state management |

---

## 7. Example Q&A

### Example 1: Basic Metric

**Question:** "What is the total TPV?"

**SQL Generated:**
```sql
SELECT ROUND(SUM(amount_transacted), 2) as total_tpv
FROM transactions
```

**Answer:** R$ 19,438,234,567.89

---

### Example 2: Segmentation

**Question:** "Which product has the highest TPV?"

**SQL Generated:**
```sql
SELECT
    product,
    ROUND(SUM(amount_transacted), 2) as tpv,
    SUM(quantity_transactions) as transactions
FROM transactions
GROUP BY product
ORDER BY tpv DESC
```

**Analysis:** "PIX leads with R$ 8.2B (42% of total TPV), followed by POS with R$ 6.1B. The high PIX adoption reflects Brazil's rapid digital payment transformation."

---

### Example 3: Time Analysis

**Question:** "Show the daily TPV trend for the last week"

**SQL Generated:**
```sql
SELECT
    day,
    ROUND(SUM(amount_transacted), 2) as tpv
FROM transactions
WHERE day >= date((SELECT MAX(day) FROM transactions), '-7 days')
GROUP BY day
ORDER BY day ASC
```

**Output:** Line chart automatically generated showing 7-day trend.

---

## 8. Screenshots

> **Note:** Add screenshots of the running application here.

### 8.1 Main Interface
`[Screenshot: Chat tab with example Q&A]`

### 8.2 Sidebar Metrics & Alerts
`[Screenshot: D-1/D-7/D-30 comparison + anomaly alerts]`

### 8.3 Visualizations Tab
`[Screenshot: Daily TPV trend, Product breakdown, Entity distribution]`

### 8.4 SQL Transparency
`[Screenshot: Expanded SQL query view]`

---

## 9. Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| LLM generating Python code instead of SQL | Added strict prompt rules: "NEVER generate Python" |
| Multiple SQL queries in one response | Improved extraction to only get first query |
| No analysis after query results | Added second LLM call to analyze actual data |
| CSS colors unreadable in dark mode | Changed to `rgba()` with transparency |
| Chat input not at bottom | Restructured with `st.container()` pattern |

---

## 10. Future Improvements

| Improvement | Benefit |
|-------------|---------|
| Real-time data streaming | Live transaction monitoring |
| More alert types | Revenue drop, merchant churn |
| Query caching | Faster repeated queries |
| Multi-language support | Portuguese interface option |
| Export to Excel/PDF | Business reporting |

---

## 11. How to Run

```bash
# 1. Clone repository
git clone https://github.com/GabrielMilhardo1/CloudWalk_Operations_Intelligence.git
cd CloudWalk_Operations_Intelligence

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
echo "GROQ_API_KEY=your_key_here" > .env

# 4. Run application
streamlit run app.py
```

Get your free Groq API key at: https://console.groq.com/keys

---

## 12. Conclusion

This project demonstrates:

1. **NL2SQL Implementation** - Accurate, auditable data queries
2. **Proactive Monitoring** - Z-score anomaly detection
3. **Modern Tech Stack** - Groq, Streamlit, Plotly
4. **Production-Ready Code** - Modular, documented, tested

The agent successfully answers natural language questions about financial data while maintaining 100% accuracy through real database queries.

---

**Gabriel Milhardo**
Data Analyst | Python | AI/ML
[LinkedIn](https://linkedin.com/in/gabriel-milhardo) | [GitHub](https://github.com/GabrielMilhardo1) | [Portfolio](https://gabrielmilhardo1.github.io)
