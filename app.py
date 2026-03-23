"""
NHS England — 28-Day Faster Diagnosis Standard Dashboard
Colorectal Cancer (Suspected Lower Gastrointestinal)
Oct 2024 – Sep 2025
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NHS CRC 28-Day FDS Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── COLOURS ───────────────────────────────────────────────────────────────────
C_DARK_BLUE  = "#003087"
C_BLUE       = "#005EB8"
C_LIGHT_BLUE = "#41B6E6"
C_GREEN      = "#009639"
C_RED        = "#DA291C"
C_YELLOW     = "#FFB81C"
C_GREY       = "#425563"
C_LIGHT_GREY = "#E8EDEE"

FDS_TARGET   = 0.75

# MONTH_ORDER is derived dynamically from loaded data — see below

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* Page padding */
  .block-container {{ padding-top: 4.5rem; padding-bottom: 2rem; }}

  /* KPI cards */
  .kpi-card {{
    background: {C_BLUE};
    color: white;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    min-height: 110px;
  }}
  .kpi-card .kpi-label {{
    font-size: 0.75rem;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    opacity: 0.85;
    margin-bottom: 0.4rem;
  }}
  .kpi-card .kpi-value {{
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.1;
  }}
  .kpi-card .kpi-delta {{
    font-size: 0.8rem;
    margin-top: 0.4rem;
  }}

  /* Page header */
  .nhs-header {{
    background: linear-gradient(135deg, {C_DARK_BLUE} 0%, {C_BLUE} 100%);
    color: white;
    padding: 1.25rem 1.75rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
  }}

  /* Sidebar */
  div[data-testid="stSidebar"] {{
    min-width: 220px !important;
    max-width: 220px !important;
  }}
  div[data-testid="stSidebar"] > div:first-child {{
    background: {C_DARK_BLUE};
  }}
  div[data-testid="stSidebar"] label,
  div[data-testid="stSidebar"] p,
  div[data-testid="stSidebar"] span,
  div[data-testid="stSidebar"] div,
  div[data-testid="stSidebar"] h1,
  div[data-testid="stSidebar"] h2,
  div[data-testid="stSidebar"] h3 {{
    color: white !important;
  }}

  /* Section headers */
  h4 {{ color: {C_DARK_BLUE}; }}
</style>
""", unsafe_allow_html=True)


# ── DATA LOADING ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent


@st.cache_data(show_spinner="Loading NHS Cancer Waiting Times data…")
def load_data() -> pd.DataFrame:
    """Parse all Excel workbooks and return a combined CRC FDS dataframe."""
    records = []

    for fp in sorted(DATA_DIR.glob("*.xlsx")):
        stem = fp.stem.upper()
        if "COMMISSIONER" in stem:
            vtype = "Commissioner"
        elif "PROVIDER" in stem:
            vtype = "Provider"
        else:
            continue

        try:
            raw = pd.read_excel(
                fp,
                sheet_name="28-DAY FDS (BY ROUTE)",
                header=None,
                engine="openpyxl",
            )
        except Exception:
            continue

        month = str(raw.iloc[1, 0]).strip()   # e.g. "Oct-24"
        rows = raw.iloc[9:].reset_index(drop=True)
        rows.columns = range(rows.shape[1])

        # Column layout (0-indexed):
        # 0=blank  1=ODS  2=org_name  3=referral_route  4=cancer_type
        # 5=total  6=within_28  7=after_28  8=pct_28  9=separator
        # 10=w14  11=d15_28  12=d29_42  13=d43_62  14=d63plus

        # Filter to colorectal cancer only
        crc = rows[rows[4] == "Suspected lower gastrointestinal cancer"].copy()

        # Drop blank / national-total rows
        crc = crc[crc[1].notna()]
        crc = crc[
            ~crc[2]
            .astype(str)
            .str.contains(r"ALL ENGLISH|NATIONAL TOTAL", na=False, regex=True, case=False)
        ]

        def n(r, col):
            return pd.to_numeric(r[col], errors="coerce") if col < len(r) else float("nan")

        for _, r in crc.iterrows():
            records.append(
                dict(
                    month=month,
                    view_type=vtype,
                    ods_code=str(r[1]).strip(),
                    org_name=str(r[2]).strip(),
                    referral_route=str(r[3]).strip(),
                    total=n(r, 5),
                    within_28=n(r, 6),
                    after_28=n(r, 7),
                    pct_28=n(r, 8),
                    w14=n(r, 10),
                    d15_28=n(r, 11),
                    d29_42=n(r, 12),
                    d43_62=n(r, 13),
                    d63plus=n(r, 14),
                )
            )

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df["_sort"] = pd.to_datetime(df["month"], format="%b-%y")
    df = df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    return df


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"<div style='font-size:1.6rem;font-weight:700;color:white;letter-spacing:1px;'>"
        f"NHS England</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='color:#41B6E6;font-size:0.9rem;margin-bottom:1rem;'>"
        "28-Day FDS Dashboard</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    view = st.radio(
        "Perspective",
        options=["Provider", "Commissioner"],
        index=0,
        help="Switch between NHS Trust (Provider) and ICB (Commissioner) views.",
    )

    st.divider()
    st.markdown(
        "<div style='font-size:0.8rem;opacity:0.85;line-height:1.6;'>"
        "<b>Cancer type:</b> Colorectal (Lower GI)<br>"
        "<b>Data:</b> NHS England CWT<br>"
        f"<b>Period:</b> {DATE_RANGE}<br>"
        "<b>Target:</b> ≥ 75% within 28 days"
        "</div>",
        unsafe_allow_html=True,
    )


# ── LOAD DATA ─────────────────────────────────────────────────────────────────
df_all = load_data()

if df_all.empty:
    st.error(
        "No data could be loaded. "
        "Make sure the NHS Excel files are in the same folder as app.py."
    )
    st.stop()

# Derive chronological month order from whatever files are present
MONTH_ORDER = sorted(
    df_all["month"].unique(),
    key=lambda m: pd.to_datetime(m, format="%b-%y"),
)
df_all["month"] = pd.Categorical(df_all["month"], categories=MONTH_ORDER, ordered=True)
df_all = df_all.sort_values("month").reset_index(drop=True)

DATE_RANGE = f"{MONTH_ORDER[0]} – {MONTH_ORDER[-1]}"

df = df_all[df_all["view_type"] == view].copy()   # raw: one row per org per route per month
org_label = "Provider" if view == "Provider" else "ICB / Commissioning Hub"

# Aggregated across routes — used for KPIs, national trend, breakdown, and table
_count_cols = ["total", "within_28", "after_28", "w14", "d15_28", "d29_42", "d43_62", "d63plus"]
df_agg = (
    df.groupby(["month", "view_type", "ods_code", "org_name"], observed=True)[_count_cols]
    .sum()
    .reset_index()
)
df_agg["pct_28"] = df_agg["within_28"] / df_agg["total"]
df_agg["month"] = pd.Categorical(df_agg["month"], categories=MONTH_ORDER, ordered=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="nhs-header">
      <div style="font-size:1.5rem;font-weight:700;">
        NHS England &nbsp;—&nbsp; 28-Day Faster Diagnosis Standard
      </div>
      <div style="opacity:0.85;margin-top:0.3rem;">
        Colorectal Cancer (Suspected Lower Gastrointestinal) &nbsp;·&nbsp;
        {view} View &nbsp;·&nbsp; {DATE_RANGE}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── NATIONAL AGGREGATES PER MONTH ─────────────────────────────────────────────
nat = (
    df_agg.groupby("month", observed=True)
    .agg(total=("total", "sum"), within_28=("within_28", "sum"))
    .reset_index()
)
nat["pct_28"] = nat["within_28"] / nat["total"]

# National aggregates split by referral route — used across multiple sections
nat_by_route = (
    df.groupby(["month", "referral_route"], observed=True)
    .agg(total=("total", "sum"), within_28=("within_28", "sum"))
    .reset_index()
)
nat_by_route["pct_28"] = nat_by_route["within_28"] / nat_by_route["total"]
nat_by_route["month"] = pd.Categorical(nat_by_route["month"], categories=MONTH_ORDER, ordered=True)
nat_by_route = nat_by_route.sort_values("month")

nat_usc = nat_by_route[nat_by_route["referral_route"] == "URGENT SUSPECTED CANCER"]
nat_nsp = nat_by_route[nat_by_route["referral_route"] == "NATIONAL SCREENING PROGRAMME"]

latest_month = nat["month"].max()
latest_row   = nat[nat["month"] == latest_month].iloc[0]

prev_months  = nat[nat["month"] < latest_month]
prev_row     = prev_months.iloc[-1] if not prev_months.empty else None

latest_pct   = latest_row["pct_28"]
latest_total = int(latest_row["total"])
latest_w28   = int(latest_row["within_28"])
delta_pct    = (latest_pct - prev_row["pct_28"]) if prev_row is not None else None

df_latest    = df_agg[df_agg["month"] == latest_month]
n_orgs       = df_latest["org_name"].nunique()
n_meeting    = df_latest[df_latest["pct_28"] >= FDS_TARGET]["org_name"].nunique()


# ── HELPER: KPI CARD ──────────────────────────────────────────────────────────
def kpi_card(label: str, value: str, delta: float | None = None, good_up: bool = True):
    delta_html = ""
    if delta is not None:
        good  = (delta >= 0 and good_up) or (delta < 0 and not good_up)
        color = C_GREEN if good else C_RED
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = (
            f'<div class="kpi-delta" style="color:{color};">'
            f'{arrow} {abs(delta):.1%} vs prior month</div>'
        )
    return (
        f'<div class="kpi-card">'
        f'  <div class="kpi-label">{label}</div>'
        f'  <div class="kpi-value">{value}</div>'
        f'  {delta_html}'
        f'</div>'
    )


# ── KPI ROW ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    kpi_card(f"28-Day FDS %  ({latest_month})", f"{latest_pct:.1%}", delta_pct),
    unsafe_allow_html=True,
)
c2.markdown(
    kpi_card(f"Patients seen  ({latest_month})", f"{latest_total:,}"),
    unsafe_allow_html=True,
)
c3.markdown(
    kpi_card(f"Within 28 days  ({latest_month})", f"{latest_w28:,}"),
    unsafe_allow_html=True,
)
c4.markdown(
    kpi_card(f"Meeting 75% target  ({latest_month})", f"{n_meeting} / {n_orgs}"),
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)


# ── TREND + VOLUME ────────────────────────────────────────────────────────────
left, right = st.columns([3, 2])

with left:
    st.markdown(f"#### National Trend — CRC 28-Day FDS % ({view}-based)")

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=nat["month"].astype(str), y=nat["pct_28"],
        mode="lines+markers", name="Combined",
        line=dict(color=C_BLUE, width=3),
        marker=dict(size=9, color=C_BLUE, line=dict(color="white", width=2)),
        hovertemplate="<b>%{x}</b> Combined<br>%{y:.1%}<extra></extra>",
    ))
    fig_trend.add_trace(go.Scatter(
        x=nat_usc["month"].astype(str), y=nat_usc["pct_28"],
        mode="lines+markers", name="Urgent Suspected Cancer",
        line=dict(color=C_DARK_BLUE, width=2, dash="dash"),
        marker=dict(size=7, color=C_DARK_BLUE),
        hovertemplate="<b>%{x}</b> Urgent Suspected Cancer<br>%{y:.1%}<extra></extra>",
    ))
    fig_trend.add_trace(go.Scatter(
        x=nat_nsp["month"].astype(str), y=nat_nsp["pct_28"],
        mode="lines+markers", name="National Screening Programme",
        line=dict(color=C_LIGHT_BLUE, width=2, dash="dot"),
        marker=dict(size=7, color=C_LIGHT_BLUE),
        hovertemplate="<b>%{x}</b> National Screening Programme<br>%{y:.1%}<extra></extra>",
    ))
    fig_trend.add_hline(
        y=FDS_TARGET, line_dash="dash", line_color=C_RED, line_width=2,
        annotation_text="75% Target", annotation_position="top left",
        annotation_font_color=C_RED, annotation_font_size=12,
    )
    fig_trend.update_layout(
        height=320,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=20, t=10, b=10),
        yaxis=dict(tickformat=".0%", range=[0.4, 1.0], gridcolor=C_LIGHT_GREY, title=None),
        xaxis=dict(gridcolor=C_LIGHT_GREY, title=None),
        legend=dict(orientation="h", y=-0.25, font=dict(size=11)),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with right:
    st.markdown("#### Monthly Patient Volume by Route")

    fig_vol = go.Figure()
    fig_vol.add_trace(go.Bar(
        x=nat_usc["month"].astype(str), y=nat_usc["total"],
        name="Urgent Suspected Cancer",
        marker_color=C_DARK_BLUE,
        hovertemplate="<b>%{x}</b> Urgent Suspected Cancer<br>%{y:,} patients<extra></extra>",
    ))
    fig_vol.add_trace(go.Bar(
        x=nat_nsp["month"].astype(str), y=nat_nsp["total"],
        name="National Screening Programme",
        marker_color=C_LIGHT_BLUE,
        hovertemplate="<b>%{x}</b> National Screening Programme<br>%{y:,} patients<extra></extra>",
    ))
    fig_vol.update_layout(
        height=320,
        barmode="stack",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(gridcolor=C_LIGHT_GREY, title=None),
        xaxis=dict(title=None),
        legend=dict(orientation="h", y=-0.25, font=dict(size=11)),
    )
    st.plotly_chart(fig_vol, use_container_width=True)




# ── PERFORMANCE DISTRIBUTION HISTOGRAM ───────────────────────────────────────
st.divider()
st.markdown(f"#### Performance Distribution Across {org_label}s")

hist_col, hist_ctrl = st.columns([5, 1])
with hist_ctrl:
    hist_month_options = [m for m in MONTH_ORDER if m in df_agg["month"].astype(str).values]
    hist_month = st.select_slider(
        "Month",
        options=hist_month_options,
        value=hist_month_options[-1],
        key="hist_month_slider",
    )
    hist_route = st.radio(
        "Route",
        options=["Combined", "Urgent Suspected Cancer", "National Screening Programme"],
        index=0,
        key="hist_route_radio",
    )

HIST_ROUTE_MAP = {
    "Combined":                     df_agg,
    "Urgent Suspected Cancer":      df[df["referral_route"] == "URGENT SUSPECTED CANCER"],
    "National Screening Programme": df[df["referral_route"] == "NATIONAL SCREENING PROGRAMME"],
}

df_hist = (
    HIST_ROUTE_MAP[hist_route][lambda d: d["month"].astype(str) == hist_month]
    .dropna(subset=["pct_28"])
    .query("total > 0")
)

with hist_col:
    # Pre-compute bins with exact 5% boundaries
    import numpy as np
    bin_edges = np.arange(0, 1.051, 0.05)
    bin_labels = [f"{bin_edges[i]:.0%}–{bin_edges[i+1]:.0%}" for i in range(len(bin_edges) - 1)]
    counts = (
        pd.cut(df_hist["pct_28"], bins=bin_edges, include_lowest=True, right=False, labels=False)
        .value_counts()
        .reindex(range(len(bin_edges) - 1), fill_value=0)
        .sort_index()
    )
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Bar(
        x=bin_centers,
        y=counts.values,
        width=0.048,
        marker_color=C_BLUE,
        marker_line=dict(color="white", width=1),
        customdata=bin_labels,
        hovertemplate="%{customdata}<br>Organisations: %{y}<extra></extra>",
    ))
    fig_hist.add_vline(
        x=FDS_TARGET,
        line_dash="dash",
        line_color=C_RED,
        line_width=2,
        annotation_text="Target 75%",
        annotation_position="top right",
        annotation_font_color=C_RED,
    )
    fig_hist.update_layout(
        height=360,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            tickformat=".0%",
            range=[0, 1],
            title="% within 28 days",
            gridcolor=C_LIGHT_GREY,
        ),
        yaxis=dict(
            title="Number of organisations",
            gridcolor=C_LIGHT_GREY,
        ),
        bargap=0.05,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ── PROVIDER TREND DRILL-DOWN ─────────────────────────────────────────────────
st.divider()
st.markdown(f"#### {org_label} Trend Over Time")

# Route display names and raw values as they appear in the data
ROUTE_STYLES = {
    "Combined":                     {"raw": None,                           "dash": "solid"},
    "Urgent Suspected Cancer":      {"raw": "URGENT SUSPECTED CANCER",      "dash": "dash"},
    "National Screening Programme": {"raw": "NATIONAL SCREENING PROGRAMME", "dash": "dot"},
}

col_orgs, col_routes = st.columns([3, 1])
with col_orgs:
    all_orgs = sorted(df_agg["org_name"].dropna().unique())
    selected_orgs = st.multiselect(
        f"Select {org_label.lower()}s to compare",
        options=all_orgs,
        default=[],
        help="Choose one or more organisations to plot their 28-day FDS % over time.",
    )
with col_routes:
    selected_routes = st.multiselect(
        "Show by route",
        options=list(ROUTE_STYLES.keys()),
        default=["Combined"],
        help="Break down by referral route. Line style: solid = Combined, dashed = USC, dotted = NSP.",
    )

if not selected_routes:
    selected_routes = ["Combined"]

# Plotly colour sequence for selected orgs
org_colors = px.colors.qualitative.Plotly

fig_drill = go.Figure()
multi_route = len(selected_routes) > 1

for route_name in selected_routes:
    style = ROUTE_STYLES[route_name]
    route_suffix = f" — {route_name}" if multi_route else ""

    # National line for this route
    if route_name == "Combined":
        x_nat, y_nat = nat["month"].astype(str), nat["pct_28"]
    else:
        rd = nat_by_route[nat_by_route["referral_route"] == style["raw"]]
        x_nat, y_nat = rd["month"].astype(str), rd["pct_28"]

    fig_drill.add_trace(go.Scatter(
        x=x_nat, y=y_nat,
        mode="lines+markers",
        name=f"National (England){route_suffix}",
        line=dict(color=C_BLUE, width=3, dash=style["dash"]),
        marker=dict(size=8, color=C_BLUE, line=dict(color="white", width=2)),
        hovertemplate=f"<b>National (England){route_suffix}</b><br>%{{x}}: %{{y:.1%}}<extra></extra>",
    ))

    # One line per selected org for this route
    for i, org in enumerate(selected_orgs):
        color = org_colors[i % len(org_colors)]
        if route_name == "Combined":
            org_data = df_agg[df_agg["org_name"] == org].sort_values("month")
        else:
            org_data = (
                df[(df["org_name"] == org) & (df["referral_route"] == style["raw"])]
                .sort_values("month")
            )
        if org_data.empty:
            continue
        fig_drill.add_trace(go.Scatter(
            x=org_data["month"].astype(str),
            y=org_data["pct_28"],
            mode="lines+markers",
            name=f"{org}{route_suffix}",
            line=dict(color=color, width=2, dash=style["dash"]),
            marker=dict(size=7, color=color),
            hovertemplate=f"<b>{org}{route_suffix}</b><br>%{{x}}: %{{y:.1%}}<extra></extra>",
        ))

fig_drill.add_hline(
    y=FDS_TARGET,
    line_dash="dash",
    line_color=C_RED,
    line_width=2,
    annotation_text="75% Target",
    annotation_position="top left",
    annotation_font_color=C_RED,
)
fig_drill.update_layout(
    height=400,
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=10, r=20, t=10, b=10),
    yaxis=dict(tickformat=".0%", range=[0, 1.05], gridcolor=C_LIGHT_GREY, title=None),
    xaxis=dict(gridcolor=C_LIGHT_GREY, title=None),
    legend=dict(orientation="h", y=-0.25, font=dict(size=10)),
)
st.plotly_chart(fig_drill, use_container_width=True)


# ── WAITING TIME BREAKDOWN ─────────────────────────────────────────────────────
st.divider()

# ── INDIVIDUAL PROVIDER / COMMISSIONER ANALYSIS ───────────────────────────────
all_orgs_individual = sorted(df_agg["org_name"].dropna().unique())
sel_col, month_col = st.columns([3, 1])

with sel_col:
    selected_org = st.selectbox(
        f"Select {org_label.lower()}",
        options=all_orgs_individual,
        index=0,
    )
with month_col:
    month_options = [m for m in MONTH_ORDER if m in df_agg["month"].astype(str).values]
    selected_month = st.select_slider(
        "Select month",
        options=month_options,
        value=month_options[-1],
        key="org_month_slider",
    )

# Data for selected org (all months) and selected month
df_org_all  = df_agg[df_agg["org_name"] == selected_org].sort_values("month")
df_org_month = df_org_all[df_org_all["month"].astype(str) == selected_month]
df_nat_month = nat[nat["month"].astype(str) == selected_month]

org_has_data = not df_org_month.empty and df_org_month["total"].iloc[0] > 0

st.markdown(f"#### {selected_org} — {selected_month}")

# ── KPI cards for selected org vs national ────────────────────────────────────
if org_has_data:
    o = df_org_month.iloc[0]
    n_row = df_nat_month.iloc[0] if not df_nat_month.empty else None

    org_pct   = o["pct_28"]
    nat_pct   = n_row["pct_28"] if n_row is not None else None
    diff      = (org_pct - nat_pct) if nat_pct is not None else None

    ka, kb, kc, kd = st.columns(4)
    ka.markdown(
        kpi_card("28-Day FDS %", f"{org_pct:.1%}", delta=diff, good_up=True),
        unsafe_allow_html=True,
    )
    kb.markdown(
        kpi_card("Total patients", f"{int(o['total']):,}"),
        unsafe_allow_html=True,
    )
    kc.markdown(
        kpi_card("Within 28 days", f"{int(o['within_28']):,}"),
        unsafe_allow_html=True,
    )
    kd.markdown(
        kpi_card("After 28 days", f"{int(o['after_28']):,}"),
        unsafe_allow_html=True,
    )
    if diff is not None:
        st.caption(f"Delta shown vs national average ({nat_pct:.1%}) for {selected_month}.")
else:
    st.info(f"No data available for {selected_org} in {selected_month}.")

st.markdown("<br>", unsafe_allow_html=True)

# ── Trend + waiting time breakdown side by side ───────────────────────────────
left_org, right_org = st.columns([3, 2])

with left_org:
    st.markdown("**12-Month Trend vs National**")

    df_org_usc = df[(df["org_name"] == selected_org) & (df["referral_route"] == "URGENT SUSPECTED CANCER")].sort_values("month")
    df_org_nsp = df[(df["org_name"] == selected_org) & (df["referral_route"] == "NATIONAL SCREENING PROGRAMME")].sort_values("month")

    fig_org_trend = go.Figure()
    # Org lines
    fig_org_trend.add_trace(go.Scatter(
        x=df_org_all["month"].astype(str), y=df_org_all["pct_28"],
        mode="lines+markers", name="Combined",
        line=dict(color=C_BLUE, width=2),
        marker=dict(size=7, color=C_BLUE),
        hovertemplate="%{x} Combined: %{y:.1%}<extra></extra>",
    ))
    if not df_org_usc.empty:
        fig_org_trend.add_trace(go.Scatter(
            x=df_org_usc["month"].astype(str), y=df_org_usc["pct_28"],
            mode="lines+markers", name="Urgent Suspected Cancer",
            line=dict(color=C_DARK_BLUE, width=2, dash="dash"),
            marker=dict(size=6, color=C_DARK_BLUE),
            hovertemplate="%{x} Urgent Suspected Cancer: %{y:.1%}<extra></extra>",
        ))
    if not df_org_nsp.empty:
        fig_org_trend.add_trace(go.Scatter(
            x=df_org_nsp["month"].astype(str), y=df_org_nsp["pct_28"],
            mode="lines+markers", name="National Screening Programme",
            line=dict(color=C_LIGHT_BLUE, width=2, dash="dot"),
            marker=dict(size=6, color=C_LIGHT_BLUE),
            hovertemplate="%{x} National Screening Programme: %{y:.1%}<extra></extra>",
        ))
    # National benchmark (combined only, for reference)
    fig_org_trend.add_trace(go.Scatter(
        x=nat["month"].astype(str), y=nat["pct_28"],
        mode="lines+markers", name="National (England)",
        line=dict(color=C_GREY, width=2, dash="dash"),
        marker=dict(size=6, color=C_GREY),
        hovertemplate="%{x} National: %{y:.1%}<extra></extra>",
    ))
    fig_org_trend.add_hline(
        y=FDS_TARGET, line_dash="dash", line_color=C_RED, line_width=1.5,
        annotation_text="75% Target", annotation_position="top left",
        annotation_font_color=C_RED,
    )
    fig_org_trend.update_layout(
        height=320,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(tickformat=".0%", range=[0, 1.05], gridcolor=C_LIGHT_GREY, title=None),
        xaxis=dict(gridcolor=C_LIGHT_GREY, title=None),
        legend=dict(orientation="h", y=-0.2, font=dict(size=10)),
    )
    st.plotly_chart(fig_org_trend, use_container_width=True)

with right_org:
    st.markdown(f"**Waiting Time Breakdown — {selected_month}**")

    breakdown_bands = [
        ("w14",    "≤ 14 days",  C_DARK_BLUE),
        ("d15_28", "15–28 days", C_BLUE),
        ("d29_42", "29–42 days", C_YELLOW),
        ("d43_62", "43–62 days", "#FF6B35"),
        ("d63plus", "> 62 days", C_RED),
    ]

    if org_has_data:
        o = df_org_month.iloc[0]
        bd_values = [o.get(col, 0) or 0 for col, _, _ in breakdown_bands]
        bd_labels = [lbl for _, lbl, _ in breakdown_bands]
        bd_colors = [col for _, _, col in breakdown_bands]

        fig_donut = go.Figure(go.Pie(
            labels=bd_labels,
            values=bd_values,
            hole=0.45,
            marker=dict(colors=bd_colors),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>%{value:,} patients (%{percent})<extra></extra>",
            sort=False,
        ))
        fig_donut.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="white",
            showlegend=False,
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("No breakdown data available for this selection.")

# ── Month-by-month detail table ───────────────────────────────────────────────
st.markdown(f"**Month-by-month detail — {selected_org}**")

_detail_cols = ["month", "total", "within_28", "after_28", "pct_28",
                "w14", "d15_28", "d29_42", "d43_62", "d63plus"]
_col_names   = ["Month", "Total", "Within 28d", "After 28d", "% within 28d",
                "≤14d", "15–28d", "29–42d", "43–62d", ">62d"]

_count_cols_detail = ["total", "within_28", "after_28", "w14", "d15_28", "d29_42", "d43_62", "d63plus"]
_all_months_df = pd.DataFrame({"month": MONTH_ORDER})

def _fmt(df_in, route_label):
    # Merge against all months so every month appears, filling gaps with 0
    base = df_in[_detail_cols].copy() if not df_in.empty else pd.DataFrame(columns=_detail_cols)
    base["month"] = base["month"].astype(str)
    d = _all_months_df.merge(base, on="month", how="left")
    for col in _count_cols_detail:
        d[col] = d[col].fillna(0).astype(int)
    # Recalculate % from filled counts
    d["pct_28"] = (d["within_28"] / d["total"]).where(d["total"] > 0, 0)
    d.columns = _col_names
    d.insert(1, "Route", route_label)
    d["% within 28d"] = d["% within 28d"].apply(lambda x: f"{x:.1%}")
    return d

detail = pd.concat([
    _fmt(df_org_all, "Combined"),
    _fmt(df_org_usc,  "Urgent Suspected Cancer"),
    _fmt(df_org_nsp,  "National Screening Programme"),
], ignore_index=True)
detail["Month"] = pd.Categorical(detail["Month"], categories=MONTH_ORDER, ordered=True)
detail = detail.sort_values(["Month", "Route"]).reset_index(drop=True)
detail["Month"] = detail["Month"].astype(str)

def swatch(color, border="#ccc"):
    return (
        f"<span style='display:inline-block;width:12px;height:12px;"
        f"background:{color};border:1px solid {border};"
        f"margin-right:6px;vertical-align:middle;'></span>"
    )

st.markdown(
    swatch("#fde8e8") +
    "<span style='font-size:0.82rem;vertical-align:middle;'>Below 75% target</span>"
    "&nbsp;&nbsp;&nbsp;" +
    swatch("#e6f4ec") +
    "<span style='font-size:0.82rem;vertical-align:middle;'>Meets or exceeds 75% target</span>"
    "&nbsp;&nbsp;&nbsp;" +
    swatch("#f0f0f0") +
    "<span style='font-size:0.82rem;vertical-align:middle;'>No data</span>"
    "&nbsp;&nbsp;&nbsp;"
    "<span style='font-size:0.82rem;vertical-align:middle;'><b>Bold</b> = Combined (all routes)</span>",
    unsafe_allow_html=True,
)

def style_detail(row):
    no_data = row["Total"] == 0
    try:
        val = float(row["% within 28d"].replace("%", "")) / 100
    except Exception:
        val = None
    if no_data:
        bg = "background-color: #f0f0f0"
    elif val is not None and val >= FDS_TARGET:
        bg = "background-color: #e6f4ec"
    elif val is not None and val < FDS_TARGET:
        bg = "background-color: #fde8e8"
    else:
        bg = ""
    weight = "font-weight: bold" if row["Route"] == "Combined" else "font-weight: normal"
    return [f"{bg}; {weight}"] * len(row)

st.dataframe(
    detail.style.apply(style_detail, axis=1),
    use_container_width=True,
    hide_index=True,
)

csv_bytes = detail.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇  Download as CSV",
    data=csv_bytes,
    file_name=f"NHS_CRC_28day_FDS_{view}_{selected_org.replace(' ', '_')}.csv",
    mime="text/csv",
)


# ── FOOTER ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"<p style='color:{C_GREY};font-size:0.78rem;line-height:1.6;'>"
    "Data source: NHS England Cancer Waiting Times (publicly available). "
    "Covers <em>Suspected Lower Gastrointestinal Cancer</em> referrals only. "
    "The 28-day Faster Diagnosis Standard (FDS) measures the proportion of patients who "
    "receive a definitive cancer diagnosis or exclusion within 28 days of urgent referral. "
    "National target: ≥ 75%. "
    "Figures are based on patients told of their outcome in the reporting month."
    "</p>",
    unsafe_allow_html=True,
)
