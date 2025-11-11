# Streamlit3.py
# Minimal, fast Streamlit dashboard for NYC Rodent Inspections (sample via API)

import os
import json
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="NYC Rodent Inspections (Sample)", page_icon="🐀", layout="wide")

st.title("🐀 NYC Rodent Inspections — Fast Sample Dashboard")
st.caption("Source: NYC Open Data (DOHMH Rodent Inspection). This app pulls a small sample via API for quick loading.")

# -----------------------------
# Controls
# -----------------------------
with st.sidebar:
    st.header("Controls")
    sample_n = st.slider("Rows to fetch (API sample)", min_value=2_000, max_value=50_000, value=20_000, step=2_000)
    years = st.slider("Year range", 2010, 2024, (2018, 2024))
    show_map_points = st.slider("Max map points", 1000, 20000, 5000, 1000)
    st.markdown("---")
    st.markdown("**Optional**: add an app token in *Advanced settings → Secrets* as `NYC_APP_TOKEN` for higher API limits.")

# -----------------------------
# Data loader (API)
# -----------------------------
API = "https://data.cityofnewyork.us/resource/p937-wjvj.json"

# Only the columns we need (keeps payload small)
COLS = [
    "borough",
    "inspection_date",
    "inspection_type",
    "result",
    "zip_code",
    "nta",
    "latitude",
    "longitude",
]

def build_query(year_lo: int, year_hi: int, limit: int) -> dict:
    # Socrata $select/$where/$limit compliant params
    where = (
        f"inspection_date between '{year_lo}-01-01T00:00:00.000' "
        f"and '{year_hi}-12-31T23:59:59.999'"
    )
    params = {
        "$select": ",".join(COLS),
        "$where": where,
        "$order": "inspection_date DESC",
        "$limit": limit
    }
    return params

@st.cache_data(show_spinner=True, ttl=600)
def fetch_sample(year_lo: int, year_hi: int, limit: int) -> pd.DataFrame:
    params = build_query(year_lo, year_hi, limit)
    headers = {}
    # Optional app token via secrets
    token = st.secrets.get("NYC_APP_TOKEN", None)
    if token:
        headers["X-App-Token"] = token

    r = requests.get(API, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not data:
        return pd.DataFrame(columns=COLS)

    df = pd.DataFrame(data)
    # Coerce dtypes
    if "inspection_date" in df.columns:
        df["inspection_date"] = pd.to_datetime(df["inspection_date"], errors="coerce")
        df["year"] = df["inspection_date"].dt.year
        df["month"] = df["inspection_date"].dt.month
        df["month_name"] = df["inspection_date"].dt.strftime("%b")
        df["year_month"] = df["inspection_date"].dt.to_period("M").astype(str)
    for c in ["latitude", "longitude"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

with st.spinner("Fetching a small sample from NYC Open Data…"):
    df = fetch_sample(years[0], years[1], sample_n)

# -----------------------------
# Guard rails
# -----------------------------
if df.empty:
    st.warning("No data returned for the current filters. Try widening the year range or increasing the sample size.")
    st.stop()

# -----------------------------
# KPIs
# -----------------------------
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Sample rows", f"{len(df):,}")
with c2:
    st.metric("Years", f"{years[0]}–{years[1]}")
with c3:
    st.metric("Boroughs", df["borough"].nunique())
with c4:
    st.metric("Outcomes", df["result"].nunique())

st.divider()

# -----------------------------
# 1) Inspections over time (monthly)
# -----------------------------
st.subheader("Inspections Over Time (sample)")
time_ct = (
    df.dropna(subset=["year_month"])
      .groupby("year_month", as_index=False)
      .size()
      .rename(columns={"size": "count"})
      .sort_values("year_month")
)
fig_time = px.line(
    time_ct, x="year_month", y="count",
    markers=True,
    title="Monthly inspection counts (sample)",
)
fig_time.update_layout(xaxis_title="", yaxis_title="Inspections")
st.plotly_chart(fig_time, width="stretch")

# -----------------------------
# 2) Outcomes by Borough
# -----------------------------
st.subheader("Outcomes by Borough (sample)")
outcome_ct = (
    df.groupby(["borough", "result"], dropna=False)
      .size()
      .reset_index(name="count")
)
# keep top 5 outcomes by total volume for readable color legend
top_outcomes = (
    outcome_ct.groupby("result")["count"].sum()
    .sort_values(ascending=False).head(5).index.tolist()
)
outcome_ct["result_top5"] = outcome_ct["result"].where(outcome_ct["result"].isin(top_outcomes), "Other/Minor")

fig_out = px.bar(
    outcome_ct, x="borough", y="count", color="result_top5",
    title="Inspection outcomes by borough (collapsed to Top 5 + Other)",
    barmode="stack"
)
fig_out.update_layout(xaxis_title="", yaxis_title="Inspections")
st.plotly_chart(fig_out, width="stretch")

# -----------------------------
# 3) Map (sampled to keep it light)
# -----------------------------
st.subheader("Map — Sampled Points")
geo = df.dropna(subset=["latitude", "longitude"]).copy()
if len(geo) > show_map_points:
    geo = geo.sample(show_map_points, random_state=42)

if not geo.empty:
    fig_map = px.scatter_mapbox(
        geo,
        lat="latitude", lon="longitude",
        color="result",
        hover_data=["borough", "zip_code", "inspection_type", "inspection_date"],
        zoom=9, height=600,
        title=f"Rodent inspections (up to {show_map_points:,} points from sample)"
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=60, b=0))
    st.plotly_chart(fig_map, width="stretch")
else:
    st.info("No rows with valid latitude/longitude in the current sample.")

st.caption("Tip: increase the sample size in the sidebar if you want more detail.")












