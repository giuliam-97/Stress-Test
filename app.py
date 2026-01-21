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
# DATA FILTERING
# =====================
df_filt = df_total[
    (df_total["Date"] == date_sel)
    & df_total["Portfolio"].isin(st.session_state.portfolio_sel)
    & df_total["Scenario"].isin(st.session_state.scenario_sel)
]

excel_data = {}

# =====================
# CHART + TABLE BY PORTFOLIO
# =====================
if df_filt.empty:
    st.warning("No data available with the selected filters")
else:
    st.subheader(f"📅 Date: {date_sel}")

    visible_portfolios = sorted(df_filt["Portfolio"].unique())

    for p in visible_portfolios:
        df_port = (
            df_filt[df_filt["Portfolio"] == p]
            .sort_values("Scenario")
        )

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
            height=450
        )

        st.plotly_chart(fig, use_container_width=True)

        df_display = df_port.rename(
            columns={
                "Stress PnL": "Stress PnL bps"
            }
        )[["Scenario", "Stress PnL bps"]]

        excel_data[p] = df_display

        output_single = BytesIO()
        with pd.ExcelWriter(output_single, engine="openpyxl") as writer:
            df_display.to_excel(writer, sheet_name=p[:31], index=False)

        st.download_button(
            label="📥 Download table as Excel",
            data=output_single.getvalue(),
            file_name=f"stress_pnl_{p}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_{p}"
        )

        st.dataframe(df_display, use_container_width=True, hide_index=True)

# =====================
# MULTI-SHEET EXCEL
# =====================
if len(excel_data) > 1:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for portfolio, df_sheet in excel_data.items():
            df_sheet.to_excel(writer, sheet_name=portfolio[:31], index=False)

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

if df_filt["Portfolio"].nunique() < 2:
    st.info("Peer analysis available only when at least two portfolios are selected.")
else:
    col1, col2 = st.columns(2)

    with col1:
        analysis_portfolio = st.selectbox(
            "⭐ Analysis portfolio",
            options=sorted(df_filt["Portfolio"].unique())
        )

    with col2:
        peer_portfolios = st.multiselect(
            "◼ Peer portfolios",
            options=[p for p in df_filt["Portfolio"].unique() if p != analysis_portfolio],
            default=[p for p in df_filt["Portfolio"].unique() if p != analysis_portfolio]
        )

    if peer_portfolios:
        df_analysis = df_filt[df_filt["Portfolio"] == analysis_portfolio][
            ["Scenario", "Stress PnL"]
        ]

        df_peers = df_filt[df_filt["Portfolio"].isin(peer_portfolios)][
            ["Scenario", "Stress PnL"]
        ]

        df_peer_stats = df_peers.groupby("Scenario", as_index=False).agg(
            peer_median=("Stress PnL", "median"),
            q25=("Stress PnL", lambda x: x.quantile(0.25)),
            q75=("Stress PnL", lambda x: x.quantile(0.75))
        )

        df_plot = df_analysis.merge(df_peer_stats, on="Scenario")

        fig = px.scatter(
            df_plot,
            x="Stress PnL",
            y="Scenario",
            title=f"Peer Analysis – {analysis_portfolio}",
        )

        for _, r in df_plot.iterrows():
            fig.add_scatter(
                x=[r["q25"], r["q75"]],
                y=[r["Scenario"], r["Scenario"]],
                mode="lines",
                line=dict(width=14, color="rgba(255,0,0,0.25)"),
                showlegend=False
            )

        fig.add_scatter(
            x=df_plot["peer_median"],
            y=df_plot["Scenario"],
            mode="markers",
            marker=dict(size=9, color="red"),
            name="Peer median"
        )

        fig.add_scatter(
            x=df_plot["Stress PnL"],
            y=df_plot["Scenario"],
            mode="markers",
            marker=dict(size=14, symbol="star", color="orange"),
            name="Analysis portfolio"
        )

        st.plotly_chart(fig, use_container_width=True)

        # =====================
        # TABLE + EXCEL
        # =====================

       
        df_table = df_plot.rename(
            columns={
                "Stress PnL": "Analysis Stress PnL",
                "peer_median": "Peer Median Stress PnL",
                "q25": "Peer Q25 Stress PnL",
                "q75": "Peer Q75 Stress PnL"
            }
        )[
            [
                "Scenario",
                "Analysis Stress PnL",
                "Peer Median Stress PnL",
                "Peer Q25 Stress PnL",
                "Peer Q75 Stress PnL"
            ]
        ]

        st.markdown(
            """
            <div style="display: flex; align-items: center;">
                <sub style="margin-right: 4px;">Note: the shaded areas</sub>
                <div style="width: 20px; height: 14px; background-color: rgba(255,0,0,0.25); margin: 0 4px 0 0; border: 1px solid rgba(0,0,0,0.1);"></div>
                <sub>represent the dispersion between the 25th and 75th percentile of the Peer median.</sub>
            </div>
            """,
            unsafe_allow_html=True
        )

        
        st.subheader("📋 Peer comparison table")
        st.dataframe(df_table, use_container_width=True, hide_index=True)

        output_peer = BytesIO()
        with pd.ExcelWriter(output_peer, engine="openpyxl") as writer:
            df_table.to_excel(writer, sheet_name="Peer Comparison", index=False)

        st.download_button(
            label="📥 Download peer comparison table as Excel",
            data=output_peer.getvalue(),
            file_name="peer_comparison_table.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

