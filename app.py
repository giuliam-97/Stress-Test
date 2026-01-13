import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Stress PnL Dashboard", layout="wide")

st.title("📊 Stress PnL Analysis")

uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx"])

@st.cache_data
def load_excel(file):
    xls = pd.ExcelFile(file)
    all_data = []

    for sheet in xls.sheet_names:
        try:
            portfolio, scenario = sheet.split("_", 1)
        except ValueError:
            continue

        df = pd.read_excel(
            xls,
            sheet_name=sheet,
            usecols="A,B,R,U"
        )

        df.columns = ["Risk Group", "Col_B", "Stress PnL", "Date"]

        df["Portfolio"] = portfolio
        df["Scenario"] = scenario

        # Rimuovo Total per ricalcolarlo
        df = df[df["Risk Group"] != "Total"]

        # Flag BRS
        df["BRS_FLAG"] = df["Col_B"].astype(str).str.startswith(("BRS", "_BRS"))

        all_data.append(df)

    return pd.concat(all_data, ignore_index=True)

if uploaded_file:
    df = load_excel(uploaded_file)

    # =====================
    # FILTRI
    # =====================
    col1, col2, col3 = st.columns(3)

    with col1:
        date_sel = st.multiselect(
            "📅 Data",
            sorted(df["Date"].dropna().unique()),
            default=sorted(df["Date"].dropna().unique())
        )

    with col2:
        portfolio_sel = st.multiselect(
            "💼 Portafoglio",
            sorted(df["Portfolio"].unique()),
            default=sorted(df["Portfolio"].unique())
        )

    with col3:
        scenario_sel = st.multiselect(
            "🧪 Scenario",
            sorted(df["Scenario"].unique()),
            default=sorted(df["Scenario"].unique())
        )

    df_filt = df[
        (df["Date"].isin(date_sel)) &
        (df["Portfolio"].isin(portfolio_sel)) &
        (df["Scenario"].isin(scenario_sel))
    ]

    # =====================
    # AGGREGAZIONE
    # =====================
    agg = (
        df_filt
        .groupby(["Date", "Portfolio", "Scenario", "BRS_FLAG"], as_index=False)
        ["Stress PnL"]
        .sum()
    )

    agg["Group"] = agg["BRS_FLAG"].map({
        True: "BRS",
        False: "Non-BRS"
    })

    # =====================
    # GRAFICO
    # =====================
    fig = px.bar(
        agg,
        x="Scenario",
        y="Stress PnL",
        color="Group",
        facet_col="Portfolio",
        hover_data=["Date"],
        title="Stress PnL Aggregato per Scenario e Portafoglio"
    )

    fig.update_layout(barmode="stack")

    st.plotly_chart(fig, use_container_width=True)

    # =====================
    # TABELLA
    # =====================
    with st.expander("📄 Dati aggregati"):
        st.dataframe(agg)

else:
    st.info("Carica un file Excel per iniziare")
