import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from io import BytesIO

# =====================
# CONFIGURATION
# =====================
st.set_page_config(
    page_title="Stress Test Dashboard",
    layout="wide"
)

# Hide ❌ in multiselect widgets
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
        st.error(f"File not found: {path}")
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
        st.error("No 'Total' rows found in Excel sheets")
        st.stop()

    return pd.concat(total_rows, ignore_index=True)


df_total = load_excel_total(FILE_PATH)

# =====================
# DATE PREPARATION
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
# CALLBACKS
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
# FILTERS
# =====================
st.sidebar.header("🎛️ Filters")

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
    "Select all portfolios",
    key="portfolio_all",
    on_change=toggle_portfolio_all
)

st.sidebar.multiselect(
    "🧪 Scenario",
    options=all_scenarios,
    key="scenario_sel"
)
st.sidebar.checkbox(
    "Select all scenarios",
    key="scenario_all",
    on_change=toggle_scenario_all
)

# =====================
# DATAFRAME FILTERING
# =====================
df_filt = df_total[
    (df_total["Date"] == date_sel)
    & df_total["Portfolio"].isin(st.session_state.portfolio_sel)
    & df_total["Scenario"].isin(st.session_state.scenario_sel)
]

# =====================
# INIT VARIABLES (AVOID ERRORS IF df_filt IS EMPTY)
# =====================
excel_data = {}
show_full_excel = False

# =====================
# CHART + TABLE BY PORTFOLIO
# =====================
if df_filt.empty:
    st.warning("No data available with the selected filters")
else:
    st.subheader(f"📅 Date: {date_sel}")

    visible_portfolios = sorted(df_filt["Portfolio"].unique())
    show_full_excel = len(visible_portfolios) > 1

    for p in visible_portfolios:
        df_port = (
            df_filt[df_filt["Portfolio"] == p]
            .sort_values("Scenario")
            .copy()
        )

        # ---- CHART ----
        fig = px.bar(
            df_port,
            x="Scenario",
            y="Stress PnL",
            title=f"Portfolio {p}",
        )

        fig.update_layout(
            showlegend=False,
            xaxis_title="Scenario",
            yaxis_title="Stress PnL (bps)",
            height=450,
            margin=dict(l=40, r=40, t=60, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)

        # ---- RENAME COLUMNS (UI + EXCEL) ----
        df_display = df_port.rename(
            columns={
                "Scenario": "Scenario",
                "Stress PnL": "Stress PnL bps (click here to order)"
            }
        )[["Scenario", "Stress PnL bps (click here to order)"]]

        # ---- SINGLE PORTFOLIO EXCEL DOWNLOAD ----
        output_single = BytesIO()
        with pd.ExcelWriter(output_single, engine="openpyxl") as writer:
            df_display.to_excel(
                writer,
                sheet_name=p[:31],
                index=False
            )

        st.download_button(
            label="📥 Download table as Excel",
            data=output_single.getvalue(),
            file_name=f"stress_pnl_{p}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_{p}"
        )

        excel_data[p] = df_display

        # ---- TABLE ----
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )

# =====================
# MULTI-SHEET EXCEL DOWNLOAD
# =====================
if excel_data and show_full_excel:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for portfolio, df_sheet in excel_data.items():
            df_sheet.to_excel(
                writer,
                sheet_name=portfolio[:31],
                index=False
            )

    st.download_button(
        label="📥 Download all tables as Excel",
        data=output.getvalue(),
        file_name="stress_pnl_per_portfolio.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =====================
# PEER ANALYSIS
# =====================
st.markdown("---")
st.header("⭐ Peer Analysis")

# La peer analysis ha senso solo con almeno 2 portafogli
if df_filt["Portfolio"].nunique() < 2:
    st.info("Peer analysis available only when at least two portfolios are selected.")
else:
    # ---- CONTROLS ----
    col1, col2 = st.columns(2)

    with col1:
        analysis_portfolio = st.selectbox(
            "⭐ Analysis portfolio",
            options=sorted(df_filt["Portfolio"].unique())
        )

    with col2:
        peer_portfolios = st.multiselect(
            "◼ Peer portfolios",
            options=[
                p for p in sorted(df_filt["Portfolio"].unique())
                if p != analysis_portfolio
            ],
            default=[
                p for p in sorted(df_filt["Portfolio"].unique())
                if p != analysis_portfolio
            ]
        )

    if not peer_portfolios:
        st.warning("Select at least one peer portfolio.")
    else:
        # =====================
        # DATA PREPARATION
        # =====================

        # Analysis portfolio (puntuale)
        df_analysis = df_filt[
            df_filt["Portfolio"] == analysis_portfolio
        ][["Scenario", "Stress PnL"]]

        # Peer portfolios (puntuali)
        df_peers = df_filt[
            df_filt["Portfolio"].isin(peer_portfolios)
        ][["Scenario", "Stress PnL"]]

        # Peer median + dispersion (std)
        df_peer_stats = (
            df_peers
            .groupby("Scenario", as_index=False)
            .agg(
                peer_median=("Stress PnL", "median"),
                peer_std=("Stress PnL", "std")
            )
        )

        # Merge
        df_plot = df_analysis.merge(
            df_peer_stats,
            on="Scenario",
            how="inner"
        )

        # Z-score
        df_plot["z_score"] = (
            (df_plot["Stress PnL"] - df_plot["peer_median"])
            / df_plot["peer_std"]
        )

        df_plot = df_plot.sort_values("Scenario")

        # =====================
        # PLOT
        # =====================
        fig = px.scatter(
            df_plot,
            x="Scenario",
            y="Stress PnL",
            title=f"Peer Analysis – {analysis_portfolio}",
            labels={"Stress PnL": "Stress PnL (bps)"}
        )

        # ⭐ Analysis portfolio
        fig.add_scatter(
            x=df_plot["Scenario"],
            y=df_plot["Stress PnL"],
            mode="markers",
            marker=dict(size=14, symbol="star"),
            name="Analysis portfolio"
        )

        # ▬ Peer median line
        fig.add_scatter(
            x=df_plot["Scenario"],
            y=df_plot["peer_median"],
            mode="lines+markers",
            line=dict(dash="dash"),
            name="Peer median"
        )

        fig.update_layout(
            height=500,
            xaxis_title="Scenario",
            yaxis_title="Stress PnL (bps)",
            legend_title_text=""
        )

        st.plotly_chart(fig, use_container_width=True)

        # =====================
        # TABLE (OPTIONAL)
        # =====================
        st.subheader("📋 Peer comparison table")

        df_table = df_plot.rename(
            columns={
                "Stress PnL": "Analysis Stress PnL",
                "peer_median": "Peer Median Stress PnL",
                "z_score": "Z-score vs peers"
            }
        )[
            ["Scenario", "Analysis Stress PnL", "Peer Median Stress PnL", "Z-score vs peers"]
        ]

        st.dataframe(
            df_table,
            use_container_width=True,
            hide_index=True
        )

