import streamlit as st
import pandas as pd
from prophet import Prophet
from prophet.plot import plot_plotly
import plotly.graph_objs as go
import sqlite3

# Page setup
st.set_page_config(
    page_title="Construction Industry Market Analysis",
    layout="wide",
    initial_sidebar_state="auto"
)

# Title & Header
st.title("🏗️ Construction Industry Market Analysis")
st.subheader("🇩🇪 Germany")
st.markdown("**Source:** [Trading Economics - Germany Indicators](https://tradingeconomics.com/germany/indicators)")

st.markdown("---")

# Load SQLite Data
conn = sqlite3.connect("market_data.db")
df = pd.read_sql("SELECT datetime, building_permits FROM market_data_quarterly", conn)
df = df.dropna()

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
