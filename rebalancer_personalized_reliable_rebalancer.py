import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
from pytz import timezone
import os
import pandas_market_calendars as mcal

st.set_page_config(page_title="Optimiertes Musterdepot", layout="wide")
st.title("💼 Persönliches Musterdepot (VW sichtbar, aber nicht gewichtet)")

data_file = "depot_data.csv"

# -------------------------------
# Depotstruktur
# -------------------------------
data = [
    {"Ticker": "NVDA", "Name": "NVIDIA", "Sector": "Tech", "Currency": "USD"},
    {"Ticker": "MSFT", "Name": "Microsoft", "Sector": "Tech", "Currency": "USD"},
    {"Ticker": "GOOGL", "Name": "Alphabet", "Sector": "Tech", "Currency": "USD"},
    {"Ticker": "ASML.AS", "Name": "ASML", "Sector": "Tech", "Currency": "EUR"},
    {"Ticker": "CRWD", "Name": "CrowdStrike", "Sector": "Cybersecurity", "Currency": "USD"},
    {"Ticker": "NOW", "Name": "ServiceNow", "Sector": "Cybersecurity", "Currency": "USD"},
    {"Ticker": "FSLR", "Name": "First Solar", "Sector": "Renewable", "Currency": "USD"},
    {"Ticker": "NEE", "Name": "NextEra Energy", "Sector": "Renewable", "Currency": "USD"},
    {"Ticker": "BEPC", "Name": "Brookfield Renewable", "Sector": "Renewable", "Currency": "USD"},
    {"Ticker": "TSLA", "Name": "Tesla", "Sector": "Disruption", "Currency": "USD"},
    {"Ticker": "PLTR", "Name": "Palantir", "Sector": "Disruption", "Currency": "USD"},
    {"Ticker": "SMCI", "Name": "Super Micro Computer", "Sector": "Disruption", "Currency": "USD"},
    {"Ticker": "JNJ", "Name": "Johnson & Johnson", "Sector": "Health", "Currency": "USD"},
    {"Ticker": "NVO", "Name": "Novo Nordisk", "Sector": "Health", "Currency": "USD"},
    {"Ticker": "AAPL", "Name": "Apple", "Sector": "Consumer", "Currency": "USD"},
    {"Ticker": "VOW3.DE", "Name": "Volkswagen", "Sector": "Excluded", "Currency": "EUR"},
]
df = pd.DataFrame(data)

# -------------------------------
# Alphabetisch sortieren
# -------------------------------
df = df.sort_values(by="Name").reset_index(drop=True)

# -------------------------------
# Wechselkurs USD->EUR
# -------------------------------
try:
    eurusd = yf.Ticker("EURUSD=X").history(period="1d")['Close'][-1]
except Exception:
    eurusd = 1.0

# -------------------------------
# Kursabruf
# -------------------------------
def get_price(row):
    try:
        hist = yf.Ticker(row["Ticker"]).history(period="1d")
        if hist.empty:
            return np.nan
        price = float(hist['Close'][-1])
        if row["Currency"] == "USD":
            price /= eurusd
        return price
    except Exception:
        return np.nan

if "Price" not in df.columns or df["Price"].isna().all():
    df["Price"] = df.apply(get_price, axis=1)

if st.button("🔄 Kurse aktualisieren"):
    df["Price"] = df.apply(get_price, axis=1)
    st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
    st.success("Kurse aktualisiert ✅")

# -------------------------------
# Shares laden
# -------------------------------
if os.path.exists(data_file):
    saved = pd.read_csv(data_file)
    st.session_state.shares_dict = dict(zip(saved["Ticker"], saved["Shares"]))
else:
    st.session_state.shares_dict = {t: 0 for t in df["Ticker"]}
    st.session_state.shares_dict["VOW3.DE"] = 57.213

df["Shares"] = df["Ticker"].map(st.session_state.shares_dict)

# -------------------------------
# Editierbare Shares
# -------------------------------
st.subheader("📊 Depot Shares manuell eingeben")
edited = st.data_editor(df[["Ticker", "Name", "Shares"]], num_rows="dynamic", use_container_width=True)

for idx, row in edited.iterrows():
    st.session_state.shares_dict[row["Ticker"]] = row["Shares"]
    df.at[idx, "Shares"] = row["Shares"]

# -------------------------------
# Xetra Kalender
# -------------------------------
xetra = mcal.get_calendar('XETR')
def next_trading_day(date):
    schedule = xetra.schedule(start_date=date, end_date=date + pd.Timedelta(days=365))
    valid = schedule.index[schedule.index.date >= date.date()]
    return valid[0] if len(valid) > 0 else date

plan_day = pd.Timestamp(2025, 11, 6)
plan_day = next_trading_day(plan_day)
today = pd.Timestamp(datetime.now(timezone('Europe/Berlin')).date()).tz_localize(None)

# -------------------------------
# Sparplanlogik
# -------------------------------
weights = {
    "NVDA": 0.375, "MSFT": 0.25, "GOOGL": 0.25, "ASML.AS": 0.125,
    "CRWD": 0.5, "NOW": 0.5,
    "FSLR": 0.4, "NEE": 0.4, "BEPC": 0.2,
    "TSLA": 0.5, "PLTR": 0.25, "SMCI": 0.25,
    "JNJ": 0.5, "NVO": 0.5,
    "AAPL": 1.0
}
monthly = {
    "Tech": 200, "Cybersecurity": 50, "Renewable": 125,
    "Disruption": 100, "Health": 50, "Consumer": 75
}

if today >= plan_day:
    for idx, row in df.iterrows():
        if row["Ticker"] == "VOW3.DE":
            continue
        sector = row["Sector"]
        plan = monthly.get(sector, 0)
        weight = weights.get(row["Ticker"], 1.0)
        price = row["Price"]
        if price > 0:
            add = (plan * weight) / price
            df.at[idx, "Shares"] = st.session_state.shares_dict.get(row["Ticker"], 0) + add
            st.session_state.shares_dict[row["Ticker"]] = df.at[idx, "Shares"]
    st.success(f"✅ Sparplan ausgeführt am {plan_day.date()}")

# -------------------------------
# Marktwerte
# -------------------------------
df["MarketValue"] = (df["Shares"] * df["Price"]).round(2)
total_value = df["MarketValue"].sum()
st.markdown(f"**Gesamtwert (inkl. VW):** {total_value:,.2f} €")

# -------------------------------
# VW ausschließen aus Sektorlogik
# -------------------------------
df_active = df[df["Sector"] != "Excluded"]

# -------------------------------
# Umschichtungsvorschläge (Teil-/Komplettverkäufe)
# -------------------------------
targets = {"Tech": 0.4, "Cybersecurity": 0.1, "Renewable": 0.2,
           "Disruption": 0.15, "Health": 0.1, "Consumer": 0.05}

sector_values = df_active.groupby("Sector")["MarketValue"].sum().to_dict()
active_total = df_active["MarketValue"].sum()
sector_weights = {s: (sector_values.get(s, 0) / active_total if active_total > 0 else 0) for s in targets.keys()}

st.subheader("🔁 Umschichtungsvorschläge (ohne VW)")
for s, t in targets.items():
    diff = sector_weights.get(s, 0) - t
    if diff > 0.05:
        st.warning(f"📉 {s}: übergewichtet um {diff*100:.1f}%. Erwäge Teil- oder Komplettverkäufe einzelner Aktien im Sektor.")
    elif diff < -0.05:
        st.info(f"📈 {s}: untergewichtet um {-diff*100:.1f}%. Investiere mehr in die einzelnen Aktien des Sektors.")
if all(abs(sector_weights.get(s, 0) - targets[s]) < 0.05 for s in targets):
    st.success("✅ Keine Umschichtung nötig")

# -------------------------------
# Pie Chart
# -------------------------------
st.subheader("📈 Sektorverteilung (VW ausgeschlossen)")
fig, ax = plt.subplots()
sizes = [sector_weights.get(s, 0) for s in targets.keys()]
ax.pie(sizes, labels=targets.keys(), autopct='%1.1f%%')
ax.axis("equal")
st.pyplot(fig)

# -------------------------------
# Prozentuale Sektoranteile
# -------------------------------
st.subheader("🔹 Aktienanteile innerhalb der Sektoren")
for sector, group in df_active.groupby("Sector"):
    total = group["MarketValue"].sum()
    group["PercentOfSector"] = (group["MarketValue"] / total * 100).round(2)
    st.write(f"**{sector}** (Gesamtwert: {total:,.2f} €)")
    st.dataframe(group[["Ticker", "Name", "Shares", "Price", "MarketValue", "PercentOfSector"]])

# -------------------------------
# CSV speichern
# -------------------------------
df[["Ticker", "Shares"]].to_csv(data_file, index=False)
