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

# Page setup
st.set_page_config(
    page_title="Construction Industry Market Analysis",
    layout="wide",
    initial_sidebar_state="auto"
)

# Your n8n production webhook URL
N8N_WEBHOOK_URL = "https://8401-62-250-42-200.ngrok-free.app/webhook/794f32f6-fb8b-4d67-a7a4-ae0e2bc07bd6"

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
                    try:
                        # Send POST request to n8n webhook with only the user's message
                        payload = {
                            "message": prompt
                        }
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=300)
                        response.raise_for_status()

                        # Handle the response from n8n (assuming plain text)
                        assistant_response = response.text

                    except requests.exceptions.RequestException as e:
                        assistant_response = f"Error connecting to n8n: {str(e)}"
                        st.write(f"Error: {assistant_response}")

                # Display the response and add it to chat history
                st.write(assistant_response)
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})

# Main content area for the dashboard
# Title & Header
st.title("🏗️ Construction Industry Market Analysis")
st.subheader("🇩🇪 Germany")
st.markdown("**Source:** [Trading Economics - Germany Indicators](https://tradingeconomics.com/germany/indicators)")

st.markdown("---")

# Load SQLite Data from GitHub
@st.cache_data
def load_database():
    url = "https://raw.githubusercontent.com/olivia-pacalau/zehnder-data/main/data/market_data.db"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if the request fails
    db_data = io.BytesIO(response.content)
    return sqlite3.connect(db_data)

try:
    conn = load_database()
    df = pd.read_sql("SELECT datetime, building_permits FROM market_data_quarterly", conn)
    df = df.dropna()
except Exception as e:
    st.error(f"Error loading database: {str(e)}")
    st.stop()

# Prophet requires specific format
df = df.rename(columns={"datetime": "ds", "building_permits": "y"})

# Prophet modeling
model = Prophet()
model.fit(df)

# Future dataframe (next 6 quarters)
future = model.make_future_dataframe(periods=6, freq='Q')
forecast = model.predict(future)

# Plotting
st.markdown("### 📈 Forecast of Building Permits (Prophet Model)")
fig = plot_plotly(model, forecast)
st.plotly_chart(fig, use_container_width=True)
