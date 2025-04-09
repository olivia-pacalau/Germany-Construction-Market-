# import streamlit as st
# import requests
# import sqlite3
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objs as go
# import tempfile
# import os

# # Page setup
# st.set_page_config(
#     page_title="Construction Industry Market Analysis",
#     layout="wide",
#     initial_sidebar_state="auto"
# )

# # Custom CSS to center the title and change the chat assistant's background to gray
# st.markdown(
#     """
#     <style>
#     /* Center the title */
#     .title {
#         text-align: center;
#         font-size: 2.5em;
#         font-weight: bold;
#         margin-bottom: 0.5em;
#     }
#     /* Target the chat message container for the assistant */
#     [data-testid="chatMessage"][data-author-role="assistant"] {
#         background-color: #808080 !important;  /* Gray background */
#         color: white !important;  /* White text for contrast */
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# # Your n8n production webhook URL
# N8N_WEBHOOK_URL = "https://f089-62-250-42-200.ngrok-free.app/webhook/f189b9b1-314e-4bbc-a8e4-105912501679"

# # Initialize session state to store chat history
# if "messages" not in st.session_state:
#     st.session_state.messages = [{"role": "assistant", "content": "Hi! How can I assist you today?"}]

# # Sidebar for the chat
# with st.sidebar:
#     st.header("Chat with Assistant")

#     # Create a container for the chat history with a fixed height and scrollable overflow
#     chat_container = st.container(height=400)  # Adjust height as needed
#     with chat_container:
#         for message in st.session_state.messages:
#             with st.chat_message(message["role"]):
#                 st.write(message["content"])

#     # Chat input at the bottom of the sidebar
#     if prompt := st.chat_input("Type your message here", key="sidebar_chat_input"):
#         # Add user message to chat history
#         st.session_state.messages.append({"role": "user", "content": prompt})
#         with chat_container:
#             with st.chat_message("user"):
#                 st.write(prompt)

#             # Send message to n8n and get response
#             with st.chat_message("assistant"):
#                 with st.spinner("Processing your request... This may take up to 30 seconds."):
#                     try:
#                         # Send POST request to n8n webhook with only the user's message
#                         payload = {"message": prompt}
#                         headers = {"Content-Type": "application/json"}
#                         response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=300)
#                         response.raise_for_status()

#                         # Handle the response from n8n (assuming plain text)
#                         assistant_response = response.text

#                     except requests.exceptions.RequestException as e:
#                         assistant_response = f"Error connecting to n8n: {str(e)}"
#                         st.write(f"Error: {assistant_response}")

#                 # Display the response and add it to chat history
#                 st.write(assistant_response)
#                 st.session_state.messages.append({"role": "assistant", "content": assistant_response})

# # Main content area for the dashboard
# # Title (centered)
# st.markdown('<div class="title">Germany Construction Market Insights</div>', unsafe_allow_html=True)

# # Subtitle
# st.subheader("🇩🇪 Germany")

# # Source
# st.markdown("**Source:** [Trading Economics - Germany Indicators](https://tradingeconomics.com/germany/indicators)")

# st.markdown("---")

# # Function to download the database file and return the temporary file path
# @st.cache_data
# def download_database():
#     url = "https://raw.githubusercontent.com/olivia-pacalau/Germany-Construction-Market-/main/market_data.db"
#     response = requests.get(url)
#     response.raise_for_status()  # Raise an error if the request fails

#     # Create a temporary file to store the database
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
#         temp_file.write(response.content)
#         temp_file_path = temp_file.name

#     return temp_file_path

# # Function to load all data from the database
# @st.cache_data
# def load_all_data(temp_file_path):
#     # Create a new connection in the current thread
#     conn = sqlite3.connect(temp_file_path)

#     # Load the quarterly and yearly tables
#     df_quarterly = pd.read_sql("SELECT * FROM market_data_quarterly", conn)
#     df_quarterly["datetime"] = pd.to_datetime(df_quarterly["datetime"])
#     df_quarterly = df_quarterly.dropna()

#     df_yearly = pd.read_sql("SELECT * FROM market_data_yearly", conn)
#     df_yearly["datetime"] = pd.to_datetime(df_yearly["datetime"])
#     df_yearly = df_yearly.dropna()

#     # Load the growth tables
#     df_qoq = pd.read_sql("SELECT * FROM market_data_qoq", conn)
#     df_yoy = pd.read_sql("SELECT * FROM market_data_yoy", conn)

#     # Close the connection
#     conn.close()

#     return df_quarterly, df_yearly, df_qoq, df_yoy

# # Download the database and load the data
# try:
#     temp_file_path = download_database()
#     df_quarterly, df_yearly, df_qoq, df_yoy = load_all_data(temp_file_path)
#     # Clean up the temporary file after loading the data
#     os.unlink(temp_file_path)
# except Exception as e:
#     st.error(f"Error loading data from database: {str(e)}")
#     # Ensure the temporary file is deleted if it exists
#     if 'temp_file_path' in locals():
#         try:
#             os.unlink(temp_file_path)
#         except FileNotFoundError:
#             pass  # File might have already been deleted
#     st.stop()

# # Slicers (Filters)
# st.markdown("### Filters")
# col1, col2 = st.columns(2)

# with col1:
#     frequency = st.selectbox("Select Frequency", ["Quarterly", "Yearly"], index=0)

# with col2:
#     # Metric selector
#     metrics = ["building_permits", "price_to_rent_ratio", "construction_output", "residential_prices"]
#     selected_metrics = st.multiselect("Select Metrics to Display", metrics, default=metrics)

# # Filter data based on frequency
# if frequency == "Quarterly":
#     df = df_quarterly.copy()
# else:
#     df = df_yearly.copy()

# # 1. Time Series Line Chart
# st.markdown("### 📈 Time Series of Construction Metrics")
# fig = go.Figure()
# for metric in selected_metrics:
#     fig.add_trace(go.Scatter(
#         x=df["datetime"],
#         y=df[metric],
#         mode="lines+markers",
#         name=metric.replace("_", " ").title()
#     ))
# fig.update_layout(
#     title="Construction Metrics Over Time",
#     xaxis_title="Date",
#     yaxis_title="Value",
#     legend_title="Metric",
#     hovermode="x unified"
# )
# st.plotly_chart(fig, use_container_width=True)

# # 2. Correlation Heatmap
# st.markdown("### 🔗 Correlation Heatmap")
# corr = df[metrics].corr()
# fig = px.imshow(
#     corr,
#     text_auto=True,
#     labels=dict(color="Correlation"),
#     color_continuous_scale="RdBu_r",
#     title="Correlation Between Construction Metrics"
# )
# st.plotly_chart(fig, use_container_width=True)

# # 3. Bar Chart: Building Permits per Year
# st.markdown("### 📊 Building Permits per Year")
# fig = px.bar(
#     df_yearly,
#     x="year",
#     y="building_permits",
#     title="Building Permits per Year in Germany",
#     labels={"year": "Year", "building_permits": "Number of Building Permits"},
#     color="building_permits",
#     color_continuous_scale="Blues"
# )
# fig.update_layout(
#     xaxis_title="Year",
#     yaxis_title="Number of Building Permits",
#     showlegend=False
# )
# st.plotly_chart(fig, use_container_width=True)

# # 4. Quarter-over-Quarter Growth Bar Chart
# st.markdown("### 📊 Quarter-over-Quarter Growth")
# qoq_metrics = ["permits_qoq_pct", "prices_qoq_pct", "ratio_qoq_pct", "output_qoq_pct"]
# quarters = df_qoq["quarter"].unique()
# selected_quarter = st.selectbox("Select Quarter for QoQ Growth", quarters)
# df_qoq_selected = df_qoq[df_qoq["quarter"] == selected_quarter]
# qoq_data = pd.DataFrame({
#     "Metric": ["Building Permits", "Residential Prices", "Price to Rent Ratio", "Construction Output"],
#     "QoQ Growth (%)": [
#         df_qoq_selected["permits_qoq_pct"].iloc[0] if not df_qoq_selected.empty else 0,
#         df_qoq_selected["prices_qoq_pct"].iloc[0] if not df_qoq_selected.empty else 0,
#         df_qoq_selected["ratio_qoq_pct"].iloc[0] if not df_qoq_selected.empty else 0,
#         df_qoq_selected["output_qoq_pct"].iloc[0] if not df_qoq_selected.empty else 0
#     ]
# })
# fig = px.bar(
#     qoq_data,
#     x="QoQ Growth (%)",
#     y="Metric",
#     orientation="h",
#     title=f"QoQ Growth for {selected_quarter}",
#     color="QoQ Growth (%)",
#     color_continuous_scale="RdBu_r"
# )
# st.plotly_chart(fig, use_container_width=True)

# # 5. Year-over-Year Growth Bar Chart
# st.markdown("### 📊 Year-over-Year Growth")
# yoy_metrics = ["permits_yoy_pct", "prices_yoy_pct", "ratio_yoy_pct", "output_yoy_pct"]
# years = df_yoy["year"].unique()
# selected_year = st.selectbox("Select Year for YoY Growth", years)
# df_yoy_selected = df_yoy[df_yoy["year"] == selected_year]
# yoy_data = pd.DataFrame({
#     "Metric": ["Building Permits", "Residential Prices", "Price to Rent Ratio", "Construction Output"],
#     "YoY Growth (%)": [
#         df_yoy_selected["permits_yoy_pct"].iloc[0] if not df_yoy_selected.empty else 0,
#         df_yoy_selected["prices_yoy_pct"].iloc[0] if not df_yoy_selected.empty else 0,
#         df_yoy_selected["ratio_yoy_pct"].iloc[0] if not df_yoy_selected.empty else 0,
#         df_yoy_selected["output_yoy_pct"].iloc[0] if not df_yoy_selected.empty else 0
#     ]
# })
# fig = px.bar(
#     yoy_data,
#     x="YoY Growth (%)",
#     y="Metric",
#     orientation="h",
#     title=f"YoY Growth for {selected_year}",
#     color="YoY Growth (%)",
#     color_continuous_scale="RdBu_r"
# )
# st.plotly_chart(fig, use_container_width=True)


import streamlit as st
import requests
import sqlite3
import json
import pandas as pd
import plotly.express as px

# Optional: Prophet forecast
try:
    from prophet import Prophet
    from prophet.plot import plot_plotly
except ImportError:
    Prophet = None

# Your n8n production webhook URL
N8N_WEBHOOK_URL = "https://8401-62-250-42-200.ngrok-free.app/webhook/794f32f6-fb8b-4d67-a7a4-ae0e2bc07bd6"

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
st.title("🏗️ Construction Market Analysis")

# Connect to SQLite
conn = sqlite3.connect("market_data.db")

# --- Bar Chart ---
st.subheader("📊 Building Permits Over the Years")
df_yearly = pd.read_sql("SELECT * FROM market_data_yearly", conn)
fig_bar = px.bar(df_yearly, x="year", y="building_permits", title="Building Permits by Year", labels={"building_permits": "Building Permits"})
st.plotly_chart(fig_bar, use_container_width=True)

# --- Prophet Forecast ---
st.subheader("🔮 Forecast: Building Permits (Prophet)")
if Prophet is not None:
    df_prophet = df_yearly[["datetime", "building_permits"]].dropna().rename(columns={"datetime": "ds", "building_permits": "y"})
    model = Prophet()
    model.fit(df_prophet)
    future = model.make_future_dataframe(periods=8, freq='Q')
    forecast = model.predict(future)
    st.write("Forecast for the next 8 quarters:")
    fig_forecast = plot_plotly(model, forecast)
    st.plotly_chart(fig_forecast, use_container_width=True)
else:
    st.error("Prophet is not installed. Run `pip install prophet` to enable forecasting.")

# --- Preview Table ---
st.subheader("📋 Sample Quarterly Market Data")
df_quarterly = pd.read_sql("SELECT * FROM market_data_quarterly LIMIT 10", conn)
st.dataframe(df_quarterly)

# Close DB connection
conn.close()

