import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

FRACTION_PRECISION = 3

st.set_page_config(page_title="Optimiertes Musterdepot", layout="wide")
st.title("💼 Optimiertes Musterdepot — Manuelle Shares Eingabe & Euro")

# --- Sidebar Einstellungen ---
st.sidebar.header("Einstellungen")
refresh_interval = st.sidebar.slider("Automatische Kursaktualisierung (Minuten)", 1, 30, 5)
st_autorefresh(interval=refresh_interval * 60 * 1000, key="auto_refresh")

# --- Optimiertes Musterdepot (Start 6. Nov 2025) ---
data = [
    # Technologie & KI
    {"Ticker":"NVDA","Name":"NVIDIA","Sector":"Tech","Currency":"USD"},
    {"Ticker":"MSFT","Name":"Microsoft","Sector":"Tech","Currency":"USD"},
    {"Ticker":"GOOGL","Name":"Alphabet","Sector":"Tech","Currency":"USD"},
    {"Ticker":"ASML.AS","Name":"ASML","Sector":"Tech","Currency":"EUR"},
    # Cybersecurity / Cloud
    {"Ticker":"CRWD","Name":"CrowdStrike","Sector":"Cybersecurity","Currency":"USD"},
    {"Ticker":"NOW","Name":"ServiceNow","Sector":"Cybersecurity","Currency":"USD"},
    # Erneuerbare Energien & Infra
    {"Ticker":"FSLR","Name":"First Solar","Sector":"Renewable","Currency":"USD"},
    {"Ticker":"NEE","Name":"NextEra Energy","Sector":"Renewable","Currency":"USD"},
    {"Ticker":"BEPC","Name":"Brookfield Renewable","Sector":"Renewable","Currency":"USD"},
    # Zukunft / Disruption
    {"Ticker":"TSLA","Name":"Tesla","Sector":"Disruption","Currency":"USD"},
    {"Ticker":"PLTR","Name":"Palantir","Sector":"Disruption","Currency":"USD"},
    {"Ticker":"SMCI","Name":"Super Micro Computer","Sector":"Disruption","Currency":"USD"},
    # Gesundheit / Stabilität
    {"Ticker":"JNJ","Name":"Johnson & Johnson","Sector":"Health","Currency":"USD"},
    {"Ticker":"NVO","Name":"Novo Nordisk","Sector":"Health","Currency":"USD"},
    # Konsum & Industrie
    {"Ticker":"AAPL","Name":"Apple","Sector":"Consumer","Currency":"USD"},
    {"Ticker":"VOW3.DE","Name":"Volkswagen","Sector":"Consumer","Currency":"EUR"},
]

df = pd.DataFrame(data)

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

# --- Preisabruf in Euro ---
def get_price(row):
    t = row["Ticker"]
    try:
        ticker = yf.Ticker(t)
        if row["Currency"]=="USD":
            hist = ticker.history(period="1d", interval="1m")
            price_usd = float(hist['Close'][-1]) if len(hist)>0 else float(ticker.history(period="1d")['Close'][-1])
            return price_usd / eurusd
        else:
            hist = ticker.history(period="1d")
            return float(hist['Close'][-1])
    except:
        return np.nan

# --- Kursaktualisierung ---
if st.session_state.refresh or "Price" not in df.columns:
    df["Price"] = df.apply(get_price, axis=1)
    st.session_state.refresh = False

# --- Persistent Shares ---
if "shares_dict" not in st.session_state:
    st.session_state.shares_dict = {t:0 for t in df["Ticker"]}
    # VW Bestand initial
    st.session_state.shares_dict["VOW3.DE"] = 5300 / get_price(df[df["Ticker"]=="VOW3.DE"].iloc[0])

# --- Editable DataFrame aus session_state erstellen ---
if "editable_df" not in st.session_state:
    st.session_state.editable_df = df.copy()
    st.session_state.editable_df["Shares"] = st.session_state.editable_df["Ticker"].map(st.session_state.shares_dict)

# --- DataEditor nur für Shares ---
st.subheader("Depot Shares eingeben")
edited = st.data_editor(
    st.session_state.editable_df[["Ticker","Name","Shares"]],
    num_rows="dynamic",
    use_container_width=True
)

# --- Übernahme der manuellen Eingaben ---
for idx, row in edited.iterrows():
    st.session_state.shares_dict[row["Ticker"]] = row["Shares"]
    st.session_state.editable_df.at[idx, "Shares"] = row["Shares"]

# --- Market Value berechnen ---
st.session_state.editable_df["Price"] = df["Price"]
st.session_state.editable_df["MarketValue"] = (st.session_state.editable_df["Shares"] * st.session_state.editable_df["Price"]).round(2)
df = st.session_state.editable_df.copy()

# --- Gesamtwert ---
total_value = df["MarketValue"].sum()
st.write(f"Stand: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S (UTC)')} — Gesamtwert: {total_value:,.2f} €")

# --- Umschichtungsvorschläge (optional nach Sparplan-Gewichten) ---
target_weights = {
    "Tech":0.4,
    "Cybersecurity":0.1,
    "Renewable":0.2,
    "Disruption":0.15,
    "Health":0.1,
    "Consumer":0.05,
}
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

# --- Pie-Chart Sektorverteilung ---
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

# --- Prozentuale Aktienanteile innerhalb der Sektoren ---
st.subheader("Aktienanteile innerhalb der Sektoren")
sector_groups = df.groupby("Sector")
for sector, group in sector_groups:
    sector_total = group["MarketValue"].sum()
    if sector_total > 0:
        st.write(f"**{sector}** (Gesamtwert: {sector_total:,.2f} €)")
        temp = group.copy()
        temp["PercentOfSector"] = (temp["MarketValue"]/sector_total*100).round(2)
        st.dataframe(temp[["Ticker","Name","Shares","Price","MarketValue","PercentOfSector"]])
