import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

FRACTION_PRECISION = 3

st.set_page_config(page_title="Personal Rebalancer Komplett", layout="wide")
st.title("📊 Personal Rebalancer — Vollständig & Stabil (Euro)")

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
    {"Ticker":"VOW3.DE","Name":"Volkswagen (VOW3)","Sector":"Blue Chips","MonthlyAlloc":0,"Currency":"EUR"}
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
    eurusd = 1.0  # fallback falls Abfrage fehlschlägt

# --- Preisabruf in Euro ---
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
        else:
            hist = ticker.history(period="1d")
            return float(hist['Close'][-1])
    except:
        return np.nan

if st.session_state.refresh or "Price" not in df.columns:
    prices = [get_price(row) for _, row in df.iterrows()]
    df["Price"] = prices
    st.session_state.refresh = False

# --- Berechnung Shares & MarketValue ---
def derive_shares(row):
    if row["Ticker"]=="VOW3.DE":
        return 57.0
    p = row["Price"]
    if pd.notna(p) and p>0 and row["MonthlyAlloc"]>0:
        invested = row["MonthlyAlloc"] * 12
        return round(invested / p, FRACTION_PRECISION)
    return 0.0

df["Shares"] = df.apply(derive_shares, axis=1)
df["MarketValue"] = (df["Shares"] * df["Price"]).round(2)

# --- Editable Portfolio ---
st.subheader("Depot bearbeiten")
editable = st.data_editor(df[["Ticker","Name","Shares","Price","Sector","MonthlyAlloc","MarketValue"]],
                          num_rows="dynamic", use_container_width=True)

total_value = editable["MarketValue"].sum()
st.write(f"Stand: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S (UTC)')} — Gesamtwert: {total_value:,.2f} €")

# --- Automatische Umschichtungsvorschläge ---
target_weights = {"Tech":0.40,"Cyber":0.10,"Renewable":0.20,"Disruption":0.15,"Health":0.10,"Consumer":0.05,"Blue Chips":0.0}
sector_values = editable.groupby("Sector")["MarketValue"].sum().to_dict()
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

# --- Sektorverteilung ---
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
