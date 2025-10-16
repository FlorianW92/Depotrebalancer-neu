import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import pandas_market_calendars as mcal

st.set_page_config(page_title="Optimiertes Musterdepot mit Sparplan", layout="wide")
st.title("💼 Optimiertes Musterdepot — Manuelle Shares & Sparplan")

# --- Sidebar Einstellungen ---
st.sidebar.header("Einstellungen")
refresh_interval = st.sidebar.slider("Automatische Kursaktualisierung (Minuten)", 1, 30, 5)
if st.sidebar.button("Kurse jetzt aktualisieren"):
    st.session_state.refresh = True

# --- Optimiertes Depot ---
data = [
    {"Ticker":"NVDA","Name":"NVIDIA","Sector":"Tech","Currency":"USD"},
    {"Ticker":"MSFT","Name":"Microsoft","Sector":"Tech","Currency":"USD"},
    {"Ticker":"GOOGL","Name":"Alphabet","Sector":"Tech","Currency":"USD"},
    {"Ticker":"ASML.AS","Name":"ASML","Sector":"Tech","Currency":"EUR"},
    {"Ticker":"CRWD","Name":"CrowdStrike","Sector":"Cybersecurity","Currency":"USD"},
    {"Ticker":"NOW","Name":"ServiceNow","Sector":"Cybersecurity","Currency":"USD"},
    {"Ticker":"FSLR","Name":"First Solar","Sector":"Renewable","Currency":"USD"},
    {"Ticker":"NEE","Name":"NextEra Energy","Sector":"Renewable","Currency":"USD"},
    {"Ticker":"BEPC","Name":"Brookfield Renewable","Sector":"Renewable","Currency":"USD"},
    {"Ticker":"TSLA","Name":"Tesla","Sector":"Disruption","Currency":"USD"},
    {"Ticker":"PLTR","Name":"Palantir","Sector":"Disruption","Currency":"USD"},
    {"Ticker":"SMCI","Name":"Super Micro Computer","Sector":"Disruption","Currency":"USD"},
    {"Ticker":"JNJ","Name":"Johnson & Johnson","Sector":"Health","Currency":"USD"},
    {"Ticker":"NVO","Name":"Novo Nordisk","Sector":"Health","Currency":"USD"},
    {"Ticker":"AAPL","Name":"Apple","Sector":"Consumer","Currency":"USD"},
    {"Ticker":"VOW3.DE","Name":"Volkswagen","Sector":"Consumer","Currency":"EUR"},
]
df = pd.DataFrame(data)

# --- Wechselkurs EUR/USD ---
try:
    eurusd = yf.Ticker("EURUSD=X").history(period="1d", interval="1m")['Close'][-1]
except:
    eurusd = 1.0

# --- Preisabruf ---
def get_price(row):
    try:
        ticker = yf.Ticker(row["Ticker"])
        hist = ticker.history(period="1d", interval="1m") if row["Currency"]=="USD" else ticker.history(period="1d")
        price = float(hist['Close'][-1]) if len(hist)>0 else float(ticker.history(period="1d")['Close'][-1])
        if row["Currency"]=="USD":
            price /= eurusd
        return price
    except:
        return np.nan

# --- Kursaktualisierung ---
if "refresh" not in st.session_state:
    st.session_state.refresh = True
if st.session_state.refresh or "Price" not in df.columns:
    df["Price"] = df.apply(get_price, axis=1)
    st.session_state.refresh = False

# --- Persistent Shares ---
if "shares_dict" not in st.session_state:
    st.session_state.shares_dict = {t:0 for t in df["Ticker"]}
    # VW-Bestand initial
    if not np.isnan(df.loc[df["Ticker"]=="VOW3.DE", "Price"].values[0]):
        st.session_state.shares_dict["VOW3.DE"] = 5300 / df.loc[df["Ticker"]=="VOW3.DE", "Price"].values[0]
    else:
        st.session_state.shares_dict["VOW3.DE"] = 0

# --- Editable DataFrame für Anzeige ---
df["Shares"] = df["Ticker"].map(st.session_state.shares_dict)

st.subheader("Depot Shares eingeben")
edited = st.data_editor(
    df[["Ticker","Name","Shares"]],
    num_rows="dynamic",
    use_container_width=True
)

# --- Übernahme der Eingaben ---
for idx, row in edited.iterrows():
    st.session_state.shares_dict[row["Ticker"]] = row["Shares"]
    df.at[idx,"Shares"] = row["Shares"]

# --- Sparplan Logik ---
# Zielgewicht pro Aktie innerhalb des Sektors
weights_within_sector = {
    "NVDA":0.375, "MSFT":0.25, "GOOGL":0.25, "ASML.AS":0.125,
    "CRWD":0.5, "NOW":0.5,
    "FSLR":0.4, "NEE":0.4, "BEPC":0.2,
    "TSLA":0.5, "PLTR":0.25, "SMCI":0.25,
    "JNJ":0.5, "NVO":0.5,
    "AAPL":0.5, "VOW3.DE":0.5
}
# Monatlicher Sparplan pro Sektor
monthly_plan = {
    "Tech":200,
    "Cybersecurity":50,
    "Renewable":125,
    "Disruption":100,
    "Health":50,
    "Consumer":75
}

# --- Handelskalender Xetra ---
xetra = mcal.get_calendar('XETR')
today = pd.Timestamp(datetime.today().date())

# Berechne nächster Sparplantag ab 6.11.
start_date = pd.Timestamp('2025-11-06')
# Prüfe nächster gültiger Handelstag
sched = xetra.valid_days(start_date=start_date, end_date=start_date + pd.DateOffset(months=12))
if len(sched) > 0:
    next_trade_day = sched[0]
else:
    next_trade_day = start_date

# --- Sparplan nur ausführen an Börsentag ---
if today >= next_trade_day and today in xetra.valid_days(start_date=today, end_date=today):
    for idx, row in df.iterrows():
        sector = row["Sector"]
        ticker = row["Ticker"]
        price = row["Price"]
        sector_plan = monthly_plan.get(sector,0)
        weight = weights_within_sector.get(ticker,1.0)
        additional_shares = (sector_plan * weight) / price if price>0 else 0
        df.at[idx,"Shares"] = st.session_state.shares_dict.get(ticker,0) + additional_shares

# --- Market Value ---
df["MarketValue"] = (df["Shares"] * df["Price"]).round(2)
total_value = df["MarketValue"].sum()
st.write(f"Stand: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S (UTC)')} — Gesamtwert: {total_value:,.2f} €")

# --- Umschichtungsvorschläge ---
target_weights = {"Tech":0.4,"Cybersecurity":0.1,"Renewable":0.2,"Disruption":0.15,"Health":0.1,"Consumer":0.05}
sector_values = df.groupby("Sector")["MarketValue"].sum().to_dict()
sector_weights = {s:(sector_values.get(s,0)/total_value if total_value>0 else 0) for s in target_weights.keys()}

st.subheader("Umschichtungsvorschläge")
threshold = 0.05
suggestions = []
for sector, target in target_weights.items():
    current = sector_weights.get(sector,0)
    diff = current - target
    if diff > threshold:
        suggestions.append(f"{sector} übergewichtet → Teilverkauf empfohlen ({diff*100:.1f}% über Zielgewicht)")
    elif diff < -threshold:
        suggestions.append(f"{sector} untergewichtet → Aufstockung empfohlen ({-diff*100:.1f}% unter Zielgewicht)")
if suggestions:
    for s in suggestions: st.info(s)
else:
    st.success("Keine Umschichtungen nötig")

# --- Pie-Chart Sektorverteilung ---
st.subheader("Sektorverteilung")
labels = list(target_weights.keys())
sizes = [sector_weights.get(s,0) for s in labels]
if sum(sizes)>0:
    fig, ax = plt.subplots(figsize=(6,4))
    ax.pie(sizes, labels=labels, autopct=lambda p:f'{p:.1f}%' if p>0 else '')
    ax.axis('equal')
    st.pyplot(fig)

# --- Prozentuale Aktienanteile innerhalb der Sektoren ---
st.subheader("Aktienanteile innerhalb der Sektoren")
for sector, group in df.groupby("Sector"):
    sector_total = group["MarketValue"].sum()
    if sector_total>0:
        st.write(f"**{sector}** (Gesamtwert: {sector_total:,.2f} €)")
        temp = group.copy()
        temp["PercentOfSector"] = (temp["MarketValue"]/sector_total*100).round(2)
        st.dataframe(temp[["Ticker","Name","Shares","Price","MarketValue","PercentOfSector"]])
