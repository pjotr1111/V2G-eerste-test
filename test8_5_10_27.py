

# === Pagina-instelling en bibliotheken ===
import streamlit as st
import pandas as pd
import numpy as np
import random
from io import BytesIO

st.set_page_config(page_title="🔋 V2G Simulatie Tool", layout="wide")

# === Layout: introductie en financiële resultaten naast elkaar ===
col_intro, col_metrics = st.columns([2, 1])

with col_intro:
    st.title("🔋 V2G Simulatie – Vehicle-to-Grid")
    st.markdown("""
    Deze tool simuleert hoeveel je per jaar kunt verdienen door slim gebruik te maken van **Vehicle-to-Grid (V2G)**.  
    Je laadt je elektrische auto op tijdens lage prijzen, en levert terug aan het net tijdens hoge prijzen.

    ### 💡 Wat deze tool doet:
    - Gebruikt échte uurlijkse stroomprijzen van 2024  
    - Gebruikt jouw weekprofiel (wanneer de auto beschikbaar is)  
    - Houdt rekening met accubegrenzingen, efficiëntie en laadsnelheid  
    - Simuleert elke dag van het jaar slim laden of ontladen  
    """)

# 🧪 Placeholder voor opbrengstmetrics (wordt later ingevuld)
with col_metrics:
    winst_placeholder = st.empty()
    opbrengst_placeholder = st.empty()
    kosten_placeholder = st.empty()

# === Sidebar instellingen ===
st.sidebar.header("🔧 Instellingen")
accu = st.sidebar.number_input("Accucapaciteit (kWh)", value=60)
soc_min = st.sidebar.slider("Min SOC (%)", 0, 100, 20, help="Voorkomt dat je accu te leeg raakt")
soc_max = st.sidebar.slider("Max SOC (%)", 0, 100, 80, help="Voorkomt overladen – behoud van acculevensduur")
laadvermogen = st.sidebar.number_input("Laadsnelheid (kW)", value=12.8)
eff = st.sidebar.slider("Efficiëntie teruglevering (%)", 50, 100, 85) / 100
weken_actief = st.sidebar.slider("Aantal weken per jaar beschikbaar", 1, 52, 50)

# === Weekprofiel ===
st.markdown("## 📅 Weekprofiel instellen")
st.info("""
Je stelt hieronder een voorbeeldweek in. De tool gebruikt dit profiel voor **elke week** in het jaar.  
Gebruik dit om aan te geven wanneer je auto thuis is en beschikbaar is voor V2G.

- **✅ Beschikbaar:** laden of ontladen mogelijk  
- **🚗 In gebruik:** auto rijdt → trekt 10 kWh per uur uit accu  
- **❌ Niet beschikbaar:** geen actie mogelijk
""")

status_opties = {
    "❌ Niet beschikbaar": 0,
    "✅ Beschikbaar": 1,
    "🚗 In gebruik": 2
}

weekdagen = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weekprofiel = pd.DataFrame(index=range(24), columns=weekdagen)

for dag in weekdagen:
    st.markdown(f"**{dag}**")
    cols = st.columns(6)
    for uur in range(24):
        keuze = cols[uur % 6].selectbox(f"{uur}:00", list(status_opties.keys()), key=f"{dag}_{uur}")
        weekprofiel.loc[uur, dag] = status_opties[keuze]

# === Stroomprijsdata laden ===
df = pd.read_excel("Stroomprijzen_2024_Met_Weekinfo.xlsx")
df["datum"] = pd.to_datetime(df["datum"])
df["dag"] = df["datum"].dt.date
df["uur"] = df["datum"].dt.hour
df["dagnaam"] = df["datum"].dt.day_name()
df["week"] = df["datum"].dt.isocalendar().week

# === Selecteer actieve weken ===
alle_weken = df["week"].unique()
weken_afwezig = random.sample(list(alle_weken), 52 - weken_actief)
df["actief"] = ~df["week"].isin(weken_afwezig)

# === Simulatie uitvoeren ===
soc = accu  # Start op 100%
df["actie"] = "geen"
df["geladen"] = 0.0
df["ontladen"] = 0.0
df["soc"] = 0.0
df["kosten"] = 0.0
df["opbrengst"] = 0.0

for i, row in df.iterrows():
    if not row["actief"]:
        df.at[i, "soc"] = soc
        continue

    status = int(weekprofiel.loc[row["uur"], row["dagnaam"]])
    if status == 0:
        actie = "niet beschikbaar"
    elif status == 2:
        soc -= 10
        soc = max(soc, soc_min / 100 * accu)
        actie = "in gebruik"
    elif status == 1:
        if soc < soc_max / 100 * accu and row["Inkoop"] < row["Verkoop"]:
            kWh = min(laadvermogen, (soc_max / 100 * accu) - soc)
            soc += kWh
            df.at[i, "geladen"] = kWh
            df.at[i, "kosten"] = kWh * row["Inkoop"]
            actie = "laden"
        elif soc > soc_min / 100 * accu and row["Verkoop"] > row["Inkoop"]:
            kWh = min(laadvermogen, soc - (soc_min / 100 * accu))
            soc -= kWh
            df.at[i, "ontladen"] = kWh
            df.at[i, "opbrengst"] = kWh * row["Verkoop"] * eff
            actie = "ontladen"
        else:
            actie = "niets"
    df.at[i, "actie"] = actie
    df.at[i, "soc"] = soc

# === Resultaten berekenen ===
totaal_opbrengst = df["opbrengst"].sum()
totaal_kosten = df["kosten"].sum()
totaal_winst = totaal_opbrengst - totaal_kosten

# === Download knop ===
buffer = BytesIO()
df.to_excel(buffer, index=False, sheet_name="V2G Resultaten")
buffer.seek(0)

st.download_button(
    label="⬇️ Download volledige simulatie als Excel",
    data=buffer,
    file_name="V2G_resultaten.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# === Resultaten rechtsboven weergeven ===
winst_placeholder.metric("📈 Totale Winst", f"€ {totaal_winst:.2f}")
opbrengst_placeholder.metric("💶 Opbrengst", f"€ {totaal_opbrengst:.2f}")
kosten_placeholder.metric("💸 Kosten", f"€ {totaal_kosten:.2f}")

# === Tabel voorbeeld ===
st.markdown("## 📈 Voorbeeld: eerste 48 uur")
st.dataframe(df[["datum", "uur", "actie", "soc", "geladen", "ontladen", "kosten", "opbrengst"]].head(48))
