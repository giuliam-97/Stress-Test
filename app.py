import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Stress Test Dashboard", layout="wide")
st.title("📊 Stress Test – Stress PnL Dashboard")

FILE_PATH = Path("stress_test.xlsx")

@st.cache_data
def load_excel_data(path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    all_data = []

    for sheet in xls.sheet_names:
        if "_" not in sheet:
            continue

        portfolio_sheet, scenario_sheet = sheet.split("_", 1)

        raw = pd.read_excel(xls, sheet_name=sheet)

        df = raw[
            [
                "Risk Group",
                "FTAG",
                "Stress PnL",
                "Date",
                "Portfolio",
                "Scenario"
            ]
        ].copy()

        df = df.dropna(subset=["Risk Group", "Stress PnL"])
        df = df[df["Risk Group"] != "Total"]

        df["BRS_FLAG"] = df["FTAG"].astype(str).str.startswith(("BRS", "_BRS"))

        # fallback se Portfolio / Scenario non valorizzati
        df["Portfolio"] = df["Portfolio"].fillna(portfolio_sheet)
        df["Scenario"] = df["Scenario"].fillna(scenario_sheet)

        all_data.append(df)

    return pd.concat(all_data, ignore_index=True)

df = load_excel_data(FILE_PATH)

# =====================
# FILTRI
# =====================
st.sidebar.header("🎛️ Filtri")

date_sel = st.sidebar.multiselect(
    "📅 Date",
    sorted(df["Date"].unique()),
    default=sorted(df["Date"].unique())
)

portfolio_sel = st.sidebar.multiselect(
    "💼 Portfolio",
    sorted(df["Portfolio"].unique()),
    default=sorted(df["Portfolio"].unique())
)

scenario_sel = st.sidebar.multiselect(
    "🧪 Scenario",
    sorted(df["Scenario"].unique()),
    default=sorted(df["Scenario"].unique())
)

df_filt = df[
    df["Date"].isin(date_sel)
    & df["Portfolio"].isin(portfolio_sel)
    & df["Scenario"].isin(scenario_sel)
]

# =====================
# AGGREGAZIONE
# =====================
agg = (
    df_filt
    .groupby(
        ["Date", "Portfolio", "Scenario", "BRS_FLAG"],
        as_index=False
    )["Stress PnL"]
    .sum()
)

agg["Group"] = agg["BRS_FLAG"].map(
    {True: "BRS", False: "Non-BRS"}
)

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
    title="Stress PnL aggregato (BRS vs Non-BRS)"
)

fig.update_layout(barmode="stack")
st.plotly_chart(fig, use_container_width=True)

# =====================
# TABELLA
# =====================
with st.expander("📄 Dati aggregati"):
    st.dataframe(agg, use_container_width=True)
