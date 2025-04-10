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
st.title("\U0001F3D7️ Construction Market Analysis")
st.markdown("### 🇩🇪 Germany")
st.markdown("[Data Source: TradingEconomics.com](https://tradingeconomics.com/)")

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

# Display KPI cards in columns
col1, col2 = st.columns(2)

with col1:
    delta = f"{change_building:+.2f}%" if change_building is not None else "N/A"
    st.metric("Building Permits – % Change from Last Month", delta, delta_color="normal")

with col2:
    delta = f"{change_output:+.2f}%" if change_output is not None else "N/A"
    st.metric("Construction Output – % Change from Last Month", delta, delta_color="normal")

# Visualization section
with st.container(border=True):
    col_select1, col_select2 = st.columns([1, 2])

    with col_select1:
        granularity = st.radio("Select data granularity:", ["Quarterly", "Yearly"], horizontal=True)

    # Load appropriate table
    table = "market_data_quarterly" if granularity == "Quarterly" else "market_data_yearly"
    df = pd.read_sql(f"SELECT * FROM {table}", conn)

    with col_select2:
        kpi_options = [col for col in df.columns if col not in ["datetime", "year", "quarter"]]
        kpi = st.selectbox("Select KPI to plot:", kpi_options)

    # Scatter plot
    st.subheader(f"{kpi.replace('_', ' ').title()} Over Time ({granularity})")
    fig = px.scatter(df, x="datetime", y=kpi, title=f"{kpi.replace('_', ' ').title()} Over Time", 
                     labels={"datetime": "Date", kpi: kpi.replace('_', ' ').title()}, color_discrete_sequence=["#008080"])
    fig.update_traces(mode='lines+markers')
    st.plotly_chart(fig, use_container_width=True)

conn.close()
