import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="NYC Rodent Inspections — Mini Dashboard", page_icon="🐀", layout="wide")

# =========================
# Settings (safe defaults)
# =========================
DATA_URL = "https://data.cityofnewyork.us/api/views/p937-wjvj/rows.csv?accessType=DOWNLOAD"

# Read only the essential columns to keep memory tiny
USECOLS = [
    "INSPECTION_DATE", "BOROUGH", "ZIP_CODE", "INSPECTION_TYPE", "RESULT",
    "LATITUDE", "LONGITUDE"
]

st.title("🐀 NYC Rodent Inspections — Mini Dashboard")
st.caption("Small, fast sample so Streamlit Cloud starts reliably.")

with st.sidebar:
    st.header("Load Options")
    nrows = st.slider("Sample rows to read", 5_000, 60_000, 25_000, 5_000,
                      help="Read only this many rows from the remote CSV to stay fast.")
    year_filter = st.selectbox("Keep only this year (optional)", ["All", 2018, 2019, 2020, 2021, 2022, 2023, 2024], index=0)
    st.markdown("---")
    st.caption("Tip: If startup still times out, lower the row limit further.")

@st.cache_data(show_spinner=True, ttl=60 * 60)
def load_sample(url: str, nrows: int, usecols: list[str]) -> pd.DataFrame:
    # Read a small, top-of-file sample and essential columns only
    df = pd.read_csv(url, nrows=nrows, usecols=usecols, low_memory=False)
    # Basic cleanup / enrich
    df["INSPECTION_DATE"] = pd.to_datetime(df["INSPECTION_DATE"], errors="coerce")
    df = df.dropna(subset=["INSPECTION_DATE", "BOROUGH", "RESULT"])
    df["YEAR"] = df["INSPECTION_DATE"].dt.year
    df["MONTH"] = df["INSPECTION_DATE"].dt.month
    return df

with st.spinner("Downloading a small sample…"):
    df = load_sample(DATA_URL, nrows, USECOLS)

# Optional year filter (after load to keep cache effective)
if year_filter != "All":
    df = df.loc[df["YEAR"] == int(year_filter)]

# =========================
# KPIs
# =========================
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Rows (sample)", f"{len(df):,}")
with k2:
    st.metric("Distinct ZIP Codes", f"{df['ZIP_CODE'].nunique():,}")
with k3:
    st.metric("Boroughs", df["BOROUGH"].nunique())
with k4:
    st.metric("Results", df["RESULT"].nunique())

st.divider()

# =========================
# Plot 1: Result mix
# =========================
st.subheader("Outcome Mix (Sample)")
mix = df["RESULT"].value_counts().reset_index()
mix.columns = ["RESULT", "count"]
fig1 = px.bar(
    mix, x="RESULT", y="count",
    text="count",
    color="RESULT",
    color_discrete_sequence=px.colors.qualitative.Set2,
    title="Inspection Outcomes (sample)"
)
fig1.update_traces(textposition="outside")
fig1.update_layout(xaxis_title="", yaxis_title="Count", margin=dict(t=70))
st.plotly_chart(fig1, use_container_width=None, width="stretch")

# =========================
# Plot 2: Trend by month
# =========================
st.subheader("Inspections by Month (Sample)")
trend = (
    df.groupby(["YEAR", "MONTH"])
      .size()
      .reset_index(name="count")
      .sort_values(["YEAR", "MONTH"])
)
trend["Month"] = pd.to_datetime(trend["MONTH"], format="%m").dt.strftime("%b")
fig2 = px.line(
    trend, x="Month", y="count", color="YEAR",
    markers=True,
    color_discrete_sequence=px.colors.sequential.Sunset,
    title="Monthly Trend (by Year)"
)
fig2.update_layout(yaxis_title="Inspections", xaxis_title="", legend_title="Year", margin=dict(t=70))
st.plotly_chart(fig2, use_container_width=None, width="stretch")

# =========================
# Plot 3: Map (thinned)
# =========================
st.subheader("Map — Sampled Points")
geo = df.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()

# Thin points for performance
MAX_POINTS = 3_000
if len(geo) > MAX_POINTS:
    geo = geo.sample(MAX_POINTS, random_state=42)

if len(geo) == 0:
    st.info("No geocoded points in the current sample/filter.")
else:
    fig3 = px.scatter_mapbox(
        geo,
        lat="LATITUDE", lon="LONGITUDE",
        color="RESULT",
        hover_data=["BOROUGH", "ZIP_CODE", "INSPECTION_TYPE", "RESULT"],
        zoom=9, height=560,
        color_discrete_sequence=px.colors.qualitative.Set2,
        title=f"Rodent Inspections (up to {MAX_POINTS:,} points)"
    )
    fig3.update_layout(mapbox_style="open-street-map", margin=dict(t=70, l=0, r=0, b=0))
    st.plotly_chart(fig3, use_container_width=None, width="stretch")

st.caption("Data: NYC Open Data — DOHMH Rodent Inspection.")











