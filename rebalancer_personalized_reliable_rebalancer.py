import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import os
import pytz
from datetime import datetime, timedelta
import pandas_market_calendars as mcal
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

# --- Definition des Depots ---
portfolio = [
    {"Ticker": "NVDA", "Name":"NVIDIA", "Sector":"Technologie & KI"},
    {"Ticker": "MSFT", "Name":"Microsoft", "Sector":"Technologie & KI"},
    {"Ticker": "GOOGL", "Name":"Alphabet", "Sector":"Technologie & KI"},
    {"Ticker": "ASML.AS", "Name":"ASML", "Sector":"Technologie & KI"},
    {"Ticker": "CRWD", "Name":"CrowdStrike", "Sector":"Cybersecurity / Cloud"},
    {"Ticker": "NOW", "Name":"ServiceNow", "Sector":"Cybersecurity / Cloud"},
    {"Ticker": "FSLR", "Name":"First Solar", "Sector":"Erneuerbare Energien & Infra"},
    {"Ticker": "NEE", "Name":"NextEra Energy", "Sector":"Erneuerbare Energien & Infra"},
    {"Ticker": "BEPC", "Name":"Brookfield Renewable", "Sector":"Erneuerbare Energien & Infra"},
    {"Ticker": "TSLA", "Name":"Tesla", "Sector":"Zukunft / Disruption"},
    {"Ticker": "PLTR", "Name":"Palantir", "Sector":"Zukunft / Disruption"},
    {"Ticker": "SMCI", "Name":"Super Micro Computer", "Sector":"Zukunft / Disruption"},
    {"Ticker": "JNJ", "Name":"Johnson & Johnson", "Sector":"Gesundheit / Stabilität"},
    {"Ticker": "NVO", "Name":"Novo Nordisk", "Sector":"Gesundheit / Stabilität"},
    {"Ticker": "AAPL", "Name":"Apple", "Sector":"Konsum & Industrie"},
    {"Ticker": "VOW3.DE", "Name":"Volkswagen", "Sector":"Konsum & Industrie"}
]

SHARES_FILE = "shares.csv"

# --- CSV erstellen, falls nicht vorhanden ---
if not os.path.exists(SHARES_FILE):
    initial_shares = {p["Ticker"]: 0.0 for p in portfolio}
    initial_shares["VOW3.DE"] = 57.213
    df_shares = pd.DataFrame.from_dict(initial_shares, orient="index", columns=["Shares"])
    df_shares.index.name = "Ticker"
    df_shares.to_csv(SHARES_FILE)

# --- Laden der Shares ---
df_shares = pd.read_csv(SHARES_FILE, index_col=0)
df_shares["Shares"] = df_shares["Shares"].astype(float)

if "shares_dict" not in st.session_state:
    st.session_state.shares_dict = df_shares["Shares"].to_dict()

# --- DataFrame für Anzeige ---
df = pd.DataFrame(portfolio)
df["Shares"] = df["Ticker"].map(st.session_state.shares_dict)

# --- Echtzeitkurse abrufen ---
tickers = [p["Ticker"] for p in portfolio]
data = yf.download(tickers, period="1d", interval="1d", progress=False)["Close"].iloc[-1]
df["Price"] = df["Ticker"].map(data.to_dict())
df["Price"].fillna(0, inplace=True)
df["MarketValue"] = (df["Shares"] * df["Price"]).round(2)

# --- Shares editierbar ---
edited = st.data_editor(df[["Ticker","Name","Shares"]], num_rows="dynamic", use_container_width=True)

for idx, row in edited.iterrows():
    st.session_state.shares_dict[row["Ticker"]] = float(row["Shares"])
    df.at[idx,"Shares"] = float(row["Shares"])

# --- Market Value aktualisieren ---
df["MarketValue"] = (df["Shares"] * df["Price"]).round(2)

# --- Gesamtübersicht ---
st.subheader("Depotübersicht")
st.dataframe(df[["Ticker","Name","Sector","Shares","Price","MarketValue"]], use_container_width=True)

# --- Sektoranteile pie chart ---
st.subheader("Sektorverteilung")
sector_group = df.groupby("Sector")["MarketValue"].sum()
fig, ax = plt.subplots()
ax.pie(sector_group, labels=sector_group.index, autopct=lambda p: f'{p:.1f}%' if p>0 else '')
st.pyplot(fig)

# --- Prozentualer Anteil je Aktie im Sektor ---
st.subheader("Prozentanteil jeder Aktie im Sektor")
sector_pct = df.groupby("Sector")["MarketValue"].apply(lambda x: x / x.sum() * 100).reset_index(name="Percent")
sector_pct = sector_pct.merge(df[["Ticker","Sector"]], on="Sector")
st.dataframe(sector_pct[["Ticker","Sector","Percent"]], use_container_width=True)

# --- Persistenz ---
pd.DataFrame.from_dict(st.session_state.shares_dict, orient="index", columns=["Shares"]).to_csv(SHARES_FILE)
