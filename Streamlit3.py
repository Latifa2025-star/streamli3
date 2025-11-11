import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Streamlit Smoke Test", page_icon="✅", layout="centered")

st.title("✅ Streamlit + Plotly Smoke Test")
st.caption("If you see the chart below, your deployment works.")

# Tiny built-in dataset from Plotly (no external downloads)
df = px.data.iris()

fig = px.scatter(
    df,
    x="sepal_width",
    y="sepal_length",
    color="species",
    title="Iris sample scatter (Plotly Express)",
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("App info"):
    st.write("• File: Streamlit3.py")
    st.write("• Uses Plotly’s built-in iris dataset (no network needed).")
    st.write("• If this runs, your requirements + runtime are correct.")


