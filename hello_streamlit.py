"""hello_streamlit.py - the smallest useful dashboard. Run:  streamlit run hello_streamlit.py"""
import streamlit as st

import dashboard_lib as dl

st.set_page_config(page_title="Hello dashboard", layout="wide")
st.title("My first dashboard")

customers, transactions, users = dl.load_data()
master = dl.prepare_master(customers, transactions)          # the cleaned master table

country = st.sidebar.selectbox("Country", ["All"] + sorted(master["country"].unique()))
df = master if country == "All" else master[master["country"] == country]

col1, col2 = st.columns(2)
col1.metric("Transactions", f"{len(df):,}")
col2.metric("Net cash flow", dl.fmt_amt(df["amount"].sum(), signed=True))

st.plotly_chart(dl.chart_monthly_cashflow(df))
st.dataframe(df.head(20))
