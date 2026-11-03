"""
app.py - Cash Flow & Customer Risk dashboard (Streamlit)
Run from this folder with:   streamlit run app.py
"""
import pandas as pd
import streamlit as st

import dashboard_lib as dl

# ------------------------------------------------------------------ page setup
st.set_page_config(page_title="Cash Flow & Customer Risk", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
      [data-testid="stMetric"] {background: #F7F8FA; border-left: 5px solid #A40000;
                                padding: 10px 14px; border-radius: 6px;}
      h1 {color: #A40000;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ data (cached: loaded once, not on every click)
@st.cache_data(show_spinner="Loading data...")
def get_data():
    customers, transactions, users = dl.load_data()
    master = dl.prepare_master(customers, transactions)
    quality = dl.data_quality(customers, transactions, users)
    return master, users, quality


master, users, quality = get_data()

MIN_D, MAX_D = master["date"].min().date(), master["date"].max().date()
COUNTRIES = sorted(master["country"].unique())
MERCHANTS = sorted(master["merchant"].unique())
BANDS = ["Low", "Medium", "High", "Unknown"]

# ------------------------------------------------------------------ sidebar filters (kept in session_state so Reset works)
DEFAULTS = {
    "f_dates": (MIN_D, MAX_D),
    "f_countries": COUNTRIES,
    "f_types": dl.TYPE_ORDER,
    "f_merchants": MERCHANTS,
    "f_bands": BANDS,
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def reset_filters():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


with st.sidebar:
    st.header("Filters")
    st.date_input("Date range", min_value=MIN_D, max_value=MAX_D, key="f_dates")
    st.multiselect("Country", COUNTRIES, key="f_countries",
                   help="'Unmatched account' = account IDs that are not in customers.csv")
    st.multiselect("Transaction type", dl.TYPE_ORDER, key="f_types")
    st.multiselect("Merchant", MERCHANTS, key="f_merchants")
    st.multiselect("Customer risk band", BANDS, key="f_bands",
                   help="Low <= 33, Medium 34-66, High > 66. Unknown = unmatched account")
    st.button("Reset filters", on_click=reset_filters)
    st.caption("All charts and numbers update together.")

dates = st.session_state["f_dates"]
if not isinstance(dates, (list, tuple)) or len(dates) != 2:
    st.info("Pick an end date to complete the date range.")
    st.stop()
start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1])


def apply_filters(frame, start, end):
    mask = (
        frame["date"].between(start, end)
        & frame["country"].isin(st.session_state["f_countries"])
        & frame["tx_type"].isin(st.session_state["f_types"])
        & frame["merchant"].isin(st.session_state["f_merchants"])
        & frame["risk_band"].isin(st.session_state["f_bands"])
    )
    return frame[mask]


df = apply_filters(master, start, end)

# ------------------------------------------------------------------ header
st.title("📊 Cash Flow & Customer Risk Dashboard")
st.caption(
    f"Data from {MIN_D:%d %b %Y} to {MAX_D:%d %b %Y} · "
    f"{len(df):,} of {len(master):,} transactions selected · amounts are in the file's currency units"
)

if df.empty:
    st.warning("No transactions match these filters. Widen the date range or press **Reset filters**.")
    st.stop()

# ------------------------------------------------------------------ KPI cards (with change vs the previous period)
k = dl.kpis(df)
span = (end - start).days + 1
prev_end = start - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=span - 1)
prev = dl.kpis(apply_filters(master, prev_start, prev_end)) if prev_start.date() >= MIN_D else None


def delta(name, money=True):
    if prev is None:
        return None
    diff = k[name] - prev[name]
    return (dl.fmt_amt(diff, signed=True) if money else f"{diff:+,.0f}") + " vs previous period"


c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Transactions", f"{k['transactions']:,}", delta("transactions", money=False))
c2.metric("Total inflow", dl.fmt_amt(k["inflow"]), delta("inflow"))
c3.metric("Total outflow", dl.fmt_amt(k["outflow"]), delta("outflow"), delta_color="inverse")
c4.metric("Net cash flow", dl.fmt_amt(k["net"], signed=True), delta("net"))
c5.metric("Avg transaction size", dl.fmt_amt(k["avg_tx"]), delta("avg_tx"))

with st.container(border=True):
    st.markdown("**Key takeaways for this selection**")
    for line in dl.insights(df):
        st.markdown(f"- {line}")


def show(fig, key):
    st.plotly_chart(fig, key=key)


# ------------------------------------------------------------------ tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview", "Cash-flow patterns", "Merchants & countries", "Customers & risk", "Data & quality"]
)

with tab1:
    show(dl.chart_monthly_cashflow(df), "monthly")
    left, right = st.columns(2)
    with left:
        show(dl.chart_cumulative_balance(df), "cumulative")
    with right:
        show(dl.chart_waterfall_types(df), "waterfall")

with tab2:
    show(dl.chart_daily_activity(df), "daily")
    left, right = st.columns(2)
    with left:
        show(dl.chart_activity_heatmap(df), "heatmap_time")
    with right:
        show(dl.chart_amount_by_type(df), "box_type")

with tab3:
    left, right = st.columns(2)
    with left:
        show(dl.chart_top_merchants(df), "merchants")
    with right:
        show(dl.chart_country_net(df), "country_net")
    show(dl.chart_country_type_heatmap(df), "country_type")
    show(dl.chart_treemap(df), "treemap")

with tab4:
    st.caption("Customer charts use matched accounts with activity in the current selection.")
    r1, r2, r3 = st.columns(3)
    r1.metric("Active customers", f"{k['customers']:,}")
    r2.metric("Average risk score", "n/a" if pd.isna(k["avg_risk"]) else f"{k['avg_risk']:.1f}")
    r3.metric("High-risk share", "n/a" if pd.isna(k["high_risk_share"]) else f"{k['high_risk_share']:.0%}")
    left, right = st.columns(2)
    with left:
        show(dl.chart_customers_by_country(df), "cust_country")
        show(dl.chart_risk_by_country(df), "risk_country")
    with right:
        show(dl.chart_risk_distribution(df), "risk_dist")
        show(dl.chart_signups(df), "signups")
    show(dl.chart_risk_vs_flow(df), "risk_flow")
    show(dl.chart_top_customers(df), "top_customers")

with tab5:
    st.subheader("Data quality checks")
    st.dataframe(quality, hide_index=True)
    st.subheader("Selected transactions")
    st.download_button("Download selection as CSV", df.to_csv(index=False).encode("utf-8"),
                       file_name="selected_transactions.csv", mime="text/csv")
    cols = ["transaction_id", "tx_timestamp", "account_id", "customer_name", "country", "tx_type",
            "merchant", "amount", "risk_score"]
    st.dataframe(df[cols].sort_values("tx_timestamp", ascending=False).head(500), hide_index=True)
    with st.expander("users.csv (reference table, not linked to customers or transactions)"):
        st.dataframe(users, hide_index=True)

st.caption("Built with Python · pandas · Plotly · Streamlit")
