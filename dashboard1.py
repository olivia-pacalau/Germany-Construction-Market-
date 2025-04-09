import streamlit as st
import pandas as pd
from prophet import Prophet
from prophet.plot import plot_plotly
import plotly.graph_objs as go
import sqlite3
import requests
import io
import json
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
import time
import tempfile
import os

# Page setup
st.set_page_config(
    page_title="Construction Industry Market Analysis",
    layout="wide",
    initial_sidebar_state="auto"
)

# Custom CSS to change the chat assistant's background to gray
st.markdown(
    """
    <style>
    /* Target the chat message container for the assistant */
    [data-testid="chatMessage"][data-author-role="assistant"] {
        background-color: #808080 !important;  /* Gray background */
        color: white !important;  /* White text for contrast */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Your n8n production webhook URL
N8N_WEBHOOK_URL = "https://f089-62-250-42-200.ngrok-free.app/webhook/f189b9b1-314e-4bbc-a8e4-105912501679"

# Initialize session state to store chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! How can I assist you today?"}]

# Sidebar for the chat
with st.sidebar:
    st.header("Chat with Assistant")

    # Create a container for the chat history with a fixed height and scrollable overflow
    chat_container = st.container(height=400)  # Adjust height as needed
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    # Chat input at the bottom of the sidebar
    if prompt := st.chat_input("Type your message here", key="sidebar_chat_input"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.write(prompt)

            # Send message to n8n and get response
            with st.chat_message("assistant"):
                with st.spinner("Processing your request... This may take up to 30 seconds."):
                    assistant_response = None
                    for attempt in range(3):  # Retry up to 3 times
                        try:
                            # Send POST request to n8n webhook with only the user's message
                            payload = {"message": prompt}
                            headers = {"Content-Type": "application/json"}
                            response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=300)
                            response.raise_for_status()
                            assistant_response = response.text
                            break
                        except requests.exceptions.RequestException as e:
                            if attempt == 2:  # Last attempt
                                assistant_response = f"Error connecting to n8n: {str(e)}"
                                st.write(f"Error: {assistant_response}")
                            else:
                                st.write("Retrying...")
                                time.sleep(2)  # Wait 2 seconds before retrying

                # Display the response and add it to chat history
                if assistant_response:
                    st.write(assistant_response)
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response})

# Main content area for the dashboard
# Title & Header
st.title("🏗️ Construction Industry Market Analysis")
st.subheader("🇩🇪 Germany")
st.markdown("**Source:** [Trading Economics - Germany Indicators](https://tradingeconomics.com/germany/indicators)")

st.markdown("---")

# Function to download the database file and return the temporary file path
@st.cache_data
def download_database():
    url = "https://raw.githubusercontent.com/olivia-pacalau/Germany-Construction-Market-/main/market_data.db"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if the request fails

    # Create a temporary file to store the database
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
        temp_file.write(response.content)
        temp_file_path = temp_file.name

    return temp_file_path

# Function to load all data from the database into DataFrames
@st.cache_data
def load_all_data(temp_file_path):
    # Create a new connection in the current thread
    conn = sqlite3.connect(temp_file_path)

    # Load all relevant tables
    df_quarterly = pd.read_sql("SELECT * FROM market_data_quarterly", conn)
    df_quarterly["datetime"] = pd.to_datetime(df_quarterly["datetime"])
    df_quarterly = df_quarterly.dropna()

    df_yearly = pd.read_sql("SELECT * FROM market_data_yearly", conn)
    df_yearly["datetime"] = pd.to_datetime(df_yearly["datetime"])
    df_yearly = df_yearly.dropna()

    # Growth tables
    df_qoq = pd.read_sql("SELECT quarter, current_permits, previous_permits, permits_qoq_pct, current_prices, previous_prices, prices_qoq_pct, current_ratio, previous_ratio, ratio_qoq_pct, current_output, previous_output, output_qoq_pct FROM market_data_quarterly ORDER BY datetime", conn)
    df_yoy = pd.read_sql("WITH yearly AS (SELECT year, building_permits, residential_prices, price_to_rent_ratio, construction_output FROM market_data_yearly), yoy AS (SELECT curr.year, ROUND(curr.building_permits, 2) AS current_permits, ROUND(prev.building_permits, 2) AS previous_permits, ROUND((curr.building_permits - prev.building_permits) * 100.0 / prev.building_permits, 2) AS permits_yoy_pct, ROUND(curr.residential_prices, 2) AS current_prices, ROUND(prev.residential_prices, 2) AS previous_prices, ROUND((curr.residential_prices - prev.residential_prices) * 100.0 / prev.residential_prices, 2) AS prices_yoy_pct, ROUND(curr.price_to_rent_ratio, 2) AS current_ratio, ROUND(prev.price_to_rent_ratio, 2) AS previous_ratio, ROUND((curr.price_to_rent_ratio - prev.price_to_rent_ratio) * 100.0 / prev.price_to_rent_ratio, 2) AS ratio_yoy_pct, ROUND(curr.construction_output, 2) AS current_output, ROUND(prev.construction_output, 2) AS previous_output, ROUND((curr.construction_output - prev.construction_output) * 100.0 / prev.construction_output, 2) AS output_yoy_pct FROM yearly curr JOIN yearly prev ON curr.year = prev.year + 1) SELECT * FROM yoy ORDER BY year", conn)

    # Close the connection
    conn.close()

    return df_quarterly, df_yearly, df_qoq, df_yoy

# Download the database and load the data
try:
    temp_file_path = download_database()
    df_quarterly, df_yearly, df_qoq, df_yoy = load_all_data(temp_file_path)
    # Clean up the temporary file
    os.unlink(temp_file_path)
except Exception as e:
    st.error(f"Error loading data from database: {str(e)}")
    if 'temp_file_path' in locals():
        try:
            os.unlink(temp_file_path)
        except FileNotFoundError:
            pass  # File might have already been deleted
    st.stop()

# Slicers (Filters)
st.markdown("### Filters")
col1, col2, col3 = st.columns(3)

with col1:
    frequency = st.selectbox("Select Frequency", ["Quarterly", "Yearly"], index=0)

with col2:
    # Date range slider
    min_date = df_quarterly["datetime"].min()
    max_date = df_quarterly["datetime"].max()
    date_range = st.slider(
        "Select Date Range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )

with col3:
    # Metric selector
    metrics = ["building_permits", "price_to_rent_ratio", "construction_output", "residential_prices"]
    selected_metrics = st.multiselect("Select Metrics to Display", metrics, default=metrics)

# Filter data based on frequency and date range
if frequency == "Quarterly":
    df = df_quarterly.copy()
else:
    df = df_yearly.copy()

df = df[(df["datetime"] >= date_range[0]) & (df["datetime"] <= date_range[1])]

# Time Series Line Chart
st.markdown("### 📈 Time Series of Construction Metrics")
fig = go.Figure()
for metric in selected_metrics:
    fig.add_trace(go.Scatter(
        x=df["datetime"],
        y=df[metric],
        mode="lines+markers",
        name=metric.replace("_", " ").title()
    ))
fig.update_layout(
    title="Construction Metrics Over Time",
    xaxis_title="Date",
    yaxis_title="Value",
    legend_title="Metric",
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# Prophet Forecast for Building Permits
st.markdown("### 📈 Forecast of Building Permits (Prophet Model)")
df_prophet = df[["datetime", "building_permits"]].rename(columns={"datetime": "ds", "building_permits": "y"})
model = Prophet()
model.fit(df_prophet)
future = model.make_future_dataframe(periods=6, freq='Q')
forecast = model.predict(future)
fig = plot_plotly(model, forecast)
st.plotly_chart(fig, use_container_width=True)

# Correlation Heatmap
st.markdown("### 🔗 Correlation Heatmap")
corr = df[metrics].corr()
fig = px.imshow(
    corr,
    text_auto=True,
    labels=dict(color="Correlation"),
    color_continuous_scale="RdBu_r",
    title="Correlation Between Construction Metrics"
)
st.plotly_chart(fig, use_container_width=True)

# Quarter-over-Quarter Growth Bar Chart
st.markdown("### 📊 Quarter-over-Quarter Growth")
qoq_metrics = ["permits_qoq_pct", "prices_qoq_pct", "ratio_qoq_pct", "output_qoq_pct"]
quarters = df_qoq["quarter"].unique()
selected_quarter = st.selectbox("Select Quarter for QoQ Growth", quarters)
df_qoq_selected = df_qoq[df_qoq["quarter"] == selected_quarter]
qoq_data = pd.DataFrame({
    "Metric": ["Building Permits", "Residential Prices", "Price to Rent Ratio", "Construction Output"],
    "QoQ Growth (%)": [
        df_qoq_selected["permits_qoq_pct"].iloc[0] if not df_qoq_selected.empty else 0,
        df_qoq_selected["prices_qoq_pct"].iloc[0] if not df_qoq_selected.empty else 0,
        df_qoq_selected["ratio_qoq_pct"].iloc[0] if not df_qoq_selected.empty else 0,
        df_qoq_selected["output_qoq_pct"].iloc[0] if not df_qoq_selected.empty else 0
    ]
})
fig = px.bar(
    qoq_data,
    x="QoQ Growth (%)",
    y="Metric",
    orientation="h",
    title=f"QoQ Growth for {selected_quarter}",
    color="QoQ Growth (%)",
    color_continuous_scale="RdBu_r"
)
st.plotly_chart(fig, use_container_width=True)

# Year-over-Year Growth Bar Chart
st.markdown("### 📊 Year-over-Year Growth")
yoy_metrics = ["permits_yoy_pct", "prices_yoy_pct", "ratio_yoy_pct", "output_yoy_pct"]
years = df_yoy["year"].unique()
selected_year = st.selectbox("Select Year for YoY Growth", years)
df_yoy_selected = df_yoy[df_yoy["year"] == selected_year]
yoy_data = pd.DataFrame({
    "Metric": ["Building Permits", "Residential Prices", "Price to Rent Ratio", "Construction Output"],
    "YoY Growth (%)": [
        df_yoy_selected["permits_yoy_pct"].iloc[0] if not df_yoy_selected.empty else 0,
        df_yoy_selected["prices_yoy_pct"].iloc[0] if not df_yoy_selected.empty else 0,
        df_yoy_selected["ratio_yoy_pct"].iloc[0] if not df_yoy_selected.empty else 0,
        df_yoy_selected["output_yoy_pct"].iloc[0] if not df_yoy_selected.empty else 0
    ]
})
fig = px.bar(
    yoy_data,
    x="YoY Growth (%)",
    y="Metric",
    orientation="h",
    title=f"YoY Growth for {selected_year}",
    color="YoY Growth (%)",
    color_continuous_scale="RdBu_r"
)
st.plotly_chart(fig, use_container_width=True)

# Scatter Plot (Building Permits vs. Residential Prices)
st.markdown("### 🔍 Scatter Plot: Building Permits vs. Residential Prices")
fig = px.scatter(
    df,
    x="building_permits",
    y="residential_prices",
    color="datetime",
    size="construction_output",
    hover_data=["quarter" if frequency == "Quarterly" else "year"],
    title="Building Permits vs. Residential Prices (Size by Construction Output)"
)
st.plotly_chart(fig, use_container_width=True)
