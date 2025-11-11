# streamlit_rodents.py
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="NYC Rodent Inspections — Mini Dashboard",
    page_icon="🐀",
    layout="wide",
)

# ========= Helper =========
@st.cache_data(ttl=60*30, show_spinner=True)
def load_rodent_data(limit=5000, start="2019-01-01", end="2024-12-31"):
    """
    Pulls a small, query-limited slice directly from NYC Open Data (Socrata API).
    Only essential columns are requested to keep it fast and memory-light.
    """
    # Socrata "DOHMH Rodent Inspection" dataset id: p937-wjvj
    base = "https://data.cityofnewyork.us/resource/p937-wjvj.csv"
    select = (
        "$select=inspection_date,borough,inspection_type,result,latitude,longitude,"
        "nta,zip_code"
    )
    where = (
        f"$where=inspection_date between '{start}T00:00:00.000' and '{end}T23:59:59.000'"
        " AND latitude IS NOT NULL AND longitude IS NOT NULL"
    )
    url = f"{base}?{select}&{where}&$limit={int(limit)}"
    df = pd.read_csv(url, low_memory=False)
    # Basic cleaning
    df["inspection_date"] = pd.to_datetime(df["inspection_date"], errors="coerce")
    df = df.dropna(subset=["inspection_date", "borough", "result"])
    df["year"] = df["inspection_date"].dt.year
    df["month"] = df["inspection_date"].dt.month
    df["ym"] = df["inspection_date"].dt.to_period("M").astype(str)
    return df

# ========= Sidebar =========
st.sidebar.title("Controls")
st.sidebar.caption("Small sample for speed on Streamlit Cloud.")

limit = st.sidebar.slider("Rows to load", 1000, 25000, 5000, step=1000)
years = st.sidebar.slider("Year range", 2019, 2024, (2019, 2024))
result_filter = st.sidebar.multiselect(
    "Result types",
    ["Passed", "Rat Activity", "Bait applied", "Monitoring visit", "Failed for Other R"],
    default=["Passed", "Rat Activity", "Bait applied", "Failed for Other R"],
)

# ========= Load =========
with st.spinner("Fetching a small slice from NYC Open Data…"):
    df = load_rodent_data(limit=limit, start=f"{years[0]}-01-01", end=f"{years[1]}-12-31")

st.title("🐀 NYC DOHMH Rodent Inspections — Mini Dashboard")
st.caption("Fast sample (Socrata API, limited rows) for class demo / Streamlit Cloud.")

if df.empty:
    st.warning("No rows loaded. Try widening the year range or increasing the row limit.")
    st.stop()

# ========= Filters in-page =========
colA, colB, colC = st.columns(3)
with colA:
    boroughs = ["All"] + sorted(df["borough"].dropna().unique().tolist())
    pick_boro = st.selectbox("Borough", boroughs, index=0)
with colB:
    pick_result = st.multiselect("Result filter", sorted(df["result"].unique()), default=result_filter)
with colC:
    sample_for_map = st.slider("Max map points (subsample)", 500, 10000, 3000, 500)

mask = df["result"].isin(pick_result) if pick_result else df["result"].notna()
if pick_boro != "All":
    mask &= df["borough"].eq(pick_boro)
df_view = df.loc[mask].copy()

st.markdown(f"**Loaded:** {len(df):,} rows · **After filters:** {len(df_view):,} rows")

# ========= KPIs =========
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Distinct Boroughs", df_view["borough"].nunique())
with k2:
    st.metric("NTA Areas", df_view["nta"].nunique())
with k3:
    st.metric("ZIP codes", df_view["zip_code"].nunique())
with k4:
    st.metric("Result types", df_view["result"].nunique())

st.divider()

# ========= Charts =========
tab1, tab2, tab3 = st.tabs(["Trends", "Results & Boroughs", "Map"])

# Trends over time
with tab1:
    st.subheader("Inspections per Month")
    month_ct = (
        df_view.groupby("ym", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("ym")
    )
    fig_tr = px.line(
        month_ct, x="ym", y="count", markers=True,
        color_discrete_sequence=["#6a1b9a"],
        labels={"ym": "Year-Month", "count": "Inspections"},
        title="Monthly inspection counts"
    )
    fig_tr.update_layout(xaxis=dict(tickangle=-45))
    st.plotly_chart(fig_tr, use_container_width=True)

    st.caption("Tip: increase ‘Rows to load’ in the sidebar for richer trends.")

# Result mix & Borough distribution
with tab2:
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.subheader("Result Mix")
        res_ct = df_view["result"].value_counts().reset_index()
        res_ct.columns = ["result", "count"]
        fig_pie = px.pie(
            res_ct, names="result", values="count",
            hole=0.45, color="result",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_pie.update_traces(textposition="inside", textinfo="label+percent")
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("By Borough")
        bor_ct = df_view["borough"].value_counts().reset_index()
        bor_ct.columns = ["borough", "count"]
        fig_bor = px.bar(
            bor_ct, x="borough", y="count",
            color="count", color_continuous_scale=px.colors.sequential.Sunset,
            labels={"count": "Inspections", "borough": ""},
        )
        fig_bor.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_bor, use_container_width=True)

# Map
with tab3:
    st.subheader("Inspection Map (sampled for speed)")
    geo = df_view.dropna(subset=["latitude", "longitude"])
    if len(geo) > sample_for_map:
        geo = geo.sample(sample_for_map, random_state=42)

    fig_map = px.scatter_mapbox(
        geo,
        lat="latitude", lon="longitude",
        color="result",
        hover_data=["inspection_date", "borough", "inspection_type", "nta", "zip_code"],
        zoom=9, height=600,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

st.divider()
with st.expander("Show raw (first 100 rows)"):
    st.dataframe(df_view.head(100), use_container_width=True)










