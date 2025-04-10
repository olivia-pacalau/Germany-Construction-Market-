import streamlit as st
import requests
import sqlite3
import pandas as pd
import plotly.express as px

# Must be the first Streamlit command
st.set_page_config(layout="wide")

# Optional: Prophet forecast
try:
    from prophet import Prophet
    from prophet.plot import plot_plotly
except ImportError:
    Prophet = None

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
def calc_change(col):
    if len(df_monthly) < 2 or pd.isna(df_monthly[col].iloc[1]) or pd.isna(df_monthly[col].iloc[0]):
        return None
    return round(((df_monthly[col].iloc[0] - df_monthly[col].iloc[1]) / df_monthly[col].iloc[1]) * 100, 2)

change_building = calc_change("building_permits")
change_output = calc_change("construction_output")

# KPI cards
st.markdown("""
<div style='display: flex; justify-content: space-around; margin-bottom: 20px;'>
    <div style='border: 1px solid #ccc; border-radius: 8px; padding: 10px; width: 22%; text-align: center;'>
        <h5 style='margin-bottom: 6px;'>Building Permits – % Change from Last Month</h5>
        <p style='color: {color1}; font-size: 20px;'><strong>{change_building:+.2f}%</strong></p>
    </div>
    <div style='border: 1px solid #ccc; border-radius: 8px; padding: 10px; width: 22%; text-align: center;'>
        <h5 style='margin-bottom: 6px;'>Construction Output – % Change from Last Month</h5>
        <p style='color: {color2}; font-size: 20px;'><strong>{change_output:+.2f}%</strong></p>
    </div>
</div>
""".format(
    change_building=change_building if change_building is not None else 0.0,
    change_output=change_output if change_output is not None else 0.0,
    color1="green" if change_building and change_building >= 0 else "red",
    color2="green" if change_output and change_output >= 0 else "red"
), unsafe_allow_html=True)

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

# Forecast Section
st.markdown("---")
st.subheader("📈 Building Permits Forecast")

# Display forecast cards
df_quarter = pd.read_sql("SELECT * FROM market_data_quarterly WHERE building_permits IS NOT NULL AND residential_prices IS NOT NULL ORDER BY datetime DESC LIMIT 1", conn)

actual_permits = int(df_quarter['building_permits'].values[0])
res_price = df_quarter['residential_prices'].values[0]
predicted_permits = int(0.5 * float(res_price) + 5000) if pd.notna(res_price) else 0

colf1, colf2 = st.columns(2)
with colf1:
    st.metric("This Quarter's Building Permits", f"{actual_permits:,}")
with colf2:
    st.metric("Next Quarter Forecast (based on residential prices)", f"{predicted_permits:,}")

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
