"""
CloudWalk Operations Intelligence - Streamlit Application

This is the main entry point for the web interface.
It provides:
1. Chat interface for natural language Q&A
2. Real-time alerts panel
3. Key metrics dashboard
4. Data visualizations

Author: Gabriel Milhardo
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import Database, setup_database
from src.agent import CloudWalkAgent
from src.alerts import AnomalyDetector, AlertSeverity


# Page configuration
st.set_page_config(
    page_title="CloudWalk Operations Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Theme aware
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .alert-critical {
        background-color: rgba(244, 67, 54, 0.2);
        border-left: 4px solid #f44336;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-radius: 4px;
        color: inherit;
    }
    .alert-warning {
        background-color: rgba(255, 152, 0, 0.2);
        border-left: 4px solid #ff9800;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-radius: 4px;
        color: inherit;
    }
    .alert-normal {
        background-color: rgba(76, 175, 80, 0.2);
        border-left: 4px solid #4caf50;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-radius: 4px;
        color: inherit;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_database():
    """Initialize database (cached)."""
    return setup_database()


@st.cache_resource
def init_agent(_db):
    """Initialize AI agent (cached)."""
    return CloudWalkAgent(db=_db)


@st.cache_resource
def init_detector(_db):
    """Initialize anomaly detector (cached)."""
    return AnomalyDetector(db=_db)


def format_currency(value: float) -> str:
    """Format number as BRL currency."""
    if value >= 1_000_000_000:
        return f"R$ {value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"R$ {value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"R$ {value/1_000:.2f}K"
    else:
        return f"R$ {value:.2f}"


def format_number(value: float) -> str:
    """Format large numbers with suffixes."""
    if value >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value/1_000:.2f}K"
    else:
        return f"{value:.0f}"


def render_sidebar(db: Database, detector: AnomalyDetector):
    """Render sidebar with metrics and alerts."""

    st.sidebar.markdown("## 📊 Key Metrics")

    # ===== D-1, D-7, D-30 Comparison =====
    comparison_data = db.execute_query("""
        WITH daily_tpv AS (
            SELECT day, SUM(amount_transacted) as tpv
            FROM transactions
            GROUP BY day
        ),
        latest AS (
            SELECT MAX(day) as max_day FROM transactions
        )
        SELECT
            (SELECT tpv FROM daily_tpv WHERE day = (SELECT max_day FROM latest)) as today_tpv,
            (SELECT tpv FROM daily_tpv WHERE day = date((SELECT max_day FROM latest), '-1 day')) as d1_tpv,
            (SELECT tpv FROM daily_tpv WHERE day = date((SELECT max_day FROM latest), '-7 day')) as d7_tpv,
            (SELECT tpv FROM daily_tpv WHERE day = date((SELECT max_day FROM latest), '-30 day')) as d30_tpv
    """).iloc[0]

    today_tpv = comparison_data['today_tpv'] or 0
    d1_tpv = comparison_data['d1_tpv'] or today_tpv
    d7_tpv = comparison_data['d7_tpv'] or today_tpv
    d30_tpv = comparison_data['d30_tpv'] or today_tpv

    # Calculate variations
    var_d1 = ((today_tpv - d1_tpv) / d1_tpv * 100) if d1_tpv else 0
    var_d7 = ((today_tpv - d7_tpv) / d7_tpv * 100) if d7_tpv else 0
    var_d30 = ((today_tpv - d30_tpv) / d30_tpv * 100) if d30_tpv else 0

    st.sidebar.markdown("### 📅 TPV Today vs History")
    st.sidebar.metric(
        "vs Yesterday (D-1)",
        f"R$ {today_tpv/1e6:.1f}M",
        f"{var_d1:+.1f}%"
    )
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("vs D-7", f"{var_d7:+.1f}%")
    with col2:
        st.metric("vs D-30", f"{var_d30:+.1f}%")

    st.sidebar.markdown("---")

    # Get quick stats
    stats = db.execute_query("""
        SELECT
            ROUND(SUM(amount_transacted), 2) as total_tpv,
            SUM(quantity_transactions) as total_txns,
            MIN(day) as start_date,
            MAX(day) as end_date
        FROM transactions
    """).iloc[0]

    total_tpv = stats['total_tpv']
    total_txns = stats['total_txns']
    avg_ticket = total_tpv / total_txns

    # Metrics
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Total TPV", format_currency(total_tpv))
    with col2:
        st.metric("Transactions", format_number(total_txns))

    col3, col4 = st.sidebar.columns(2)
    with col3:
        st.metric("Avg Ticket", format_currency(avg_ticket))
    with col4:
        st.metric("Days", "90")

    st.sidebar.markdown("---")

    # Alerts section
    st.sidebar.markdown("## 🚨 Anomaly Alerts")

    alerts = detector.get_alerts_for_display()

    # Summary counts
    critical = sum(1 for a in alerts if a['severity'] == 'critical')
    warning = sum(1 for a in alerts if a['severity'] == 'warning')
    normal = sum(1 for a in alerts if a['severity'] == 'normal')

    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        st.markdown(f"🔴 **{critical}**")
    with col2:
        st.markdown(f"🟡 **{warning}**")
    with col3:
        st.markdown(f"🟢 **{normal}**")

    st.sidebar.markdown("---")

    # Alert details with better labels
    for alert in alerts[:7]:  # Show top 7
        severity = alert['severity']
        icon = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🟢"
        metric = alert['metric']
        dimension = alert['dimension']
        change = alert['change_pct']
        z_score = alert['z_score']

        # Create clear label
        if dimension == "total" and metric == "tpv":
            label = "💰 TPV Total"
        elif dimension == "total" and metric == "transactions":
            label = "🔢 Transactions"
        else:
            label = f"💳 TPV {dimension.upper()}"

        change_str = f"+{change:.1f}%" if change > 0 else f"{change:.1f}%"

        st.sidebar.markdown(f"""
        <div class="alert-{severity}">
            {icon} <b>{label}</b><br>
            <small>{change_str} (Z={z_score:.2f})</small>
        </div>
        """, unsafe_allow_html=True)


def auto_generate_chart(df: pd.DataFrame):
    """
    Automatically generate appropriate chart based on data structure.
    """
    if df is None or len(df) < 2:
        return None

    cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=['float64', 'int64', 'float', 'int']).columns.tolist()

    if len(numeric_cols) == 0:
        return None

    y_col = numeric_cols[0]

    # Time series: day column
    if 'day' in cols:
        fig = px.line(df, x='day', y=y_col, title=f'{y_col.replace("_", " ").title()} Over Time')
        fig.update_layout(xaxis_title='Date', yaxis_title=y_col.replace("_", " ").title())
        return fig

    # Hourly data
    if 'hour' in cols:
        fig = px.bar(df, x='hour', y=y_col, title=f'{y_col.replace("_", " ").title()} by Hour')
        fig.update_layout(xaxis_title='Hour', yaxis_title=y_col.replace("_", " ").title())
        return fig

    # Categorical: product, entity, payment_method, etc.
    categorical_cols = ['product', 'entity', 'payment_method', 'price_tier', 'anticipation_method']
    for cat_col in categorical_cols:
        if cat_col in cols:
            if len(df) <= 6:
                fig = px.pie(df, values=y_col, names=cat_col, title=f'{y_col.replace("_", " ").title()} by {cat_col.replace("_", " ").title()}')
            else:
                fig = px.bar(df, x=cat_col, y=y_col, title=f'{y_col.replace("_", " ").title()} by {cat_col.replace("_", " ").title()}')
                fig.update_layout(xaxis_title=cat_col.replace("_", " ").title(), yaxis_title=y_col.replace("_", " ").title())
            return fig

    # Generic: first column as x, numeric as y
    if len(cols) >= 2 and len(df) > 1:
        x_col = cols[0]
        fig = px.bar(df, x=x_col, y=y_col, title=f'{y_col.replace("_", " ").title()} by {x_col.replace("_", " ").title()}')
        return fig

    return None


def render_chat(agent: CloudWalkAgent):
    """Render chat interface."""

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Create a container for chat messages
    chat_container = st.container()

    # Chat input at the bottom (always visible)
    prompt = st.chat_input("Ask a question about the data...")

    # Display chat history in the container
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Show SQL if available
                if message.get("sql"):
                    with st.expander("📝 SQL Query"):
                        st.code(message["sql"], language="sql")

                # Show data table if available
                if message.get("data") and len(message["data"]) > 0:
                    df = pd.DataFrame(message["data"])
                    if len(df) <= 20:
                        st.dataframe(df, use_container_width=True)

                    # Auto-generate chart
                    fig = auto_generate_chart(df)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

    # Process new input
    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get agent response
        with st.spinner("Analyzing..."):
            result = agent.ask(prompt)

        # Save assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sql": result.get("sql"),
            "data": result.get("data")
        })

        # Rerun to show updated messages
        st.rerun()


def render_visualizations(db: Database):
    """Render visualization section."""

    st.markdown("### 📈 Quick Visualizations")

    tab1, tab2, tab3 = st.tabs(["Daily TPV", "By Product", "By Entity"])

    with tab1:
        df = db.execute_query("""
            SELECT day, SUM(amount_transacted) as tpv
            FROM transactions
            GROUP BY day
            ORDER BY day
        """)
        fig = px.line(df, x='day', y='tpv', title='Daily TPV Trend')
        fig.update_traces(line_color='#2E86AB')
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='TPV (R$)',
            yaxis_tickformat=',.0f'
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        df = db.execute_query("""
            SELECT product, SUM(amount_transacted) as tpv
            FROM transactions
            GROUP BY product
            ORDER BY tpv DESC
        """)
        fig = px.bar(df, x='product', y='tpv', title='TPV by Product',
                     color='tpv', color_continuous_scale='Viridis')
        fig.update_layout(
            xaxis_title='Product',
            yaxis_title='TPV (R$)',
            yaxis_tickformat=',.0f',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        df = db.execute_query("""
            SELECT
                CASE entity
                    WHEN 'PJ' THEN 'Business (PJ)'
                    WHEN 'PF' THEN 'Individual (PF)'
                END as entity_name,
                SUM(amount_transacted) as tpv
            FROM transactions
            GROUP BY entity
        """)
        fig = px.pie(df, values='tpv', names='entity_name',
                     title='TPV Distribution by Entity',
                     color_discrete_sequence=['#2E86AB', '#A23B72'])
        st.plotly_chart(fig, use_container_width=True)


def main():
    """Main application."""

    # Header
    st.title("🏦 CloudWalk Operations Intelligence")
    st.caption("AI-powered analytics agent for financial transaction data")
    st.divider()

    # Initialize components
    db = init_database()
    agent = init_agent(db)
    detector = init_detector(db)

    # Render sidebar
    render_sidebar(db, detector)

    # Main content tabs
    chat_tab, viz_tab, about_tab = st.tabs(["💬 Chat", "📊 Visualizations", "ℹ️ About"])

    with chat_tab:
        st.markdown("### Ask questions in natural language")
        st.markdown("Examples: *'What was the total TPV last week?'* | *'Which product has the highest revenue?'* | *'Compare PJ vs PF'*")
        st.markdown("")
        render_chat(agent)

    with viz_tab:
        render_visualizations(db)

    with about_tab:
        st.markdown("""
        ### About This Project

        **CloudWalk Operations Intelligence** is an AI-powered analytics agent designed for
        financial transaction data analysis. It demonstrates:

        1. **Natural Language to SQL (NL2SQL)**: Ask questions in plain English and get SQL-powered answers
        2. **Anomaly Detection**: Z-score based monitoring for unusual patterns
        3. **Real-time Visualizations**: Interactive charts for data exploration

        ---

        ### Technical Stack

        | Component | Technology |
        |-----------|------------|
        | LLM | Llama 3.3 70B via Groq |
        | Database | SQLite |
        | Framework | Streamlit |
        | Charts | Plotly |

        ---

        ### Data Dictionary

        | Column | Description |
        |--------|-------------|
        | day | Transaction date |
        | entity | PJ (Business) or PF (Individual) |
        | product | pix, pos, tap, link, bank_slip |
        | amount_transacted | TPV - Total Payment Volume |
        | quantity_transactions | Number of transactions |

        ---

        **Author**: Gabriel Milhardo
        **For**: CloudWalk Data Analyst Challenge
        """)


if __name__ == "__main__":
    main()
