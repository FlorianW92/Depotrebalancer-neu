# -------------------------------
# Umschichtungsvorschläge nach Aktiengewicht
# -------------------------------
st.subheader("🔁 Umschichtungsvorschläge nach Aktiengewicht (ohne VW)")

for sector, group in df_active.groupby("Sector"):
    total_sector_value = group["MarketValue"].sum()
    for idx, row in group.iterrows():
        # Zielgewicht innerhalb des Sektors
        monthly_amount = weights.get(row["Ticker"], 1.0) * monthly.get(sector, 0)
        target_value = monthly_amount  # simplifiziert: Zielwert aus Sparplan
        actual_value = row["MarketValue"]
        diff_pct = (actual_value - target_value) / target_value if target_value > 0 else 0

        if diff_pct > 0.05:
            st.warning(f"📉 {row['Name']} ({sector}) über Zielwert um {diff_pct*100:.1f}% → Teilverkauf erwägen")
        elif diff_pct < -0.05:
            st.info(f"📈 {row['Name']} ({sector}) unter Zielwert um {-diff_pct*100:.1f}% → Aufstocken")
        else:
            st.success(f"✅ {row['Name']} ({sector}) im Zielbereich ({diff_pct*100:.1f}%)")
