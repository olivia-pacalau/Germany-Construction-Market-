import streamlit as st
import requests
import sqlite3
import pandas as pd
import plotly.express as px
from prophet import Prophet
from prophet.plot import plot_plotly

st.set_page_config(layout="wide")
st.markdown("""
<style>
    body {
        background-color: #f5f5f5;
        margin-top: 10px !important;
    }
    .stApp {
        background-color: #f5f5f5;
    }
    h1 {
        margin-bottom: 0.3em !important;
    }
    h3 {
        margin-top: 0.1em !important;
    }
    .qoq-value {
        font-size: 24px !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Your n8n production webhook URL
N8N_WEBHOOK_URL = "https://b1e0-62-250-42-200.ngrok-free.app/webhook/f189b9b1-314e-4bbc-a8e4-105912501679"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! How can I assist you today?"}]
if "show_sidebar" not in st.session_state:
    st.session_state.show_sidebar = True

# Toggle Button
topcol1, topcol2 = st.columns([5, 1])
with topcol2:
    label = "📂 Hide Sidebar" if st.session_state.show_sidebar else "📂 Show Sidebar"
    if st.button(label):
        st.session_state.show_sidebar = not st.session_state.show_sidebar

# Dynamic layout
top_layout = st.columns([4, 1.3], gap="large") if st.session_state.show_sidebar else [st.container()]
main_col = top_layout[0]
sidebar_col = top_layout[1] if st.session_state.show_sidebar else None

if sidebar_col:
    with sidebar_col:
        st.header("📊 Sections")
        selected_section = st.radio("Jump to:", [
            "Indicators Trends",
            "Prophet Forecast",
            "YoY Growth",
            "Moving Average"
        ])

        st.divider()
        st.header("💬 Chat with Assistant")
        chat_container = st.container(height=300)
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
else:
    selected_section = "Indicators Trends"  # default fallback

with main_col:
    st.markdown("""
    <div style='text-align: center;'>
        <h1 style='margin-bottom: 0.2em;'>Construction Market Analytics</h1>
        <h3 style='margin-top: 0.1em;'>🇩🇪 Germany</h3>
        <p style='font-size: 14px; margin-bottom: 1em;'><a href='https://tradingeconomics.com/' target='_blank'>Data Source: TradingEconomics.com</a></p>
    </div>
    """, unsafe_allow_html=True)

    conn = sqlite3.connect("market_data.db")

    st.subheader("Quarter-over-Quarter Changes")
    df_quarterly = pd.read_sql("SELECT * FROM market_data_quarterly ORDER BY datetime DESC", conn)
    df_quarterly['datetime'] = pd.to_datetime(df_quarterly['datetime'])
    metrics = {
        'Building Permits': 'building_permits',
        'Construction Output': 'construction_output',
        'Price-to-Rent Ratio': 'price_to_rent_ratio',
        'Residential Prices': 'residential_prices'
    }
    qoq_changes = {}
    quarters_compared = {}
    for display_name, col in metrics.items():
        df_feature = df_quarterly[['datetime', col]].dropna(subset=[col]).sort_values('datetime', ascending=False)
        if len(df_feature) >= 2:
            latest = df_feature.iloc[0]
            previous = df_feature.iloc[1]
            if previous[col] != 0:
                change = ((latest[col] - previous[col]) / previous[col]) * 100
                qoq_changes[display_name] = round(change, 2)
                latest_quarter = latest['datetime'].to_period('Q').strftime('%YQ%q')
                prev_quarter = previous['datetime'].to_period('Q').strftime('%YQ%q')
                quarters_compared[display_name] = f"{latest_quarter} vs {prev_quarter}"
            else:
                qoq_changes[display_name] = None
                quarters_compared[display_name] = "N/A"
        else:
            qoq_changes[display_name] = None
            quarters_compared[display_name] = "N/A"
    cols = st.columns(4)
    for idx, (display_name, change) in enumerate(qoq_changes.items()):
        with cols[idx]:
            if change is not None:
                color = "green" if change >= 0 else "red"
                sign = "+" if change >= 0 else ""
                st.markdown(
                    f"""
                    <div style='text-align: center; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>
                        <h4 style='margin: 0; margin-bottom: 10px;'>{display_name}</h4>
                        <p class='qoq-value' style='color: {color}; margin: 0; margin-bottom: 8px;'>{sign}{change}%</p>
                        <p style='color: #888; font-size: 12px; margin: 0;'>{quarters_compared[display_name]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style='text-align: center; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>
                        <h4 style='margin: 0; margin-bottom: 10px;'>{display_name}</h4>
                        <p class='qoq-value' style='color: #888; margin: 0; margin-bottom: 8px;'>N/A</p>
                        <p style='color: #888; font-size: 12px; margin: 0;'>{quarters_compared[display_name]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    st.markdown("<div style='margin-top: 30px'></div>", unsafe_allow_html=True)
    st.markdown("### 📈 Building Permits Forecast Based on Residential Property Prices")

    df_pred = pd.read_sql("SELECT * FROM building_permit_predictions ORDER BY current_quarter DESC LIMIT 1", conn)
    if not df_pred.empty:
        actual = int(df_pred["actual_permits"].values[0])
        predicted = int(df_pred["predicted_permits"].values[0])
        quarter_str = pd.to_datetime(df_pred["current_quarter"].values[0]).to_period("Q").strftime("Q%q %Y")
        cardcol1, cardcol2 = st.columns(2)
        with cardcol1:
            st.markdown(
                f"""
                <div style='padding: 15px; border: 1px solid #ccc; border-radius: 10px; background-color: #fff;'>
                    <h5 style='margin: 0 0 5px 0;'>📌 {quarter_str} – Building Permits</h5>
                    <p style='font-size: 28px; font-weight: bold; margin: 0;'>{actual:,}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        with cardcol2:
            st.markdown(
                f"""
                <div style='padding: 15px; border: 1px solid #ccc; border-radius: 10px; background-color: #fff;'>
                    <h5 style='margin: 0 0 5px 0;'>📌 Next Quarter – Predicted Permits</h5>
                    <p style='font-size: 28px; font-weight: bold; margin: 0;'>{predicted:,}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.warning("No predictions available yet.")

    st.markdown("<div style='margin-top: 30px'></div>", unsafe_allow_html=True)
