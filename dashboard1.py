# imports
import pandas as pd
import os
import sqlite3
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
from functools import reduce

# preprocessing
data_files = {
    "building_permits": "/Users/olivia.pacalau/Desktop/ZehnderAssignment/GERMANYBUIPER.csv",
    "price_to_rent": "/Users/olivia.pacalau/Desktop/ZehnderAssignment/BDPRR.csv",
    "construction_output": "/Users/olivia.pacalau/Desktop/ZehnderAssignment/GermanyConOut.csv",
    "residential_prices": "/Users/olivia.pacalau/Desktop/ZehnderAssignment/BDRPP.csv"
}

def load_and_clean_data(file_path):
    df = pd.read_csv(file_path)
    if df.columns[0] == df.iloc[0, 0]:
        df.columns = df.iloc[0]
        df = df.drop(index=0)
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
    for col in ['datetime', 'lastupdate']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

# Load all data
data = {name: load_and_clean_data(path) for name, path in data_files.items()}

# Create SQLite database
conn = sqlite3.connect("market_data.db")

# Monthly Table
bp = data["building_permits"][["datetime", "value"]].rename(columns={"value": "building_permits"})
co = data["construction_output"]["datetime", "value"].rename(columns={"value": "construction_output"})

unified_monthly = pd.merge(bp, co, on="datetime", how="outer")
unified_monthly = unified_monthly.sort_values("datetime").reset_index(drop=True)
unified_monthly['quarter'] = unified_monthly['datetime'].dt.to_period('Q').astype(str)
unified_monthly.to_sql("market_data_monthly", conn, index=False, if_exists="replace")

# Quarterly Unified Table
monthly_data = ['building_permits', 'construction_output']
data_quarterly = {}

for name, df in data.items():
    if name in monthly_data:
        df = df.set_index('datetime')
        df_num = df.select_dtypes(include='number').resample('Q').mean().round(2)
        df_meta = df.select_dtypes(exclude='number').resample('Q').last()
        df_q = pd.concat([df_num, df_meta], axis=1).reset_index()
        df_q['quarter'] = df_q['datetime'].dt.to_period('Q').astype(str)
        data_quarterly[name] = df_q
    else:
        df_q = df.copy()
        df_q['quarter'] = df_q['datetime'].dt.to_period('Q').astype(str)
        data_quarterly[name] = df_q

bp = data_quarterly["building_permits"][["datetime", "value"]].rename(columns={"value": "building_permits"})
pr = data_quarterly["price_to_rent"][["datetime", "value"]].rename(columns={"value": "price_to_rent_ratio"})
co = data_quarterly["construction_output"]["datetime", "value"].rename(columns={"value": "construction_output"})
rp = data_quarterly["residential_prices"]["datetime", "value"].rename(columns={"value": "residential_prices"})

unified_quarterly = reduce(lambda l, r: pd.merge(l, r, on="datetime", how="outer"), [bp, pr, co, rp])
unified_quarterly = unified_quarterly.sort_values("datetime").reset_index(drop=True)
unified_quarterly['quarter'] = unified_quarterly['datetime'].dt.to_period('Q').astype(str)
unified_quarterly.to_sql("market_data_quarterly", conn, index=False, if_exists="replace")

# Yearly Unified Table
data_yearly = {}
for name, df in data_quarterly.items():
    df = df.set_index('datetime')
    df_num = df.select_dtypes(include='number').resample('Y').mean().round(2)
    df_meta = df.select_dtypes(exclude='number').resample('Y').last()
    df_y = pd.concat([df_num, df_meta], axis=1).reset_index()
    df_y['year'] = df_y['datetime'].dt.year
    data_yearly[name] = df_y

bp_y = data_yearly["building_permits"][["datetime", "value"]].rename(columns={"value": "building_permits"})
pr_y = data_yearly["price_to_rent"][["datetime", "value"]].rename(columns={"value": "price_to_rent_ratio"})
co_y = data_yearly["construction_output"]["datetime", "value"].rename(columns={"value": "construction_output"})
rp_y = data_yearly["residential_prices"]["datetime", "value"].rename(columns={"value": "residential_prices"})

unified_yearly = reduce(lambda l, r: pd.merge(l, r, on="datetime", how="outer"), [bp_y, pr_y, co_y, rp_y])
unified_yearly = unified_yearly.sort_values("datetime").reset_index(drop=True)
unified_yearly['year'] = unified_yearly['datetime'].dt.year
unified_yearly.to_sql("market_data_yearly", conn, index=False, if_exists="replace")

# Linear Regression + Predictions
df_lr = unified_quarterly.dropna().copy()
df_lr['target'] = df_lr['building_permits'].shift(-1)
df_lr = df_lr.dropna()

X = df_lr[['residential_prices']]
y = df_lr['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
lr = LinearRegression().fit(X_train, y_train)

latest = unified_quarterly.dropna().iloc[-1]
latest_date = latest['datetime']
latest_price = latest['residential_prices']
predicted_permits = int(lr.predict([[latest_price]])[0])
actual_permits = int(latest['building_permits'])

predictions_df = pd.DataFrame([{
    "current_quarter": latest_date,
    "residential_price": latest_price,
    "predicted_permits": predicted_permits,
    "actual_permits": actual_permits
}])

predictions_df.to_sql("building_permit_predictions", conn, index=False, if_exists="replace")

print("🎯 Zehnder-ready database generated with insights and forecasts.")
conn.close()
