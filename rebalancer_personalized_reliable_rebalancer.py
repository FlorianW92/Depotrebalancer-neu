import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

FRACTION_PRECISION = 3

st.set_page_config(page_title="Personal Rebalancer Komplett XETRA", layout="wide")
st.title("📊 Personal Rebalancer — Vollständig & Euro (XETRA für DE-Aktien)")

# --- Sidebar Einstellungen ---
st.sidebar.header("Einstellungen")
refresh_interval = st.sidebar.slider("Automatische Kursaktualisierung (Minuten)", 1,30,5)
st_autorefresh(interval=refresh_interval*60*1000, key="auto_refresh")

# --- Depot Definition ---
initial = [
    {"Ticker":"NVDA","Name":"NVIDIA","Sector":"Tech","MonthlyAlloc":75,"Currency":"USD"},
    {"Ticker":"MSFT","Name":"Microsoft","Sector":"Tech","MonthlyAlloc":50,"Currency":"USD"},
    {"Ticker":"GOOGL","Name":"Alphabet","Sector":"Tech","MonthlyAlloc":50,"Currency":"USD"},
    {"Ticker":"ASML","Name":"ASML","Sector":"Tech","MonthlyAlloc":25,"Currency":"USD"},
    {"Ticker":"CRWD","Name":"CrowdStrike","Sector":"Cyber","MonthlyAlloc":25,"Currency":"USD"},
    {"Ticker":"NOW","Name":"ServiceNow","Sector":"Cyber","MonthlyAlloc":25,"Currency":"USD"},
    {"Ticker":"FSLR","Name":"First Solar","Sector":"Renewable","MonthlyAlloc":50,"Currency":"USD"},
    {"Ticker":"NEE","Name":"NextEra Energy","Sector":"Renewable","MonthlyAlloc":25,"Currency":"USD"},
    {"Ticker":"BEPC","Name":"Brookfield Renewable","Sector":"Renewable","MonthlyAlloc":25,"Currency":"USD"},
    {"Ticker":"TSLA","Name":"Tesla","Sector":"Disruption","MonthlyAlloc":37.5,"Currency":"USD"},
    {"Ticker":"PLTR","Name":"Palantir","Sector":"Disruption","MonthlyAlloc":25,"Currency":"USD"},
    {"Ticker":"SMCI","Name":"Super Micro Computer","Sector":"Disruption","MonthlyAlloc":12.5,"Currency":"USD"},
    {"Ticker":"JNJ","Name":"Johnson & Johnson","Sector":"Health","MonthlyAlloc":25,"Currency":"USD"},
    {"Ticker":"NVO","Name":"Novo Nordisk","Sector":"Health","MonthlyAlloc":25,"Currency":"USD"},
    {"Ticker":"AAPL","Name":"Apple","Sector":"Consumer","MonthlyAlloc":25,"Currency":"USD"},
    {"Ticker":"VOW3.DE","Name":"Volkswagen","Sector":"Blue Chips","MonthlyAlloc":0,"Currency":"EUR"} # XETRA
]

df = pd.DataFrame(initial)

# --- Button für sofortige Aktualisierung ---
if "refresh" not in st.session_state:
    st.session_state.refresh = False
if st.button("Kurse jetzt aktualisieren"):
    st.session_state.refresh = True

# --- EUR/USD Wechselkurs ---
try:
    eurusd = yf.Ticker("EURUSD=X").history(period="1d", interval="1m")['Close'][-1]
except:
    eurusd = 1.0

# --- Preisabruf in Euro (USD → EUR, DE → XETRA) ---
def get_price(row):
    t = row["Ticker"]
    try:
        ticker = yf.Ticker(t)
        if row["Currency"]=="USD":
            hist = ticker.history(period="1d", interval="1m")
            if len(hist) > 0:
                price_usd = float(hist['Close'][-1])
            else:
                hist = ticker.history(period="1d")
                price_usd = float(hist['Close'][-1])
            return price_usd / eurusd
        else:  # EUR / XETRA
            hist = ticker.history(period="1d")
            return float(hist['Close'][-1])
    except:
        return np.nan

# --- Kursaktualisierung nur Preis, Shares bleiben unverändert ---
if st.session_state.refresh or "Price" not in df.columns:
    for i, row in df.iterrows():
        df.at[i, "Price"] = get_price(row)
    st.session_state.refresh = False

# --- Initial Shares Berechnung (nur einmal, persistent) ---
if "SharesInitialized" not in st.session_state:
    shares_list = []
    for i, row in df.iterrows():
        if row["Ticker"]=="VOW3.DE":
            shares_list.append(57.0)
        else:
            p = row["Price"]
            if pd.notna(p) and p>0 and row["MonthlyAlloc"]>0:
                shares_list.append(round(row["MonthlyAlloc"]*12 / p, FRACTION_PRECISION))
            else:
                shares_list.append(0.0)
    df["Shares"] = shares_list
    st.session_state.SharesInitialized = True

# --- MarketValue immer berechnen ---
df["MarketValue"] = (df["Shares"] * df["Price"]).round(2)

# --- Editable Portfolio ---
st.subheader("Depot bearbeiten")
editable = st.data_editor(df[["Ticker","Name","Shares","Price","Sector","MonthlyAlloc"]],
                          num_rows="dynamic", use_container_width=True)

# --- Persistente Übernahme der Shares ---
for i, row in editable.iterrows():
    df.at[i, "Shares"] = row["Shares"]
df["MarketValue"] = (df["Shares"] * df["Price"]).round(2)

# --- Gesamtwert anzeigen ---
total_value = df["MarketValue"].sum()
st.write(f"Stand: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S (UTC)')} — Gesamtwert: {total_value:,.2f} €")

# --- Automatische Umschichtungsvorschläge ---
target_weights = {"Tech":0.40,"Cyber":0.10,"Renewable":0.20,"Disruption":0.15,"Health":0.10,"Consumer":0.05,"Blue Chips":0.0}
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
    for s in suggestions:
        st.info(s)
else:
    st.success("Keine Umschichtungen nötig")

# --- Sektorverteilung Pie-Chart ---
st.subheader("Sektorverteilung")
labels = list(target_weights.keys())
sizes = [sector_weights.get(s,0) for s in labels]
if sum(sizes) > 0:
    fig, ax = plt.subplots(figsize=(6,4))
    ax.pie(sizes, labels=labels, autopct=lambda p: f'{p:.1f}%' if p>0 else '')
    ax.axis('equal')
    st.pyplot(fig)
else:
    st.info("Keine Werte im Depot vorhanden, daher keine Grafik.")
