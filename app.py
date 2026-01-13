import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# =====================
# CONFIG
# =====================
st.set_page_config(
    page_title="Stress Test Dashboard",
    layout="wide"
)

st.title("📊 Stress Test – Stress PnL Dashboard")

FILE_PATH = Path("stress_test.xlsx")

# =====================
# LOAD DATA
# =====================
@st.cache_data
def load_excel_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"File non trovato: {path}")
        st.stop()

    xls = pd.ExcelFile(path)
    all_data = []

    for sheet in xls.sheet_names:

        # Split nome foglio → Portfolio / Scenario
        try:
            portfolio, scenario = sheet.split("_", 1)
        except ValueError:
            # Skip fogli non conformi
            continue

        df = pd.read_excel(
            xls,
            sheet_name=sheet,
            usecols="A,B,R,U"
        )

        df.columns = [
            "Risk Group",
            "Col_B",
            "Stress PnL",
            "Date"
        ]

        df["Portfolio"] = portfolio
        df["Scenario"] = scenario

        # Rimuovo Total (verrà ricalcolato)
        df = df[df["Risk Group"] != "Total"]

        # Flag BRS
        df["BRS_FLAG"] = (
            df["Col_B"]
            .astype(str)
            .str.startswith(("BRS", "_BRS"))
        )

        all_data.append(df)

    if not all_data:
        st.error("Nessun foglio valido trovato nel file Excel")
        st.stop()

    return pd.concat(all_data, ignore_index=True)


df = load_excel_data(FILE_PATH)

# =====================
# FILTRI
# =====================
st.sidebar.header("🎛️ Filtri")

date_sel = st.sidebar.multiselect(
    "📅 Data di analisi",
    sorted(df["Date"].dropna().unique()),
    default=sorted(df["Date"].dropna().unique())
)

portfolio_sel = st.sidebar.multiselect(
    "💼 Portafoglio",
    sorted(df["Portfolio"].unique()),
    default=sorted(df["Portfolio"].unique())
)

scenario_sel = st.sidebar.multiselect(
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
agg_df = (
    df_filt
    .groupby(
        ["Date", "Portfolio", "Scenario", "BRS_FLAG"],
        as_index=False
    )["Stress PnL"]
    .sum()
)

agg_df["Aggregation Group"] = agg_df["BRS_FLAG"].map(
    {True: "BRS", False: "Non-BRS"}
)

# =====================
# KPI
# =====================
kpi1, kpi2 = st.columns(2)

with kpi1:
    st.metric(
        "Totale Stress PnL",
        f"{agg_df['Stress PnL'].sum():,.0f}"
    )

with kpi2:
    st.metric(
        "Totale BRS",
        f"{agg_df.loc[agg_df['Aggregation Group']=='BRS','Stress PnL'].sum():,.0f}"
    )

# =====================
# GRAFICO
# =====================
fig = px.bar(
    agg_df,
    x="Scenario",
    y="Stress PnL",
    color="Aggregation Group",
    facet_col="Portfolio",
    hover_data=["Date"],
    title="Stress PnL Aggregato per Scenario e Portafoglio"
)

fig.update_layout(
    barmode="stack",
    legend_title_text="Tipo Aggregazione"
)

st.plotly_chart(fig, use_container_width=True)

# =====================
# TABELLA DETTAGLIO
# =====================
with st.expander("📄 Dati aggregati di dettaglio"):
    st.dataframe(
        agg_df.sort_values(
            ["Date", "Portfolio", "Scenario"]
        ),
        use_container_width=True
    )
