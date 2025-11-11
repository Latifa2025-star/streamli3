# Streamlit3.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Streamlit + Plotly Smoke Test", page_icon="✅", layout="centered")

st.title("✅ Streamlit + Plotly Smoke Test")
st.caption("If you can see and interact with the chart below, your deployment is wired correctly.")

# Built-in sample – no internet needed
df = px.data.iris()

# Simple UI controls
cols = df.columns.tolist()
num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
x = st.selectbox("X axis", num_cols, index=num_cols.index("sepal_width"))
y = st.selectbox("Y axis", num_cols, index=num_cols.index("sepal_length"))
color = st.selectbox("Color by", ["species", None], index=0)

fig = px.scatter(
    df,
    x=x, y=y,
    color=None if color is None else color,
    height=500,
    title=f"Iris sample scatter — {x} vs {y}",
)
fig.update_traces(marker=dict(size=10, line=dict(width=0)))  # clean look
st.plotly_chart(fig, use_container_width=True)

with st.expander("App info"):
    st.write("• File: **Streamlit3.py**")
    st.write("• Uses Plotly’s built-in iris dataset (no network).")
    st.write("• If this runs, `requirements.txt` and `runtime.txt` are set up correctly.")




