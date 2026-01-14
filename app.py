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

# 🔒 NASCONDE LA ❌ CLEAR ALL NEI MULTISELECT
st.markdown(
    """
    <style>
    div[data-baseweb="select"] span[aria-label="Clear value"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
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

        df_total = raw[raw["Risk Group"] == "Total"].copy()

        if df_total.empty:
            continue

        df_total = df_total[
            ["Risk Group", "Stress PnL", "Date", "Portfolio", "Scenario"]
        ]

        df_total["Portfolio"] = df_total["Portfolio"].fillna(portfolio_sheet)
        df_total["Scenario"] = df_total["Scenario"].fillna(scenario_sheet)

        total_rows.append(df_total)

    if not total_rows:
        st.error("Nessuna riga 'Total' trovata nei fogli Excel")
        st.stop()

    return pd.concat(total_rows, ignore_index=True)


df_total = load_excel_total(FILE_PATH)

# =====================
# PREPARAZIONE DATE
# =====================
df_total["Date"] = pd.to_datetime(df_total["Date"]).dt.date

available_dates = sorted(df_total["Date"].unique())
last_date = max(available_dates)

all_portfolios = sorted(df_total["Portfolio"].unique())
all_scenarios = sorted(df_total["Scenario"].unique())

# =====================
# SESSION STATE INIT
# =====================
if "portfolio_all" not in st.session_state:
    st.session_state.portfolio_all = True
if "scenario_all" not in st.session_state:
    st.session_state.scenario_all = True
if "portfolio_sel" not in st.session_state:
    st.session_state.portfolio_sel = all_portfolios.copy()
if "scenario_sel" not in st.session_state:
    st.session_state.scenario_sel = all_scenarios.copy()

# =====================
# CALLBACK
# =====================
def toggle_portfolio_all():
    st.session_state.portfolio_sel = (
        all_portfolios.copy() if st.session_state.portfolio_all else []
    )

def toggle_scenario_all():
    st.session_state.scenario_sel = (
        all_scenarios.copy() if st.session_state.scenario_all else []
    )

# =====================
# FILTRI
# =====================
st.sidebar.header("🎛️ Filtri")

date_sel = st.sidebar.date_input(
    "📅 Date",
    value=last_date,
    min_value=min(available_dates),
    max_value=max(available_dates)
)

st.sidebar.multiselect(
    "💼 Portfolio",
    options=all_portfolios,
    key="portfolio_sel"
)
st.sidebar.checkbox(
    "Select all portfolio",
    key="portfolio_all",
    on_change=toggle_portfolio_all
)

st.sidebar.multiselect(
    "🧪 Scenario",
    options=all_scenarios,
    key="scenario_sel"
)
st.sidebar.checkbox(
    "Select all scenario",
    key="scenario_all",
    on_change=toggle_scenario_all
)

# =====================
# FILTRO DATAFRAME
# =====================
df_filt = df_total[
    (df_total["Date"] == date_sel)
    & df_total["Portfolio"].isin(st.session_state.portfolio_sel)
    & df_total["Scenario"].isin(st.session_state.scenario_sel)
]

# =====================
# GRAFICI (UNO SOTTO L'ALTRO)
# =====================
if df_filt.empty:
    st.warning("Nessun dato disponibile con i filtri selezionati")
else:
    st.subheader(f"📅 Data: {date_sel}")

    portfolios = sorted(df_filt["Portfolio"].unique())

    for p in portfolios:
        df_plot = df_filt[df_filt["Portfolio"] == p]

        fig = px.bar(
            df_plot,
            x="Scenario",
            y="Stress PnL",
            title=f"Portfolio {p}",
        )

        fig.update_layout(
            showlegend=False,
            xaxis_title="Scenario",
            yaxis_title="Stress PnL",
            height=500,  # più alto per visione orizzontale
            margin=dict(l=40, r=40, t=60, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)

# =====================
# TABELLA
# =====================
with st.expander("📄 Dettaglio granulare dello Stress PnL"):
    st.dataframe(
        df_filt.sort_values(
            ["Date", "Portfolio", "Scenario"]
        ),
        use_container_width=True
    )
