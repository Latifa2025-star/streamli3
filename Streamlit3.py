# rodents_app.py
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="NYC Rodent Inspections — Mini Dashboard", page_icon="🐀", layout="wide")

# ---- palettes (colorblind-friendly) ----
PAL_SEQ = px.colors.sequential.OrRd
PAL_ALT = px.colors.sequential.Sunset
PAL_QUAL = px.colors.qualitative.Set2

# ---- sidebar controls ----
st.sidebar.title("🐀 Rodent Dashboard — Controls")

SAMPLE_N = st.sidebar.slider("Sample rows (keeps app fast)", min_value=5_000, max_value=100_000, value=30_000, step=5_000)
MAX_MAP_POINTS = st.sidebar.slider("Max points on map", 1_000, 30_000, 8_000, 1_000)
RESULT_PICK = st.sidebar.multiselect(
    "Filter: Inspection Result",
    options=["Passed", "Rat Activity", "Bait applied", "Failed for Other R", "Monitoring visit"],
    default=["Passed", "Rat Activity", "Bait applied", "Failed for Other R", "Monitoring visit"],
)

BORO_PICK = st.sidebar.multiselect(
    "Filter: Borough",
    options=["MANHATTAN", "BROOKLYN", "BRONX", "QUEENS", "STATEN ISLAND"],
    default=[],
)

st.sidebar.caption("Tip: reduce sample/map points if the app feels slow.")

# ---- data helpers ----
DATA_URL = "https://data.cityofnewyork.us/api/views/p937-wjvj/rows.csv?accessType=DOWNLOAD"

@st.cache_data(show_spinner=True)
def load_clean(sample_n: int) -> pd.DataFrame:
    df = pd.read_csv(DATA_URL, low_memory=False)
    # keep lightweight columns
    keep = [
        "INSPECTION_DATE","BOROUGH","ZIP_CODE","INSPECTION_TYPE","RESULT",
        "X_COORD","Y_COORD","LATITUDE","LONGITUDE","NTA"
    ]
    df = df[keep].copy()

    # parse dates & derive parts
    df["INSPECTION_DATE"] = pd.to_datetime(df["INSPECTION_DATE"], errors="coerce")
    df = df.dropna(subset=["INSPECTION_DATE", "RESULT", "BOROUGH"])
    df["INSPECTION_YEAR"] = df["INSPECTION_DATE"].dt.year
    df["INSPECTION_MONTH"] = df["INSPECTION_DATE"].dt.month

    # normalize categories
    df["RESULT"] = df["RESULT"].replace({
        "Bait applied":"Bait applied", "Rat Activity":"Rat Activity", "Passed":"Passed",
        "Failed for Other R":"Failed for Other R", "Monitoring visit":"Monitoring visit"
    })

    # reasonable year window
    df = df[(df["INSPECTION_YEAR"] >= 2010) & (df["INSPECTION_YEAR"] <= 2024)]

    # sample for performance
    if len(df) > sample_n:
        df = df.sample(n=sample_n, random_state=42)
    return df

with st.spinner("Loading & sampling NYC Rodent data…"):
    df = load_clean(SAMPLE_N)

# filters
if RESULT_PICK:
    df = df[df["RESULT"].isin(RESULT_PICK)]
if BORO_PICK:
    df = df[df["BOROUGH"].isin(BORO_PICK)]

# ---- header KPIs ----
st.title("🐀 NYC DOHMH Rodent Inspections — Mini Dashboard")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Rows (sampled)", f"{len(df):,}")
with k2:
    st.metric("Boroughs", df["BOROUGH"].nunique())
with k3:
    st.metric("Year range", f"{int(df['INSPECTION_YEAR'].min())}–{int(df['INSPECTION_YEAR'].max())}")
with k4:
    st.metric("Results shown", len(RESULT_PICK))

st.markdown("---")

# ---- tabs ----
tab1, tab2, tab3 = st.tabs(["Overview", "Time & Seasonality", "Map"])

# ---------------- Overview ----------------
with tab1:
    c1, c2 = st.columns([1, 1])

    with c1:
        counts = (
            df["RESULT"].value_counts()
              .rename_axis("RESULT")
              .reset_index(name="count")
        )
        fig = px.pie(
            counts, names="RESULT", values="count",
            hole=0.45, color="RESULT", color_discrete_sequence=PAL_QUAL,
            title="Outcome Mix"
        )
        fig.update_traces(textinfo="percent+label", textposition="inside")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        boro = (
            df["BOROUGH"].value_counts()
              .rename_axis("BOROUGH")
              .reset_index(name="count")
              .sort_values("count", ascending=False)
        )
        fig = px.bar(
            boro, x="BOROUGH", y="count",
            color="count", color_continuous_scale=PAL_ALT,
            title="Inspections by Borough"
        )
        fig.update_layout(xaxis_title="", yaxis_title="Inspections", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    st.caption("Tip: use the sidebar to filter by result/borough and resample rows.")

# ------------- Time & Seasonality -------------
with tab2:
    c1, c2 = st.columns([1.2, 0.8])

    with c1:
        yearly = (
            df.groupby("INSPECTION_YEAR")
              .size().reset_index(name="count")
              .sort_values("INSPECTION_YEAR")
        )
        fig = px.line(
            yearly, x="INSPECTION_YEAR", y="count",
            markers=True, color_discrete_sequence=[PAL_SEQ[5]],
            title="Inspections per Year (2010–2024)"
        )
        # neat COVID annotation inside the plot area (near 2020)
        if (yearly["INSPECTION_YEAR"] == 2020).any():
            y2020 = yearly.loc[yearly["INSPECTION_YEAR"] == 2020, "count"].values[0]
            fig.add_annotation(
                x=2019.3, y=y2020*1.05, text="<b>COVID-19 dip</b>",
                showarrow=True, arrowhead=3, ax=60, ay=-10,
                arrowcolor="purple", font=dict(color="purple", size=14)
            )
        fig.update_layout(xaxis=dict(dtick=1))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        month = (
            df.groupby("INSPECTION_MONTH")
              .size().reset_index(name="count")
              .sort_values("INSPECTION_MONTH")
        )
        month["MONTH"] = pd.to_datetime(month["INSPECTION_MONTH"], format="%m").dt.strftime("%b")
        fig = px.bar(
            month, x="MONTH", y="count",
            color="count", color_continuous_scale=PAL_SEQ,
            title="Seasonality — Inspections by Month"
        )
        fig.update_layout(xaxis_title="", yaxis_title="Inspections", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # Year x Month heatmap (compact)
    pivot = (
        df.groupby(["INSPECTION_YEAR", "INSPECTION_MONTH"])
          .size().reset_index(name="count")
          .pivot(index="INSPECTION_YEAR", columns="INSPECTION_MONTH", values="count")
          .fillna(0)
    )
    pivot.columns = [pd.to_datetime(str(int(m)), format="%m").strftime("%b") for m in pivot.columns]
    fig = px.imshow(
        pivot.values,
        x=list(pivot.columns), y=list(pivot.index.astype(int)),
        color_continuous_scale=PAL_SEQ, aspect="auto",
        title="Heatmap — Year × Month"
    )
    fig.update_layout(xaxis_title="Month", yaxis_title="Year")
    st.plotly_chart(fig, use_container_width=True)

# ------------------- Map -------------------
with tab3:
    st.subheader("Map — Sampled Points")
    geo = df.dropna(subset=["LATITUDE", "LONGITUDE"])
    if len(geo) > MAX_MAP_POINTS:
        geo = geo.sample(n=MAX_MAP_POINTS, random_state=42)

    fig = px.scatter_mapbox(
        geo,
        lat="LATITUDE", lon="LONGITUDE",
        color="RESULT", color_discrete_sequence=PAL_QUAL,
        hover_data=["BOROUGH", "INSPECTION_DATE", "INSPECTION_TYPE", "RESULT"],
        zoom=9, height=650, title=f"Rodent Inspections (up to {len(geo):,} points)"
    )
    fig.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=60, b=0))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Data: NYC Open Data — DOHMH Rodent Inspection (2010–2024). This mini app uses a sampled subset for speed.")








