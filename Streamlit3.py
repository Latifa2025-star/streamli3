# streamlit_app.py
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="NYC Rodent Inspections (Mini Demo)", page_icon="🐀", layout="wide")

DATA_URL = "https://data.cityofnewyork.us/api/views/p937-wjvj/rows.csv?accessType=DOWNLOAD"

@st.cache_data(show_spinner=True)
def load_data(sample_n: int = 200_000):
    # Load & optionally sample for speed
    df = pd.read_csv(DATA_URL, low_memory=False)
    if sample_n and len(df) > sample_n:
        df = df.sample(n=sample_n, random_state=42)
    # Parse dates + restrict range (2010–2024)
    df["INSPECTION_DATE"] = pd.to_datetime(df["INSPECTION_DATE"], errors="coerce")
    df = df[(df["INSPECTION_DATE"] >= "2010-01-01") & (df["INSPECTION_DATE"] <= "2024-12-31")]
    # Year/Month
    df["INSPECTION_YEAR"]  = df["INSPECTION_DATE"].dt.year
    df["INSPECTION_MONTH"] = df["INSPECTION_DATE"].dt.month
    # Light clean
    df = df.dropna(subset=["BOROUGH", "RESULT"])
    return df

st.title("🐀 NYC DOHMH Rodent Inspections — Mini Demo")
st.caption("Small, safe dashboard to test Streamlit Cloud deployment. You can expand later.")

# --- Sidebar ---
st.sidebar.header("Settings")
sample_n = st.sidebar.number_input("Rows to sample (0 = all; recommended 200k)", 0, 2_000_000, 200_000, step=50_000)

with st.spinner("Loading data…"):
    df = load_data(sample_n)

# --- KPIs ---
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Rows", f"{len(df):,}")
with c2: st.metric("Year range", f"{int(df['INSPECTION_YEAR'].min())}–{int(df['INSPECTION_YEAR'].max())}")
with c3: st.metric("Boroughs", df["BOROUGH"].nunique())
with c4: st.metric("Outcomes", df["RESULT"].nunique())

st.markdown("---")

# --- Row 1: Outcomes donut + Borough bars ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Outcome Mix")
    outcomes = df["RESULT"].value_counts().rename_axis("RESULT").reset_index(name="count")
    fig_pie = px.pie(
        outcomes, names="RESULT", values="count",
        hole=0.45, color="RESULT",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.subheader("Inspections by Borough")
    borough_ct = df["BOROUGH"].value_counts().rename_axis("BOROUGH").reset_index(name="count")
    fig_boro = px.bar(
        borough_ct, x="BOROUGH", y="count",
        color="count", color_continuous_scale=px.colors.sequential.Sunset
    )
    fig_boro.update_layout(xaxis_title="", yaxis_title="Inspections", coloraxis_showscale=False)
    st.plotly_chart(fig_boro, use_container_width=True)

# --- Row 2: Year trend ---
st.subheader("Inspections per Year (2010–2024)")
year_counts = (
    df.groupby("INSPECTION_YEAR")
      .size()
      .reset_index(name="count")
      .sort_values("INSPECTION_YEAR")
)
fig_year = px.line(
    year_counts, x="INSPECTION_YEAR", y="count",
    markers=True, color_discrete_sequence=[px.colors.sequential.OrRd[4]]
)
# COVID dip annotation (kept inside plot area)
if 2020 in year_counts["INSPECTION_YEAR"].values:
    y2020 = year_counts.loc[year_counts["INSPECTION_YEAR"]==2020, "count"].values[0]
    fig_year.add_annotation(
        x=2019.5, y=y2020*1.05,
        text="<b>COVID-19 dip</b>", showarrow=True, arrowhead=3,
        ax=60, ay=-10, arrowcolor="purple", font=dict(size=14, color="purple")
    )
fig_year.update_layout(xaxis=dict(dtick=1))
st.plotly_chart(fig_year, use_container_width=True)

# --- Optional small map (sampled for speed) ---
st.subheader("Sampled Map (Optional)")
map_rows = st.slider("Max points on map", min_value=2_000, max_value=50_000, value=10_000, step=2_000)
geo = df.dropna(subset=["LATITUDE", "LONGITUDE"])
if len(geo) > map_rows:
    geo = geo.sample(n=map_rows, random_state=42)
fig_map = px.scatter_mapbox(
    geo, lat="LATITUDE", lon="LONGITUDE",
    color="RESULT", color_discrete_sequence=px.colors.qualitative.Set2,
    hover_data=["BOROUGH", "INSPECTION_DATE", "INSPECTION_TYPE"],
    zoom=9, height=550, title="Rodent Inspections (sample)"
)
fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=60, b=0))
st.plotly_chart(fig_map, use_container_width=True)

st.markdown("---")
st.caption("Data: NYC Open Data — DOHMH Rodent Inspection (2010–2024). Mini app for deployment check.")
