import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# Initial settings
st.set_page_config(layout="wide")
conn = sqlite3.connect("market_data.db")

# --- 1. TITLE & INTRO ---
st.markdown("<h1 style='text-align: center;'>🏗️ German Construction Market Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center;'>🇩🇪 For Zehnder Group | [Data Source](https://tradingeconomics.com/)</h4>", unsafe_allow_html=True)

st.markdown("")

# --- 2. HIGH LEVEL INSIGHT ---
st.subheader("📊 Market Summary")
with st.container(border=True):
    st.write("Based on the latest data, the construction market appears to be **cooling down slightly**, with fewer permits issued compared to last quarter, and rising residential prices. Forecasts suggest a moderate decline next quarter.")

# --- 3. KPI CARDS WITH TRENDS (QoQ or YoY only) ---
df_qoq = pd.read_sql("SELECT * FROM market_data_qoq ORDER BY datetime DESC LIMIT 1", conn)
change_building = df_qoq["permits_qoq_pct"].values[0]
change_output = df_qoq["output_qoq_pct"].values[0]

col1, col2 = st.columns(2)
with col1:
    st.metric("🏠 Building Permits (QoQ)", f"{change_building:+.2f}%", delta_color="inverse")
with col2:
    st.metric("⚙️ Construction Output (QoQ)", f"{change_output:+.2f}%", delta_color="inverse")

st.markdown("---")

# --- 4. FORECAST SECTION ---
st.subheader("🔮 Building Permits Forecast")

df_pred = pd.read_sql("SELECT * FROM building_permit_predictions ORDER BY current_quarter DESC LIMIT 1", conn)
actual = int(df_pred["actual_permits"].values[0])
predicted = int(df_pred["predicted_permits"].values[0])

colf1, colf2 = st.columns(2)
with colf1:
    st.metric("This Quarter's Permits", f"{actual:,}")
with colf2:
    st.metric("Predicted Next Quarter", f"{predicted:,}", delta=f"{predicted - actual:+,}")

st.markdown("---")

# --- 5. MAIN KPI EXPLORER (IN BORDER) ---
with st.container(border=True):
    st.subheader("📈 KPI Explorer")
    
    colg1, colg2 = st.columns([1, 2])
    with colg1:
        granularity = st.radio("Granularity", ["Quarterly", "Yearly"], horizontal=True)
    with colg2:
        table = "market_data_quarterly" if granularity == "Quarterly" else "market_data_yearly"
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
        kpis = [c for c in df.columns if c not in ['datetime', 'quarter', 'year']]
        kpi = st.selectbox("Select KPI", kpis)

    fig = px.line(df, x="datetime", y=kpi, title=kpi.replace("_", " ").title())
    st.plotly_chart(fig, use_container_width=True)

# --- 6. MOVING AVERAGE SECTION ---
st.subheader("📊 Monthly Moving Average – Construction Output")

df_avg = pd.read_sql("SELECT * FROM market_data_m_avg", conn)
fig_avg = px.line(df_avg, x="date", y=["current_output", "output_3mo_avg"], 
                  labels={"value": "Construction Output"}, 
                  title="Construction Output vs 3-Month Moving Average")
st.plotly_chart(fig_avg, use_container_width=True)

# --- 7. OPTIONAL RAW TABLE ---
with st.expander("📋 View Raw Quarterly Market Data"):
    df_view = pd.read_sql("SELECT * FROM market_data_quarterly", conn)
    df_view['quarter_label'] = pd.to_datetime(df_view['datetime']).dt.to_period('Q').astype(str)
    df_display = df_view[["quarter_label", "building_permits", "construction_output", "residential_prices", "price_to_rent_ratio"]]
    st.dataframe(df_display, use_container_width=True)

conn.close()
