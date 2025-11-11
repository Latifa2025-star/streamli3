# Tiny Rodent Dashboard – safe small-sample version
# Works on Streamlit Cloud with no large downloads

import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Rodent Inspections (mini)", page_icon="🐀", layout="wide")

API = "https://data.cityofnewyork.us/resource/p937-wjvj.json"  # DOHMH Rodent Inspection
COLUMNS = [
    "inspection_date",
    "borough",
    "inspection_type",
    "result",
    "latitude",
    "longitude",
]

st.sidebar.header("Controls")

# Keep the API request light; 1k default, with an upper bound of 20k
limit = st.sidebar.slider("Rows to load (API limit)", 1000, 20000, 3000, step=1000)

year_min, year_max = st.sidebar.select_slider(
    "Year range",
    options=list(range(2010, 2025)),
    value=(2018, 2024),
)

@st.cache_data(show_spinner=True, ttl=3600)
def fetch_data(limit: int, y_min: int, y_max: int, boro: str | None):
    # Build Socrata query
    where = f"year(inspection_date) between {y_min} and {y_max}"
    params = {
        "$select": ",".join(COLUMNS),
        "$where": where,
        "$limit": limit,
        "$order": "inspection_date DESC",
    }
    if boro and boro != "All":
        params["$where"] = f"{where} AND borough = '{boro}'"

    r = requests.get(API, params=params, timeout=30)
    r.raise_for_status()  # will show a neat error in Streamlit if HTTP fails

    data = r.json()  # list[dict]
    if not data:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.json_normalize(data)
    # Normalize types
    if "inspection_date" in df:
        df["inspection_date"] = pd.to_datetime(df["inspection_date"], errors="coerce")
        df["year"] = df["inspection_date"].dt.year
        df["month"] = df["inspection_date"].dt.month
    for col in ("latitude", "longitude"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "borough" in df:
        df["borough"] = df["borough"].astype("category")
    if "result" in df:
        df["result"] = df["result"].astype("category")
    return df

# First fetch once without borough to populate the filter options
stub_df = fetch_data(1000, year_min, year_max, boro=None)
boro_options = ["All"] + sorted(x for x in stub_df["borough"].dropna().unique()) if not stub_df.empty else ["All"]
selected_boro = st.sidebar.selectbox("Borough (optional filter)", boro_options, index=0)

# Now fetch the actual data for the UI
df = fetch_data(limit, year_min, year_max, selected_boro if selected_boro != "All" else None)

st.title("🐀 NYC Rodent Inspections — mini dashboard")

if df.empty:
    st.info("No rows returned for the current filters. Try widening the year range or removing the borough filter.")
    st.stop()

left, right = st.columns([1, 1])

with left:
    st.subheader("Counts by Inspection Result")
    counts = (
        df["result"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
        .rename(columns={"index": "result", "result": "count"})
    )
    fig = px.bar(
        counts,
        x="result",
        y="count",
        color="count",
        color_continuous_scale=px.colors.sequential.Sunset,
        title="Inspection Outcomes",
        text="count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="", yaxis_title="Count", coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Quick Map (sampled for speed)")
    map_df = df.dropna(subset=["latitude", "longitude"]).sample(
        n=min(1500, len(df)), random_state=42
    )
    if map_df.empty:
        st.write("No mappable points for this slice.")
    else:
        mfig = px.scatter_mapbox(
            map_df,
            lat="latitude",
            lon="longitude",
            color="result",
            hover_data=["borough", "inspection_date", "inspection_type", "result"],
            zoom=9,
            height=520,
            color_discrete_sequence=px.colors.qualitative.Set2,
            title=f"Rodent inspections ({len(map_df):,} points)",
        )
        mfig.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=60, b=0))
        st.plotly_chart(mfig, use_container_width=True)

st.caption(
    "Data source: NYC Open Data (DOHMH Rodent Inspections). "
    "This app intentionally pulls a small sample to keep it fast and reliable."
)







