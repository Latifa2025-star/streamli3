import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Test App", layout="wide")

st.title("✅ Streamlit Deployment Test")
st.write("If you can see this, your app is working!")

# Create small sample data
df = pd.DataFrame({
    "City": ["NYC", "LA", "Chicago", "Houston", "Phoenix"],
    "Population": [8.4, 4.0, 2.7, 2.3, 1.7]
})

st.subheader("Sample Data")
st.dataframe(df)

# Plotly Bar Chart
fig = px.bar(
    df,
    x="City",
    y="Population",
    title="Population of 5 Major US Cities",
    color="Population"
)

st.subheader("Simple Plot")
st.plotly_chart(fig, use_container_width=True)








