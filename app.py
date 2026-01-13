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
def load_excel_total(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"File non trovato: {path}")
        st.stop()

    xls = pd.ExcelFile(path)
    total_rows = []

    for sheet in xls.sheet_names:
        if "_" not in sheet:
            continue

        portfolio_sheet, scenario_sheet = sheet.split("_", 1)

        raw = pd.read_excel(xls, sheet_name=sheet)

        # Seleziono SOLO la riga Total
        df_total = raw[raw["Risk Group"] == "Total"].copy()

        if df_total.empty:
            continue

        df_total = df_total[
            ["Risk Group", "Stress PnL", "Date", "Portfolio", "Scenario"]
        ]

        # fallback se Portfolio / Scenario non compilati
        df_total["Portfolio"] = df_total["Portfolio"].fillna(portfolio_sheet)
        df_total["Scenario"] = df_total["Scenario"].fillna(scenario_sheet)

        total_rows.append(df_total)

    if not total_rows:
        st.error("Nessuna riga 'Total' trovata nei fogli Excel")
        st.stop()

    return pd.concat(total_rows, ignore_index=True)


df_total = load_excel_total(FILE_PATH)

# =====================
# FILTRI
# =====================
st.sidebar.header("🎛️ Filtri")

date_sel = st.sidebar.multiselect(
    "📅 Date",
    sorted(df_total["Date"].unique()),
    default=sorted(df_total["Date"].unique())
)

portfolio_sel = st.sidebar.multiselect(
    "💼 Portfolio",
    sorted(df_total["Portfolio"].unique()),
    default=sorted(df_total["Portfolio"].unique())
)

scenario_sel = st.sidebar.multiselect(
    "🧪 Scenario",
    sorted(df_total["Scenario"].unique()),
    default=sorted(df_total["Scenario"].unique())
)

df_filt = df_total[
    df_total["Date"].isin(date_sel)
    & df_total["Portfolio"].isin(portfolio_sel)
    & df_total["Scenario"].isin(scenario_sel)
]

# =====================
# KPI
# =====================
k1, k2 = st.columns(2)

k1.metric(
    "Totale Stress PnL",
    f"{df_filt['Stress PnL'].sum():,.0f}"
)

k2.metric(
    "Numero fogli selezionati",
    len(df_filt)
)

# =====================
# GRAFICO (SOLO TOTAL)
# =====================
fig = px.bar(
    df_filt,
    x="Scenario",
    y="Stress PnL",
    facet_col="Portfolio",
    color="Portfolio",
    hover_data=["Date"],
    title="Stress PnL – Risk Group = Total (da Excel)"
)

fig.update_layout(
    showlegend=False,
    yaxis_title="Stress PnL"
)

st.plotly_chart(fig, use_container_width=True)

# =====================
# TABELLA
# =====================
with st.expander("📄 Dettaglio righe Total"):
    st.dataframe(
        df_filt.sort_values(
            ["Date", "Portfolio", "Scenario"]
        ),
        use_container_width=True
    )
