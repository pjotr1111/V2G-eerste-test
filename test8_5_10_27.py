import streamlit as st
import pandas as pd
import numpy as np
import random

st.set_page_config(page_title="⚡ V2G Webapp", layout="wide")
st.title("⚡ Vehicle-to-Grid Simulatie Tool")

# === Stap 1: Invoerparameters ===
st.sidebar.header("🔧 Instellingen")
accu = st.sidebar.number_input("Accucapaciteit (kWh)", value=60)
soc_min = st.sidebar.slider("Minimale SOC (%)", 0, 100, 20)
soc_max = st.sidebar.slider("Maximale SOC (%)", 0, 100, 80)
laadvermogen = st.sidebar.number_input("Laadsnelheid (kW)", value=12.8)
eff = st.sidebar.slider("Efficiëntie teruglevering (%)", 50, 100, 85) / 100
weken_actief = st.sidebar.slider("Aantal weken per jaar beschikbaar", 1, 52, 50)

# === Stap 2: Weekprofiel maken ===
st.subheader("📅 Weekprofiel (beschikbaarheid per uur)")

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

# === Stap 3: Upload stroomprijsbestand ===
st.subheader("📁 Upload Excel met stroomprijzen")
bestand = st.file_uploader("Bestand uploaden (.xlsx)", type=["xlsx"])

if bestand:
    df = pd.read_excel(bestand)
    df["datum"] = pd.to_datetime(df["datum"])
    df["dag"] = df["datum"].dt.date
    df["uur"] = df["datum"].dt.hour
    df["dagnaam"] = df["datum"].dt.day_name()
    df["week"] = df["datum"].dt.isocalendar().week

    # Check op vereiste kolommen
    if not {"Inkoop", "Verkoop"}.issubset(df.columns):
        st.error("❌ Bestand mist kolommen 'Inkoop' of 'Verkoop'")
        st.stop()

    # Bepaal weken waarin auto niet beschikbaar is
    alle_weken = df["week"].unique()
    weken_afwezig = random.sample(list(alle_weken), 52 - weken_actief)
    df["actief"] = ~df["week"].isin(weken_afwezig)

    # Simulatievoorbereiding
    soc = accu  # Start op 100%
    df["actie"] = "geen"
    df["geladen"] = 0.0
    df["ontladen"] = 0.0
    df["soc"] = 0.0
    df["kosten"] = 0.0
    df["opbrengst"] = 0.0

    # Simuleer per uur
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
            # Keuze op basis van prijzen
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

    # Resultaten
    totaal_opbrengst = df["opbrengst"].sum()
    totaal_kosten = df["kosten"].sum()
    totaal_winst = totaal_opbrengst - totaal_kosten

    st.subheader("📈 Resultaat")
    st.metric("Totale Winst", f"€ {totaal_winst:.2f}")
    st.metric("Totale Opbrengst", f"€ {totaal_opbrengst:.2f}")
    st.metric("Totale Kosten", f"€ {totaal_kosten:.2f}")

    st.subheader("📊 Tabelvoorbeeld")
    st.dataframe(df[["datum", "uur", "actie", "soc", "geladen", "ontladen", "kosten", "opbrengst"]].head(48))
