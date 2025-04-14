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
    }
    .stApp {
        background-color: #f5f5f5;
    }
    details > summary {
        font-size: 1.1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Your n8n production webhook URL
N8N_WEBHOOK_URL = "https://b1e0-62-250-42-200.ngrok-free.app/webhook/f189b9b1-314e-4bbc-a8e4-105912501679"

# Initialize session state to store chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! How can I assist you today?"}]

# Layout: Main content and custom sidebar
main_col, sidebar_col = st.columns([4, 1.3], gap="large")

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

with main_col:
    # Header and subtitle
    st.markdown("""
    <div style='text-align: center;'>
        <h1 style='margin-bottom: 0;'>Construction Market Analytics</h1>
        <h3 style='margin-top: 0;'>🇩🇪 Germany</h3>
        <p style='font-size: 14px'><a href='https://tradingeconomics.com/' target='_blank'>Data Source: TradingEconomics.com</a></p>
    </div>
    """, unsafe_allow_html=True)

    conn = sqlite3.connect("market_data.db")

    # QoQ Cards
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
                        <p style='color: {color}; font-size: 18px; margin: 0; margin-bottom: 8px;'>{sign}{change}%</p>
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
                        <p style='color: #888; font-size: 18px; margin: 0; margin-bottom: 8px;'>N/A</p>
                        <p style='color: #888; font-size: 12px; margin: 0;'>{quarters_compared[display_name]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # Forecast Cards
    st.markdown("### 📈 Building Permits Forecast Based on Residential Property Prices")
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

    # Display section based on sidebar selection
    if selected_section == "Indicators Trends":
        st.subheader("📊 Indicators Trends Over Time")
        col_select1, col_select2 = st.columns([1, 2])
        with col_select1:
            granularity = st.radio("Select data granularity:", ["Quarterly", "Yearly"], horizontal=True)
        table = "market_data_quarterly" if granularity == "Quarterly" else "market_data_yearly"
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
        df['datetime'] = pd.to_datetime(df['datetime'])
        with col_select2:
            kpi_options = [col for col in df.columns if col not in ["datetime", "year", "quarter"]]
            kpi = st.selectbox("Select indicator to plot:", kpi_options)
        fig = px.scatter(df, x="datetime", y=kpi, labels={"datetime": "Date", kpi: kpi.replace('_', ' ').title()}, color_discrete_sequence=["#008080"])
        fig.update_traces(mode='lines+markers')
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        if st.toggle("🔍 Show Raw Data Table", key="scatter_table"):
            st.dataframe(df)

    elif selected_section == "Prophet Forecast":
        st.subheader("📅 Building Permits Forecast (Prophet)")
        df_prophet = pd.read_sql("SELECT datetime, building_permits FROM market_data_monthly WHERE building_permits IS NOT NULL ORDER BY datetime", conn)
        df_prophet = df_prophet.rename(columns={"datetime": "ds", "building_permits": "y"})
        df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])
        m = Prophet()
        m.fit(df_prophet)
        periods = st.slider("Forecast months", 1, 12, 6)
        future = m.make_future_dataframe(periods=periods, freq="M")
        forecast = m.predict(future)
        fig_prophet = plot_plotly(m, forecast)
        fig_prophet.update_layout(hovermode="x unified")
        st.plotly_chart(fig_prophet, use_container_width=True)
        if st.toggle("🔍 Show Forecast Data Table", key="prophet_table"):
            st.dataframe(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']])

    elif selected_section == "YoY Growth":
        st.subheader("📈 Year-over-Year Growth")
        df_yoy = pd.read_sql("SELECT * FROM market_data_yoy", conn)
        df_yoy_melt = df_yoy.melt(id_vars="year", value_vars=["permits_yoy_pct", "prices_yoy_pct", "ratio_yoy_pct", "output_yoy_pct"], var_name="Metric", value_name="YoY Growth (%)")
        df_yoy_melt["Metric"] = df_yoy_melt["Metric"].replace({
            "permits_yoy_pct": "Building Permits",
            "prices_yoy_pct": "Residential Prices",
            "ratio_yoy_pct": "Price-to-Rent Ratio",
            "output_yoy_pct": "Construction Output"
        })
        fig_yoy = px.bar(df_yoy_melt, x="year", y="YoY Growth (%)", color="Metric", barmode="group", text="YoY Growth (%)")
        fig_yoy.update_traces(textposition="outside")
        fig_yoy.update_layout(yaxis_tickformat=".2f")
        st.plotly_chart(fig_yoy, use_container_width=True)
        if st.toggle("🔍 Show Year-over-Year Raw Data", key="yoy_table"):
            st.dataframe(df_yoy)

    elif selected_section == "Moving Average":
        st.subheader("📐 Construction Output – 3-Month Moving Average")
        df_ma = pd.read_sql("SELECT * FROM market_data_m_avg", conn)
        fig_ma = px.line(df_ma, x="date", y=["current_output", "output_3mo_avg"], labels={"value": "Construction Output", "date": "Date"})
        fig_ma.update_layout(legend_title_text="Legend")
        st.plotly_chart(fig_ma, use_container_width=True)
        if st.toggle("🔍 Show Raw Data Table", key="ma_table"):
            st.dataframe(df_ma)

    conn.close()
