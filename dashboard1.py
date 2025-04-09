import streamlit as st
import requests
import sqlite3
import pandas as pd
import plotly.express as px
import tempfile
import os

# Page setup
st.set_page_config(
    page_title="Construction Industry Market Analysis",
    layout="wide",
    initial_sidebar_state="auto"
)

# Custom CSS to center the title and change the chat assistant's background to gray
st.markdown(
    """
    <style>
    /* Center the title */
    .title {
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 0.5em;
    }
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
                    try:
                        # Send POST request to n8n webhook with only the user's message
                        payload = {"message": prompt}
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
# Title (centered)
st.markdown('<div class="title">Germany Construction Market Insights</div>', unsafe_allow_html=True)

# Subtitle
st.subheader("🇩🇪 Germany")

# Source
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

# Function to load the yearly data for the bar chart
@st.cache_data
def load_yearly_data(temp_file_path):
    # Create a new connection in the current thread
    conn = sqlite3.connect(temp_file_path)

    # Load the market_data_yearly table
    df_yearly = pd.read_sql("SELECT year, building_permits FROM market_data_yearly", conn)
    df_yearly = df_yearly.dropna()

    # Close the connection
    conn.close()

    return df_yearly

# Download the database and load the data
try:
    temp_file_path = download_database()
    df_yearly = load_yearly_data(temp_file_path)
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

# Bar Chart: Building Permits per Year
st.markdown("### 📊 Building Permits per Year")
fig = px.bar(
    df_yearly,
    x="year",
    y="building_permits",
    title="Building Permits per Year in Germany",
    labels={"year": "Year", "building_permits": "Number of Building Permits"},
    color="building_permits",
    color_continuous_scale="Blues"
)
fig.update_layout(
    xaxis_title="Year",
    yaxis_title="Number of Building Permits",
    showlegend=False
)
st.plotly_chart(fig, use_container_width=True)
