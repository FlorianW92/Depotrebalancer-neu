import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pytz import timezone
import os
import pandas_market_calendars as mcal

st.set_page_config(page_title="Persistentes Musterdepot", layout="wide")
st.title("💼 Persönliches Optimiertes Musterdepot (mit VW, aber ohne VW-Gewichtung)")

# --------------------------------------------------------
# 🔹 Speicherdatei
# --------------------------------------------------------
data_file = "depot_data.csv"

# --------------------------------------------------------
# 🔹 Depotdefinition
# --------------------------------------------------------
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

# --------------------------------------------------------
# 🔹 Wechselkurs EUR/USD
# --------------------------------------------------------
try:
    eurusd = yf.Ticker("EURUSD=X").history(period="1d")['Close'][-1]
except Exception:
    eurusd = 1.0

# --------------------------------------------------------
# 🔹 Preisabruf
# --------------------------------------------------------
def get_price(row):
    try:
        ticker = yf.Ticker(row["Ticker"])
        hist = ticker.history(period="1d")
        if len(hist) == 0:
            return np.nan
        price = float(hist['Close'][-1])
        if row["Currency"] == "USD":
            price /= eurusd
        return price
    except Exception:
        return np.nan

# --------------------------------------------------------
# 🔹 Aktualisieren-Button
# --------------------------------------------------------
if st.button("🔄 Kurse aktualisieren"):
    df["Price"] = df.apply(get_price, axis=1)
    st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
    st.success("Kurse erfolgreich aktualisiert ✅")

if "Price" not in df.columns or df["Price"].isna().all():
    df["Price"] = df.apply(get_price, axis=1)

# --------------------------------------------------------
# 🔹 Bestehende Shares laden oder initialisieren
# --------------------------------------------------------
if os.path.exists(data_file):
    saved = pd.read_csv(data_file)
    st.session_state.shares_dict = dict(zip(saved["Ticker"], saved["Shares"]))
else:
    st.session_state.shares_dict = {t: 0 for t in df["Ticker"]}
    st.session_state.shares_dict["VOW3.DE"] = 57.213  # VW fester Bestand

df["Shares"] = df["Ticker"].map(st.session_state.shares_dict)

# --------------------------------------------------------
# 🔹 Manuelle Eingabe der Shares
# --------------------------------------------------------
st.subheader("📊 Depot Shares manuell eingeben")
edited = st.data_editor(
    df[["Ticker", "Name", "Shares"]],
    num_rows="dynamic",
    use_container_width=True
)
for idx, row in edited.iterrows():
    st.session_state.shares_dict[row["Ticker"]] = row["Shares"]
    df.at[idx, "Shares"] = row["Shares"]

# --------------------------------------------------------
# 🔹 Sparplan
# --------------------------------------------------------
weights_within_sector = {
    "NVDA": 0.375, "MSFT": 0.25, "GOOGL": 0.25, "ASML.AS": 0.125,
    "CRWD": 0.5, "NOW": 0.5,
    "FSLR": 0.4, "NEE": 0.4, "BEPC": 0.2,
    "TSLA": 0.5, "PLTR": 0.25, "SMCI": 0.25,
    "JNJ": 0.5, "NVO": 0.5,
    "AAPL": 1.0
}
monthly_plan = {
    "Tech": 200,
    "Cybersecurity": 50,
    "Renewable": 125,
    "Disruption": 100,
    "Health": 50,
    "Consumer": 75
}

# --------------------------------------------------------
# 🔹 Feiertags- & Wochenendlogik (Xetra)
# --------------------------------------------------------
xetra = mcal.get_calendar('XETR')
def next_trading_day(date):
    schedule = xetra.schedule(start_date=date, end_date=date + pd.Timedelta(days=365))
    future_days = schedule.index[schedule.index.date >= date.date()]
    if len(future_days) == 0:
        return date
    return future_days[0]

# --------------------------------------------------------
# 🔹 Automatische Ausführung ab 6.11.2025
# --------------------------------------------------------
plan_day = pd.Timestamp(2025, 11, 6)
plan_day = next_trading_day(plan_day)
today = pd.Timestamp(datetime.now(timezone('Europe/Berlin')).date()).tz_localize(None)

if today >= plan_day:
    for idx, row in df.iterrows():
        ticker = row["Ticker"]
        if ticker == "VOW3.DE":  # VW bleibt ausgeschlossen
            continue
        sector = row["Sector"]
        price = row["Price"]
        if row["Currency"] == "USD":
            price /= eurusd
        sector_plan = monthly_plan.get(sector, 0)
        weight = weights_within_sector.get(ticker, 1.0)
        add_shares = (sector_plan * weight) / price if price > 0 else 0
        df.at[idx, "Shares"] = st.session_state.shares_dict.get(ticker, 0) + add_shares
        st.session_state.shares_dict[ticker] = df.at[idx, "Shares"]
    st.success(f"✅ Sparplan automatisch ausgeführt am {plan_day.date()}")

# --------------------------------------------------------
# 🔹 Berechnungen
# --------------------------------------------------------
df["MarketValue"] = (df["Shares"] * df["Price"]).round(2)
total_value = df["MarketValue"].sum()

st.markdown(f"**Gesamtwert (inkl. VW):** {total_value:,.2f} €")
st.caption(f"Letztes Update: {st.session_state.get('last_update', 'automatisch')}")

# --------------------------------------------------------
# 🔹 Umschichtungsvorschläge (ohne VW)
# --------------------------------------------------------
df_active = df[df["Sector"] != "Excluded"]
target_weights = {
    "Tech": 0.4, "Cybersecurity": 0.1, "Renewable": 0.2,
    "Disruption": 0.15, "Health": 0.1, "Consumer": 0.05
}
sector_values = df_active.groupby("Sector")["MarketValue"].sum().to_dict()
active_total = df_active["MarketValue"].sum()
sector_weights = {s: (sector_values.get(s, 0) / active_total if active_total > 0 else 0)
                  for s in target_weights.keys()}

st.subheader("🔁 Umschichtungsvorschläge (ohne VW)")
threshold = 0.05
for sector, target in target_weights.items():
    current = sector_weights.get(sector, 0)
    diff = current - target
    if diff > threshold:
        st.warning(f"📉 {sector}: übergewichtet um {diff*100:.1f}% → Teilverkauf prüfen")
    elif diff < -threshold:
        st.info(f"📈 {sector}: untergewichtet um {-diff*100:.1f}% → Aufstockung prüfen")
if all(abs(sector_weights.get(s, 0) - target_weights[s]) < threshold for s in target_weights):
    st.success("✅ Keine Umschichtung nötig")

# --------------------------------------------------------
# 🔹 Diagramm (ohne VW)
# --------------------------------------------------------
st.subheader("📈 Sektorverteilung (ohne VW)")
labels = list(target_weights.keys())
sizes = [sector_weights.get(s, 0) for s in labels]
if sum(sizes) > 0:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, labels=labels, autopct=lambda p: f'{p:.1f}%' if p > 0 else '')
    ax.axis('equal')
    st.pyplot(fig)

# --------------------------------------------------------
# 🔹 Prozentanteile in Sektoren (ohne VW)
# --------------------------------------------------------
st.subheader("🔹 Aktienanteile innerhalb der Sektoren (ohne VW)")
for sector, group in df_active.groupby("Sector"):
    total = group["MarketValue"].sum()
    if total > 0:
        st.write(f"**{sector}** (Gesamtwert: {total:,.2f} €)")
        temp = group.copy()
        temp["PercentOfSector"] = (temp["MarketValue"] / total * 100).round(2)
        st.dataframe(temp[["Ticker", "Name", "Shares", "Price", "MarketValue", "PercentOfSector"]])

# --------------------------------------------------------
# 🔹 Daten speichern
# --------------------------------------------------------
df_save = df[["Ticker", "Shares"]]
df_save.to_csv(data_file, index=False)

