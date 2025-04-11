import streamlit as st
import requests
import sqlite3
import pandas as pd
import plotly.express as px

# Must be the first Streamlit command
st.set_page_config(layout="wide")
st.markdown("""
<style>
    body {
        background-color: #f5f5f5;
    }
    .stApp {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)

# Your n8n production webhook URL
N8N_WEBHOOK_URL = "https://f089-62-250-42-200.ngrok-free.app/webhook/f189b9b1-314e-4bbc-a8e4-105912501679"

# Initialize session state to store chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! How can I assist you today?"}]

# Sidebar for the chat
with st.sidebar:
    st.header("Chat with Assistant")

    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    if prompt := st.chat_input("Type your message here", key="sidebar_chat_input"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Processing your request... This may take up to 30 seconds."):
                    try:
                        payload = {"message": prompt}
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=300)
                        response.raise_for_status()
                        assistant_response = response.text
                    except requests.exceptions.RequestException as e:
                        assistant_response = f"Error connecting to n8n: {str(e)}"
                        st.write(f"Error: {assistant_response}")

                st.write(assistant_response)
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})


# ----------------- MAIN CONTENT -----------------
st.markdown("""
<div style='text-align: center;'>
    <h1 style='margin-bottom: 0;'>🏗️ Construction Market Analysis</h1>
    <h3 style='margin-top: 0;'>🇩🇪 Germany</h3>
    <p style='font-size: 16px'><a href='https://tradingeconomics.com/' target='_blank'>Data Source: TradingEconomics.com</a></p>
</div>
""", unsafe_allow_html=True)

# Connect to database
conn = sqlite3.connect("market_data.db")

# Load latest two months of data for percent change cards
df_monthly = pd.read_sql("SELECT * FROM market_data_monthly ORDER BY datetime DESC LIMIT 2", conn)

# Calculate percent changes
df_quarter = pd.read_sql("SELECT * FROM market_data_quarterly ORDER BY datetime DESC LIMIT 2", conn)

# Calculate percentage change for each KPI
def calc_qoq_change(col):
    if len(df_quarter) < 2 or pd.isna(df_quarter[col].iloc[1]) or pd.isna(df_quarter[col].iloc[0]):
        return None
    return round(((df_quarter[col].iloc[0] - df_quarter[col].iloc[1]) / df_quarter[col].iloc[1]) * 100, 2)

change_building_qoq = calc_qoq_change("building_permits")
change_output_qoq = calc_qoq_change("construction_output")
change_price_qoq = calc_qoq_change("residential_prices")
change_ratio_qoq = calc_qoq_change("price_to_rent_ratio")

# Display 4 Streamlit metrics (no custom borders)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Building Permits (QoQ)", value=f"{change_building_qoq:+.2f}%" if change_building_qoq is not None else "N/A")

with col2:
    st.metric(label="Construction Output (QoQ)", value=f"{change_output_qoq:+.2f}%" if change_output_qoq is not None else "N/A")

with col3:
    st.metric(label="Residential Prices (QoQ)", value=f"{change_price_qoq:+.2f}%" if change_price_qoq is not None else "N/A")

with col4:
    st.metric(label="Price-to-Rent Ratio (QoQ)", value=f"{change_ratio_qoq:+.2f}%" if change_ratio_qoq is not None else "N/A")


# Visualization section
with st.container(border=True):
    col_select1, col_select2 = st.columns([1, 2])

    with col_select1:
        granularity = st.radio("Select data granularity:", ["Quarterly", "Yearly"], horizontal=True)

    # Load appropriate table
    table = "market_data_quarterly" if granularity == "Quarterly" else "market_data_yearly"
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    df['datetime'] = pd.to_datetime(df['datetime'])

    with col_select2:
        kpi_options = [col for col in df.columns if col not in ["datetime", "year", "quarter"]]
        kpi = st.selectbox("Select KPI to plot:", kpi_options)

    st.subheader(f"{kpi.replace('_', ' ').title()} Over Time ({granularity})")
    fig = px.scatter(df, x="datetime", y=kpi, title=f"{kpi.replace('_', ' ').title()} Over Time", 
                     labels={"datetime": "Date", kpi: kpi.replace('_', ' ').title()}, color_discrete_sequence=["#008080"])
    fig.update_traces(mode='lines+markers')
    st.plotly_chart(fig, use_container_width=True)

# --- Building Permits Forecast Section ---
st.markdown("### 📈 Building Permits Forecast")

# Load prediction from database
conn = sqlite3.connect("market_data.db")
df_pred = pd.read_sql("SELECT * FROM building_permit_predictions ORDER BY current_quarter DESC LIMIT 1", conn)

if not df_pred.empty:
    actual = int(df_pred["actual_permits"].values[0])
    predicted = int(df_pred["predicted_permits"].values[0])
    quarter_str = pd.to_datetime(df_pred["current_quarter"].values[0]).to_period("Q").strftime("Q%q %Y")

    colf1, colf2 = st.columns(2)
    with colf1:
        st.metric(label=f"📌 {quarter_str} – Building Permits", value=f"{actual:,}")
    with colf2:
        st.metric(label=f"📌 Next Quarter – Predicted Permits", value=f"{predicted:,}")
else:
    st.warning("No predictions available yet.")

# Prophet Forecast section
if Prophet:
    df_prophet = pd.read_sql("SELECT datetime, building_permits FROM market_data_monthly WHERE building_permits IS NOT NULL ORDER BY datetime", conn)
    df_prophet = df_prophet.rename(columns={"datetime": "ds", "building_permits": "y"})

    m = Prophet()
    m.fit(df_prophet)
    future = m.make_future_dataframe(periods=3, freq="M")
    forecast = m.predict(future)

    fig_prophet = plot_plotly(m, forecast)
    st.plotly_chart(fig_prophet, use_container_width=True)
else:
    st.warning("Prophet library not installed. Forecasting feature unavailable.")

# SQL Query Viewer Section
st.markdown("---")
st.header("🧠 SQL Growth Queries")
with st.expander("📄 Show Year-over-Year Growth SQL Query"):
    query_yoy = """
    WITH yearly AS (
        SELECT
            CAST(STRFTIME('%Y', datetime) AS INTEGER) AS year,
            building_permits,
            residential_prices,
            price_to_rent_ratio,
            construction_output
        FROM market_data_yearly
    ),
    yoy AS (
        SELECT
            curr.year,
            ROUND(curr.building_permits, 2) AS current_permits,
            ROUND(prev.building_permits, 2) AS previous_permits,
            ROUND((curr.building_permits - prev.building_permits) * 100.0 / prev.building_permits, 2) AS permits_yoy_pct
        FROM yearly curr
        JOIN yearly prev ON curr.year = prev.year + 1
    )
    SELECT * FROM yoy
    ORDER BY year;
    """
    st.code(query_yoy, language="sql")

# Table View of Market Data Quarterly
st.markdown("---")
st.header("📋 Quarterly Market Data Table")
df_quarterly = pd.read_sql("SELECT * FROM market_data_quarterly ORDER BY datetime DESC", conn)
df_quarterly['datetime'] = pd.to_datetime(df_quarterly['datetime'])
df_quarterly['quarter_label'] = df_quarterly['datetime'].apply(lambda d: f"{d.year} Q{(d.month-1)//3 + 1}")
df_quarterly_display = df_quarterly[['quarter_label', 'building_permits', 'construction_output', 'price_to_rent_ratio', 'residential_prices']]
st.dataframe(df_quarterly_display, use_container_width=True)

conn.close()

# Load YoY data
with sqlite3.connect("market_data.db") as conn:
    df_yoy = pd.read_sql("SELECT * FROM market_data_yoy", conn)

# Melt for visualization
df_yoy_melt = df_yoy.melt(id_vars="year", 
                          value_vars=["permits_yoy_pct", "prices_yoy_pct", "ratio_yoy_pct", "output_yoy_pct"],
                          var_name="Metric", value_name="YoY Growth (%)")

# Clean names
df_yoy_melt["Metric"] = df_yoy_melt["Metric"].replace({
    "permits_yoy_pct": "Building Permits",
    "prices_yoy_pct": "Residential Prices",
    "ratio_yoy_pct": "Price-to-Rent Ratio",
    "output_yoy_pct": "Construction Output"
})

# Bar chart
st.markdown("### 📊 Year-over-Year Growth")
fig_yoy = px.bar(df_yoy_melt, x="year", y="YoY Growth (%)", color="Metric", 
                 barmode="group", text="YoY Growth (%)",
                 color_discrete_sequence=px.colors.qualitative.Set2)

fig_yoy.update_traces(textposition="outside")
fig_yoy.update_layout(yaxis_tickformat=".2f", xaxis_title="Year", yaxis_title="% Change")
st.plotly_chart(fig_yoy, use_container_width=True)

# Optional: Display table
with st.expander("🔍 View Raw Data Table"):
    st.dataframe(df_yoy, use_container_width=True)

# Load moving average data
with sqlite3.connect("market_data.db") as conn:
    df_ma = pd.read_sql("SELECT * FROM market_data_m_avg", conn)

st.markdown("### 🧮 Construction Output – 3-Month Moving Average")
fig_ma = px.line(df_ma, x="date", y=["current_output", "output_3mo_avg"],
                 labels={"value": "Construction Output", "date": "Date"},
                 title="Construction Output vs 3-Month Moving Average",
                 color_discrete_map={"current_output": "#1f77b4", "output_3mo_avg": "#ff7f0e"})

fig_ma.update_layout(legend_title_text="Legend")
st.plotly_chart(fig_ma, use_container_width=True)
