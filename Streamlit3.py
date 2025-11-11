# --- Streamlit NYC Rodent mini dashboard (fast, API-based) ---
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="NYC Rodent Inspections — Mini Dashboard",
    page_icon="🐀",
    layout="wide",
)

API = "https://data.cityofnewyork.us/resource/p937-wjvj.json"

# -------- Sidebar controls (kept small for speed) --------
st.sidebar.title("Controls")
limit = st.sidebar.slider("Rows to load (API limit)", 5_000, 50_000, 20_000, 5_000)
year_min, year_max = st.sidebar.select_slider(
    "Year range",
    options=list(range(2010, 2025)),
    value=(2018, 2024)
)
selected_boro = st.sidebar.selectbox(
    "Borough (optional filter)", ["All","MANHATTAN","BROOKLYN","BRONX","QUEENS","STATEN ISLAND"]
)

# -------- Data fetch (cached) --------
@st.cache_data(show_spinner=True, ttl=3600)
def fetch_data(limit, y0, y1, borough=None):
    # keep only the columns we need, and filter on the server
    select_cols = ",".join([
        "borough","result","inspection_date","inspection_type",
        "zip_code","nta","latitude","longitude"
    ])

    where = [
        "inspection_date between '2010-01-01T00:00:00.000' and '2024-12-31T23:59:59.999'",
        "latitude is not null",
        "longitude is not null"
    ]
    # slice to requested years
    where.append(f"date_part_yyyy(inspection_date) between {y0} and {y1}")
    if borough and borough != "All":
        where.append(f"upper(borough) = '{borough}'")

    params = {
        "$select": select_cols,
        "$where": " AND ".join(where),
        "$order": "inspection_date DESC",
        "$limit": limit
    }
    df = pd.read_json(API, params=params)

    # basic cleaning/enrichment
    if not df.empty and "inspection_date" in df.columns:
        df["inspection_date"] = pd.to_datetime(df["inspection_date"], errors="coerce")
        df["year"]  = df["inspection_date"].dt.year
        df["month"] = df["inspection_date"].dt.month
        df["month_name"] = pd.to_datetime(df["month"], format="%m").dt.strftime("%b")

    return df

with st.spinner("Loading NYC Open Data slice…"):
    df = fetch_data(limit, year_min, year_max, selected_boro if selected_boro!="All" else None)

st.title("🐀 NYC Rodent Inspections — Mini Dashboard")
st.caption(f"Live slice via NYC Open Data API • Rows loaded: {len(df):,} (limit {limit:,})")

if df.empty:
    st.warning("No rows returned. Try widening the year range or increasing the limit.")
    st.stop()

# --------- KPIs ---------
k1,k2,k3,k4 = st.columns(4)
with k1: st.metric("Rows", f"{len(df):,}")
with k2: st.metric("Boroughs", df["borough"].nunique())
with k3: st.metric("Outcomes", df["result"].nunique())
with k4:
    yrs = df["year"].min(), df["year"].max()
    st.metric("Year span", f"{int(yrs[0])}–{int(yrs[1])}")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["Overview", "Seasonality", "Map"])

# --------- Overview ---------
with tab1:
    c1,c2 = st.columns([1,1])
    with c1:
        by_boro = (df["borough"]
                   .fillna("Unknown")
                   .value_counts()
                   .reset_index()
                   .rename(columns={"index":"borough","borough":"count"}))
        fig1 = px.bar(by_boro, x="borough", y="count",
                      color="count", color_continuous_scale=px.colors.sequential.Sunset,
                      title="Inspections by Borough")
        fig1.update_layout(yaxis_title="Inspections", xaxis_title="")
        fig1.update_coloraxes(showscale=False)
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        by_res = (df["result"]
                  .fillna("Unknown")
                  .value_counts()
                  .reset_index()
                  .rename(columns={"index":"result","result":"count"}))
        fig2 = px.pie(by_res, names="result", values="count",
                      color="result", color_discrete_sequence=px.colors.qualitative.Set2,
                      hole=0.45, title="Outcome Mix")
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig2, use_container_width=True)

# --------- Seasonality ---------
with tab2:
    by_month = (df.groupby("month_name", sort=False)
                  .size().reset_index(name="count"))
    # Ensure Jan..Dec order
    cat = pd.Categorical(by_month["month_name"],
                         categories=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
                         ordered=True)
    by_month = by_month.assign(month_name=cat).sort_values("month_name")
    fig3 = px.bar(by_month, x="month_name", y="count",
                  color="count", color_continuous_scale=px.colors.sequential.OrRd,
                  title="Inspections by Month (selected years)")
    fig3.update_coloraxes(showscale=False)
    fig3.update_layout(xaxis_title="", yaxis_title="Inspections")
    st.plotly_chart(fig3, use_container_width=True)

# --------- Map ---------
with tab3:
    st.caption("Sampled points for performance (uses OpenStreetMap, no token needed).")
    # (df is already limited; optionally resample again for speed if user loaded the full 50k)
    sample_for_map = df.sample(min(len(df), 15_000), random_state=42)
    fig4 = px.scatter_mapbox(
        sample_for_map,
        lat="latitude", lon="longitude",
        color="result",
        hover_data=["borough","inspection_type","inspection_date"],
        color_discrete_sequence=px.colors.qualitative.Set2,
        zoom=9, height=620, title="Rodent Inspections (sample)"
    )
    fig4.update_layout(mapbox_style="open-street-map", margin=dict(l=0,r=0,t=60,b=0))
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")
st.caption("Data source: NYC Open Data — DOHMH Rodent Inspection. This app pulls a small, cached slice via the API for fast Streamlit Cloud rendering.")





