import streamlit as st
import requests
import sqlite3
import pandas as pd
import plotly.express as px
from prophet import Prophet
from prophet.plot import plot_plotly

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
    <h1 style='margin-bottom: 0;'>Construction Market Analytics</h1>
    <h3 style='margin-top: 0;'>🇩🇪 Germany</h3>
    <p style='font-size: 14px'><a href='https://tradingeconomics.com/' target='_blank'>Data Source: TradingEconomics.com</a></p>
</div>
""", unsafe_allow_html=True)

# Connect to database
conn = sqlite3.connect("market_data.db")

# Visualization section (QoQ cards)
with st.container(border=True):
    st.subheader("Quarter-over-Quarter Changes")
    # Load quarterly data
    df_quarterly = pd.read_sql("SELECT * FROM market_data_quarterly ORDER BY datetime DESC", conn)
    df_quarterly['datetime'] = pd.to_datetime(df_quarterly['datetime'])

    # Calculate QoQ percentage changes for each feature
    metrics = {
        'Building Permits': 'building_permits',
        'Construction Output': 'construction_output',
        'Price-to-Rent Ratio': 'price_to_rent_ratio',
        'Residential Prices': 'residential_prices'
    }
    qoq_changes = {}
    quarters_compared = {}

    for display_name, col in metrics.items():
        # Filter non-null values for this feature
        df_feature = df_quarterly[['datetime', col]].dropna(subset=[col]).sort_values('datetime', ascending=False)
        
        if len(df_feature) >= 2:
            # Take the two most recent quarters
            latest = df_feature.iloc[0]
            previous = df_feature.iloc[1]
            if previous[col] != 0:  # Avoid division by zero
                change = ((latest[col] - previous[col]) / previous[col]) * 100
                qoq_changes[display_name] = round(change, 2)
                # Get quarter labels (e.g., "2024Q3")
                latest_quarter = latest['datetime'].to_period('Q').strftime('%YQ%q')
                prev_quarter = previous['datetime'].to_period('Q').strftime('%YQ%q')
                quarters_compared[display_name] = f"{latest_quarter} vs {prev_quarter}"
            else:
                qoq_changes[display_name] = None
                quarters_compared[display_name] = "N/A"
        else:
            qoq_changes[display_name] = None
            quarters_compared[display_name] = "N/A"

    # Display QoQ cards
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

# ... (Previous imports and code up to Scatter Plot section remain the same)

# Scatter Plot section
with st.container(border=True):
    # Existing controls for granularity and KPI selection
    col_select1, col_select2 = st.columns([1, 2])

    with col_select1:
        granularity = st.radio("Select data granularity:", ["Quarterly", "Yearly"], horizontal=True)

    # Load appropriate table
    table = "market_data_quarterly" if granularity == "Quarterly" else "market_data_yearly"
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    df['datetime'] = pd.to_datetime(df['datetime'])

    with col_select2:
        # Apply custom CSS for the selectbox background
        st.markdown(
            """
            <style>
            div[data-testid="stSelectbox"] select {
                background-color: #cfcccc;
                border-radius: 5px;
                padding: 5px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        kpi_options = [col for col in df.columns if col not in ["datetime", "year", "quarter"]]
        kpi = st.selectbox("Select indicator to plot:", kpi_options)

    # Scatter plot
    st.subheader(f"{kpi.replace('_', ' ').title()} Over Time ({granularity})")
    fig = px.scatter(df, x="datetime", y=kpi, title=f"{kpi.replace('_', ' ').title()} Over Time",
                     labels={"datetime": "Date", kpi: kpi.replace('_', ' ').title()}, color_discrete_sequence=["#008080"])
    fig.update_traces(
        mode='lines+markers',
        hovertemplate='Date: %{x|%Y-%m-%d}<br>Value: %{y:.2f}<extra></extra>'
    )
    fig.update_layout(
        hovermode="x unified",  # Shows all points at a given x-value in one tooltip
        yaxis=dict(
            tickformat=".2f",  # Ensures y-axis labels are rounded to 2 decimals
            fixedrange=False  # Allows zooming without forcing format
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    # Add expander for raw data with download button
    with st.expander("🔍 View Raw Data Table"):
        st.dataframe(df, use_container_width=True)
        st.download_button(
            label="Download Data",
            data=df.to_csv(index=False),
            file_name=f"scatter_data_{granularity.lower()}.csv",
            mime="text/csv"
        )

# ... (Code up to Prophet Forecast section remains the same)

# Prophet Forecast section
st.markdown("### 📅 Building Permits Forecast (Prophet)")
df_prophet = pd.read_sql("SELECT datetime, building_permits FROM market_data_monthly WHERE building_permits IS NOT NULL ORDER BY datetime", conn)
df_prophet = df_prophet.rename(columns={"datetime": "ds", "building_permits": "y"})
df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])

# Fit Prophet model
m = Prophet()
m.fit(df_prophet)

# Dynamic forecast period with slider
periods = st.slider("Forecast months", 1, 12, 6)
future = m.make_future_dataframe(periods=periods, freq="M")
forecast = m.predict(future)

# Plot forecast
st.subheader(f"{periods}-Month Forecast")
fig_prophet = plot_plotly(m, forecast)
# Customize hover for historical data (scatter points)
fig_prophet.update_traces(
    selector=dict(name="y"),  # Targets historical data points
    hovertemplate='Date: %{x|%Y-%m-%d}<br>Value: %{y:.2f}<extra></extra>'
)
# Customize hover for forecast line
fig_prophet.update_traces(
    selector=dict(name="yhat"),  # Targets forecast line
    hovertemplate='Date: %{x|%Y-%m-%d}<br>Forecast: %{y:.2f}<extra></extra>'
)
# Customize hover for confidence intervals (optional, if visible)
fig_prophet.update_traces(
    selector=dict(name="yhat_upper"),  # Upper bound
    hovertemplate='Date: %{x|%Y-%m-%d}<br>Upper: %{y:.2f}<extra></extra>'
)
fig_prophet.update_traces(
    selector=dict(name="yhat_lower"),  # Lower bound
    hovertemplate='Date: %{x|%Y-%m-%d}<br>Lower: %{y:.2f}<extra></extra>'
)
fig_prophet.update_layout(
    hovermode="x unified",
    yaxis=dict(
        tickformat=".2f",
        fixedrange=False
    )
)
st.plotly_chart(fig_prophet, use_container_width=True)

# Show raw forecast data with download button
with st.expander("🔍 View Forecast Data"):
    forecast_display = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    st.dataframe(forecast_display, use_container_width=True)
    st.download_button(
        label="Download Forecast Data",
        data=forecast_display.to_csv(index=False),
        file_name=f"prophet_forecast_{periods}_months.csv",
        mime="text/csv"
    )

# ... (Rest of the code remains the same)
