"""
dashboard_lib.py
Shared code for the Module 11 dashboards (Streamlit, Dash and the notebook).
It holds: data loading and preparation, KPI maths, auto-written insights and 16 Plotly charts.
Every chart is a function:  chart_xxx(df) -> plotly Figure, where df is the (filtered) master table.
"""
# ===== SECTION: header =====
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    BASE = Path(__file__).resolve().parent
except NameError:                      # running inside a notebook cell
    BASE = Path.cwd()
DATA_DIR = BASE / "data"

# ---- Colour system: one meaning per colour, colour-blind friendly ----
INFLOW = "#2F5D8A"      # blue      = money coming in
OUTFLOW = "#A40000"     # dark red  = money going out
NEUTRAL = "#B7BEC7"     # grey      = context / everything that is not the message
INK = "#222222"

COUNTRY_COLORS = {
    "Germany": "#0072B2", "Pakistan": "#009E73", "UAE": "#E69F00",
    "UK": "#CC79A7", "USA": "#56B4E9", "Unmatched account": "#B7BEC7",
}
TYPE_COLORS = {
    "deposit": "#2F5D8A", "transfer_in": "#7BA3C9",
    "payment": "#A40000", "transfer_out": "#D0605E", "withdrawal": "#6E0000",
}
BAND_COLORS = {"Low": "#9ECAE1", "Medium": "#E69F00", "High": "#A40000"}

TYPE_ORDER = ["deposit", "transfer_in", "payment", "transfer_out", "withdrawal"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOUR_BLOCKS = ["00-03h", "04-07h", "08-11h", "12-15h", "16-19h", "20-23h"]


def fmt_amt(x, signed=False):
    """12345678 -> '12.35M', -4500 -> '-4K'. The files do not state a currency, so no symbol is added."""
    if x is None or pd.isna(x):
        return "n/a"
    ax = abs(x)
    if ax >= 1e6:
        s = f"{ax / 1e6:,.2f}M"
    elif ax >= 1e4:
        s = f"{ax / 1e3:,.0f}K"
    elif ax >= 1e3:
        s = f"{ax / 1e3:,.1f}K"
    else:
        s = f"{ax:,.0f}"
    return ("-" if x < 0 else ("+" if signed and x > 0 else "")) + s


def empty_fig(msg="No data for the current selection"):
    """A friendly blank chart, used when filters remove every row."""
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=14, color="#777"))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(template="plotly_white", height=300)
    return fig


def style(fig, title, sub=None, height=400, legend=True):
    """One look for every chart: message title on the left, grey sub-title, white background."""
    fig.update_layout(
        template="plotly_white", height=height,
        title=dict(text=f"<b>{title}</b>", subtitle=dict(text=sub or "", font=dict(size=12, color="#666")),
                   x=0, xanchor="left"),
        margin=dict(l=10, r=10, t=85 if sub else 60, b=10),
        font=dict(family="Arial, sans-serif", size=12, color=INK),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, title_text=""),
    )
    return fig


# ===== SECTION: data =====
def load_data(folder=DATA_DIR):
    """Read the three CSV files and parse the date columns."""
    folder = Path(folder)
    customers = pd.read_csv(folder / "customers.csv", parse_dates=["signup_date"])
    transactions = pd.read_csv(folder / "transactions.csv", parse_dates=["tx_timestamp"])
    users = pd.read_csv(folder / "users.csv")
    return customers, transactions, users


def prepare_master(customers, transactions):
    """Clean transactions, add helper columns, and attach the customer details (left join)."""
    tx = transactions.copy()
    tx["merchant"] = tx["merchant"].fillna("Unknown")              # 12% of rows have no merchant
    tx["date"] = tx["tx_timestamp"].dt.normalize()
    tx["month"] = tx["tx_timestamp"].dt.to_period("M").dt.to_timestamp()
    tx["weekday"] = tx["tx_timestamp"].dt.day_name()
    tx["hour"] = tx["tx_timestamp"].dt.hour
    tx["hour_block"] = pd.cut(tx["hour"], bins=[-1, 3, 7, 11, 15, 19, 23], labels=HOUR_BLOCKS).astype(str)
    tx["direction"] = np.where(tx["amount"] >= 0, "Inflow", "Outflow")
    tx["abs_amount"] = tx["amount"].abs()

    cust = customers.rename(columns={"customer_id": "account_id"}).copy()
    cust["customer_name"] = cust["first_name"] + " " + cust["last_name"]
    cust["risk_band"] = pd.cut(cust["risk_score"], bins=[-0.01, 33, 66, 100],
                               labels=["Low", "Medium", "High"]).astype(str)

    master = tx.merge(cust, on="account_id", how="left")           # left join keeps ALL transactions
    master["is_matched"] = master["country"].notna()               # False = account id not in customers.csv
    master["country"] = master["country"].fillna("Unmatched account")
    master["risk_band"] = master["risk_band"].fillna("Unknown")
    master["customer_name"] = master["customer_name"].fillna("Account " + master["account_id"].astype(str))
    return master.sort_values("tx_timestamp").reset_index(drop=True)


def customer_summary(df):
    """One row per *matched* customer with activity in df (unmatched accounts have no customer record)."""
    m = df[df["is_matched"]]
    if m.empty:
        return pd.DataFrame(columns=["account_id", "customer_name", "country", "city", "signup_date",
                                     "risk_score", "risk_band", "n_tx", "inflow", "outflow", "net", "volume"])
    g = m.assign(inflow=m["amount"].clip(lower=0), outflow=m["amount"].clip(upper=0).abs()).groupby("account_id")
    out = g.agg(customer_name=("customer_name", "first"), country=("country", "first"), city=("city", "first"),
                signup_date=("signup_date", "first"), risk_score=("risk_score", "first"),
                risk_band=("risk_band", "first"), n_tx=("transaction_id", "count"),
                inflow=("inflow", "sum"), outflow=("outflow", "sum")).reset_index()
    out["net"] = out["inflow"] - out["outflow"]
    out["volume"] = out["inflow"] + out["outflow"]
    return out


def data_quality(customers, transactions, users):
    """A table of checks: what we found in the raw files and what we did about it."""
    t = transactions
    matched = t["account_id"].isin(customers["customer_id"])
    j = t[matched].merge(customers, left_on="account_id", right_on="customer_id")
    before = (j["tx_timestamp"] < j["signup_date"]).mean()
    last = t["tx_timestamp"].max()
    month_end = (last.to_period("M").to_timestamp("M")).normalize()
    shared = set(users["email"]) & set(customers["email"])
    rows = [
        ("Rows loaded", f"{len(t):,} transactions, {len(customers):,} customers, {len(users):,} users",
         "Loaded as is"),
        ("Accounts without a customer record",
         f"{t.loc[~matched, 'account_id'].nunique()} of {t['account_id'].nunique()} account IDs "
         f"({(~matched).mean():.0%} of transactions)",
         "Kept (left join) and labelled 'Unmatched account'; customer-level charts use matched accounts only"),
        ("Missing merchant", f"{t['merchant'].isna().mean():.0%} of transactions", "Filled with 'Unknown'"),
        ("Transaction signs", "Deposits / transfer_in are positive; payments / withdrawals / transfer_out negative",
         "Used the sign of amount as the money direction"),
        ("Transactions dated before the customer signed up", f"{before:.0%} of matched transactions",
         "Flagged only; not removed (ask the data owner)"),
        ("Last month is incomplete", f"Data ends on {last:%d %b %Y}" + (" (before month end)" if last < month_end else ""),
         "Faded / marked as 'partial month' in monthly charts"),
        ("Currency", "Not stated in the files", "Amounts shown as plain numbers (no symbol)"),
        ("users.csv", "Shares no email or city with customers.csv" if not shared else "Some emails shared",
         "Cannot be joined; shown as a separate reference table"),
    ]
    return pd.DataFrame(rows, columns=["Check", "What we found", "What we did"])


def kpis(df):
    """Headline numbers for the KPI cards."""
    if df.empty:
        return dict(transactions=0, accounts=0, inflow=0.0, outflow=0.0, net=0.0, avg_tx=0.0,
                    customers=0, avg_risk=np.nan, high_risk_share=np.nan, unmatched_share=np.nan)
    inflow = df.loc[df["amount"] > 0, "amount"].sum()
    outflow = -df.loc[df["amount"] < 0, "amount"].sum()
    cs = customer_summary(df)
    return dict(
        transactions=len(df), accounts=df["account_id"].nunique(), inflow=inflow, outflow=outflow,
        net=inflow - outflow, avg_tx=df["abs_amount"].mean(), customers=len(cs),
        avg_risk=cs["risk_score"].mean() if len(cs) else np.nan,
        high_risk_share=(cs["risk_band"] == "High").mean() if len(cs) else np.nan,
        unmatched_share=(~df["is_matched"]).mean(),
    )


def insights(df):
    """Plain-English takeaways that update with the filters (data storytelling)."""
    if df.empty:
        return ["No data for this selection."]
    k = kpis(df)
    out = []
    ratio = k["outflow"] / k["inflow"] if k["inflow"] else np.nan
    out.append(f"Net cash flow is **{fmt_amt(k['net'], signed=True)}**: outflows are "
               f"{fmt_amt(k['outflow'])} against inflows of {fmt_amt(k['inflow'])}"
               + (f" ({ratio:.2f} out for every 1 in)." if pd.notna(ratio) else "."))
    o = df[df["amount"] < 0].groupby("merchant")["abs_amount"].sum().sort_values(ascending=False)
    if len(o):
        out.append(f"**{o.index[0]}** takes the largest share of outflows ({o.iloc[0] / o.sum():.0%}).")
    wd = df.groupby("weekday").size()
    out.append(f"The busiest weekday is **{wd.idxmax()}** ({wd.max():,} transactions).")
    cs = customer_summary(df)
    if len(cs):
        r = cs.groupby("country")["risk_score"].mean().sort_values(ascending=False)
        out.append(f"**{r.index[0]}** has the highest average customer risk score ({r.iloc[0]:.0f}); "
                   f"{k['high_risk_share']:.0%} of active customers are in the High-risk band.")
    if k["unmatched_share"] > 0:
        out.append(f"{k['unmatched_share']:.0%} of these transactions belong to accounts with no customer record.")
    return out


# ===== SECTION: charts =====
# ----- CHART: monthly_cashflow -----
def chart_monthly_cashflow(df):
    """Bars: inflow (up) and outflow (down) per month; line: net cash flow."""
    if df.empty:
        return empty_fig()
    m = (df.assign(inflow=df["amount"].clip(lower=0), outflow=df["amount"].clip(upper=0))
           .groupby("month")[["inflow", "outflow"]].sum().reset_index())
    m["net"] = m["inflow"] + m["outflow"]
    last_day = df["tx_timestamp"].max()
    last_month = m["month"].max()
    partial = last_day < (last_month + pd.offsets.MonthEnd(0)).normalize()
    opacity = [0.4 if (partial and mth == last_month) else 1.0 for mth in m["month"]]

    fig = go.Figure()
    fig.add_bar(x=m["month"], y=m["inflow"], name="Inflow", marker_color=INFLOW, marker_opacity=opacity)
    fig.add_bar(x=m["month"], y=m["outflow"], name="Outflow", marker_color=OUTFLOW, marker_opacity=opacity)
    fig.add_scatter(x=m["month"], y=m["net"], name="Net", mode="lines+markers",
                    line=dict(color=INK, width=2.5), marker=dict(size=6))
    fig.update_layout(barmode="relative")
    fig.update_xaxes(tickformat="%b\n%Y", dtick="M1" if len(m) <= 14 else "M2")
    fig.update_yaxes(title="Amount", zeroline=True, zerolinecolor="#888")
    if partial:
        fig.add_annotation(x=last_month, y=float(m["inflow"].iloc[-1]), ax=0, ay=-40, showarrow=True, arrowhead=2,
                           text=f"Partial month<br>(data to {last_day:%d %b})", font=dict(size=11, color="#555"))
    neg = int((m["net"] < 0).sum())
    return style(fig, f"Outflows exceeded inflows in {neg} of {len(m)} months",
                 "Monthly inflow (up), outflow (down) and net cash flow. A faded bar means an incomplete month.",
                 height=430)


# ----- CHART: cumulative_balance -----
def chart_cumulative_balance(df):
    """Running total of net cash flow over time."""
    if df.empty:
        return empty_fig()
    cum = df.groupby("date")["amount"].sum().sort_index().cumsum()
    end = cum.iloc[-1]
    color = OUTFLOW if end < 0 else INFLOW
    fill = "rgba(164,0,0,0.10)" if end < 0 else "rgba(47,93,138,0.12)"
    fig = go.Figure(go.Scatter(x=cum.index, y=cum.values, mode="lines", line=dict(color=color, width=2.5),
                               fill="tozeroy", fillcolor=fill, name="Cumulative net",
                               hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f}<extra></extra>"))
    fig.add_hline(y=0, line_color="#888", line_width=1)
    fig.add_annotation(x=cum.index[-1], y=end, text=f"<b>{fmt_amt(end)}</b>", showarrow=True, ax=-35, ay=-30,
                       font=dict(color=color, size=13))
    fig.update_yaxes(title="Cumulative net amount")
    fig.update_xaxes(tickformat="%b %Y")
    return style(fig, f"The net cash position ends at {fmt_amt(end)}",
                 "Cumulative net cash flow of every account in view", legend=False)


# ----- CHART: waterfall_types -----
def chart_waterfall_types(df):
    """Cash-flow bridge: how each transaction type moves the net position (a P&L-style waterfall)."""
    if df.empty:
        return empty_fig()
    s = df.groupby("tx_type")["amount"].sum().reindex(TYPE_ORDER).fillna(0.0)
    labels = [t.replace("_", " ").title() for t in TYPE_ORDER] + ["Net cash flow"]
    fig = go.Figure()
    running, tops = 0.0, []
    for i, (t, v) in enumerate(s.items()):
        new = running + v
        fig.add_bar(x=[labels[i]], y=[abs(v)], base=[min(running, new)],
                    marker_color=INFLOW if v >= 0 else OUTFLOW, showlegend=False,
                    hovertemplate=f"{labels[i]}: {v:,.0f}<extra></extra>")
        tops.append(max(running, new))
        if i < len(s):                                              # connector to the next bar
            fig.add_shape(type="line", x0=i + 0.4, x1=i + 0.6, y0=new, y1=new, line=dict(color="#777", width=1))
        running = new
    fig.add_bar(x=[labels[-1]], y=[running], base=[0], marker_color=INK, showlegend=False,
                hovertemplate=f"Net cash flow: {running:,.0f}<extra></extra>")
    tops.append(max(running, 0))
    for lab, v, top in zip(labels, list(s.values) + [running], tops):
        fig.add_annotation(x=lab, y=top, text=f"<b>{fmt_amt(v, signed=lab != 'Net cash flow')}</b>",
                           showarrow=False, yshift=12, font=dict(size=11))
    fig.update_yaxes(title="Amount", zeroline=True, zerolinecolor="#888")
    fig.update_layout(barmode="overlay")
    return style(fig, f"Net cash flow of {fmt_amt(running)} after all transaction types",
                 "Blue = money in, red = money out, dark bar = result", legend=False, height=430)


# ----- CHART: top_merchants -----
def chart_top_merchants(df, n=8):
    """Which merchants receive most of the outflows."""
    o = df[df["amount"] < 0].groupby("merchant")["abs_amount"].sum().sort_values(ascending=False)
    if o.empty:
        return empty_fig("No outflows in the current selection")
    top = o.head(n).iloc[::-1]
    colors = [NEUTRAL] * (len(top) - 1) + [OUTFLOW]
    fig = go.Figure(go.Bar(y=top.index, x=top.values, orientation="h", marker_color=colors,
                           text=[f"{fmt_amt(v)}  ({v / o.sum():.0%})" for v in top.values], textposition="outside",
                           hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
    fig.update_xaxes(title="Total outflow", range=[0, top.max() * 1.25])
    return style(fig, f"{o.index[0]} receives the largest share of outflows ({o.iloc[0] / o.sum():.0%})",
                 "Total outflow by merchant (payments, withdrawals and transfers out)", legend=False)


# ----- CHART: activity_heatmap -----
def chart_activity_heatmap(df):
    """When do transactions happen? Weekday x time-of-day heatmap."""
    if df.empty:
        return empty_fig()
    p = (df.pivot_table(index="weekday", columns="hour_block", values="transaction_id", aggfunc="count")
           .reindex(index=WEEKDAYS, columns=HOUR_BLOCKS).fillna(0).astype(int))
    fig = go.Figure(go.Heatmap(z=p.values, x=p.columns, y=p.index, colorscale="Blues", text=p.values,
                               texttemplate="%{text}", colorbar=dict(title="Count"),
                               hovertemplate="%{y} %{x}: %{z} transactions<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    day, block = np.unravel_index(p.values.argmax(), p.shape)
    return style(fig, f"Busiest slot: {p.index[day]} {p.columns[block]} ({p.values.max()} transactions)",
                 "Number of transactions by weekday and time of day", legend=False)


# ----- CHART: amount_by_type -----
def chart_amount_by_type(df):
    """Distribution of transaction sizes for each type (box plot)."""
    if df.empty:
        return empty_fig()
    fig = px.box(df, x="tx_type", y="abs_amount", color="tx_type", color_discrete_map=TYPE_COLORS,
                 category_orders={"tx_type": TYPE_ORDER}, points=False)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Transaction size (absolute amount)")
    med = df.groupby("tx_type")["abs_amount"].median()
    return style(fig, f"Typical transaction size is similar across types (medians {fmt_amt(med.min())} to {fmt_amt(med.max())})",
                 "Box = middle 50% of transactions, line = median", legend=False)


# ----- CHART: daily_activity -----
def chart_daily_activity(df):
    """Transactions per day with a 7-day moving average."""
    if df.empty:
        return empty_fig()
    d = df.groupby("date").size()
    d = d.reindex(pd.date_range(d.index.min(), d.index.max()), fill_value=0)
    ma = d.rolling(7, min_periods=1).mean()
    fig = go.Figure()
    fig.add_bar(x=d.index, y=d.values, name="Daily count", marker_color=NEUTRAL)
    fig.add_scatter(x=ma.index, y=ma.values, name="7-day average", mode="lines", line=dict(color=INFLOW, width=2.5))
    fig.update_yaxes(title="Transactions per day")
    fig.update_xaxes(tickformat="%b %Y")
    return style(fig, f"About {d.mean():.0f} transactions a day; busiest day had {d.max()}",
                 "Daily number of transactions and 7-day moving average")


# ----- CHART: customers_by_country -----
def chart_customers_by_country(df):
    """How many active customers per country, coloured by their average risk."""
    cs = customer_summary(df)
    if cs.empty:
        return empty_fig("No matched customers in the current selection")
    g = (cs.groupby("country").agg(customers=("account_id", "count"), avg_risk=("risk_score", "mean"))
           .sort_values("customers", ascending=False).reset_index())
    fig = px.bar(g, x="country", y="customers", color="avg_risk", text="customers",
                 color_continuous_scale="Reds", range_color=(30, 70))
    fig.update_traces(textposition="outside")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Active customers", range=[0, g["customers"].max() * 1.15])
    fig.update_coloraxes(colorbar_title="Avg risk")
    riskiest = g.sort_values("avg_risk").iloc[-1]
    return style(fig, f"{g['country'].iloc[0]} has the most customers; {riskiest['country']} has the highest average risk",
                 "Customers with activity in the selection. Darker red = higher average risk score", legend=False)


# ----- CHART: risk_distribution -----
def chart_risk_distribution(df):
    """Histogram of customer risk scores split into Low / Medium / High bands."""
    cs = customer_summary(df)
    if cs.empty:
        return empty_fig("No matched customers in the current selection")
    fig = px.histogram(cs, x="risk_score", color="risk_band", nbins=20, color_discrete_map=BAND_COLORS,
                       category_orders={"risk_band": ["Low", "Medium", "High"]})
    for x in (33, 66):
        fig.add_vline(x=x, line_dash="dot", line_color="#666")
    fig.update_xaxes(title="Risk score (0 = safest, 100 = riskiest)", range=[0, 100])
    fig.update_yaxes(title="Customers")
    hi = (cs["risk_band"] == "High").sum()
    return style(fig, f"{hi} customers ({hi / len(cs):.0%}) are in the High-risk band (score above 66)",
                 "Distribution of customer risk scores")


# ----- CHART: risk_by_country -----
def chart_risk_by_country(df):
    """Risk score spread per country (box plot with every customer shown)."""
    cs = customer_summary(df)
    if cs.empty:
        return empty_fig("No matched customers in the current selection")
    fig = px.box(cs, x="country", y="risk_score", color="country", points="all",
                 color_discrete_map=COUNTRY_COLORS, hover_name="customer_name")
    fig.add_hline(y=66, line_dash="dot", line_color="#666", annotation_text="High-risk line (66)")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Risk score")
    med = cs.groupby("country")["risk_score"].median().sort_values(ascending=False)
    return style(fig, f"{med.index[0]} has the highest median risk score ({med.iloc[0]:.0f})",
                 "Each dot is a customer; box = middle 50%", legend=False)


# ----- CHART: signups -----
def chart_signups(df):
    """New customers per month and the growing customer base."""
    cs = customer_summary(df)
    if cs.empty:
        return empty_fig("No matched customers in the current selection")
    s = cs.groupby(cs["signup_date"].dt.to_period("M").dt.to_timestamp()).size().sort_index()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=s.index, y=s.values, name="New customers per month", marker_color=NEUTRAL, secondary_y=False)
    fig.add_scatter(x=s.index, y=s.cumsum().values, name="Total customers", mode="lines", line=dict(color=INFLOW, width=3),
                    secondary_y=True)
    fig.update_yaxes(title_text="New per month", secondary_y=False)
    fig.update_yaxes(title_text="Total customers", secondary_y=True, showgrid=False)
    fig.update_xaxes(tickformat="%b %Y")
    return style(fig, f"The customer base grew to {len(cs)}; the best month brought {s.max()} sign-ups",
                 "Sign-ups by month (bars) and cumulative customers (line)")


# ----- CHART: country_net -----
def chart_country_net(df):
    """Net cash flow per country; the grey bar is accounts with no customer record."""
    if df.empty:
        return empty_fig()
    g = df.groupby("country")["amount"].sum().sort_values(ascending=False)
    colors = [NEUTRAL if c == "Unmatched account" else (INFLOW if v >= 0 else OUTFLOW) for c, v in g.items()]
    fig = go.Figure(go.Bar(y=g.index, x=g.values, orientation="h", marker_color=colors,
                           text=[fmt_amt(v, signed=True) for v in g.values], textposition="outside",
                           hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    fig.add_vline(x=0, line_color="#555")
    lo, hi = float(min(g.min(), 0)), float(max(g.max(), 0))
    pad = (hi - lo) * 0.2 or 1
    fig.update_xaxes(title="Net cash flow", range=[lo - pad, hi + pad])
    matched = g[g.index != "Unmatched account"]
    head = (f"{matched.idxmin()} has the largest net outflow ({fmt_amt(matched.min())})" if len(matched) else "Net cash flow by country")
    return style(fig, head, "Grey bar = accounts that are not in customers.csv (country unknown)", legend=False)


# ----- CHART: country_type_heatmap -----
def chart_country_type_heatmap(df):
    """Net amount for every country x transaction type (diverging colours, centred on zero)."""
    if df.empty:
        return empty_fig()
    p = (df.pivot_table(index="country", columns="tx_type", values="amount", aggfunc="sum")
           .reindex(columns=TYPE_ORDER).fillna(0))
    fig = go.Figure(go.Heatmap(z=p.values, x=[c.replace("_", " ") for c in p.columns], y=p.index, zmid=0,
                               colorscale=[[0, OUTFLOW], [0.5, "#FFFFFF"], [1, INFLOW]],
                               text=[[fmt_amt(v) for v in row] for row in p.values], texttemplate="%{text}",
                               colorbar=dict(title="Net"), hovertemplate="%{y} / %{x}: %{z:,.0f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return style(fig, "Where the money moves: net amount by country and transaction type",
                 "Blue = net inflow, red = net outflow", legend=False)


# ----- CHART: treemap -----
def chart_treemap(df):
    """Outflows split by country, then merchant (size = amount)."""
    o = df[df["amount"] < 0]
    if o.empty:
        return empty_fig("No outflows in the current selection")
    colors = dict(COUNTRY_COLORS)
    colors["(?)"] = "#EEF1F5"                                       # colour of the root box
    fig = px.treemap(o, path=[px.Constant("All outflows"), "country", "merchant"], values="abs_amount",
                     color="country", color_discrete_map=colors)
    fig.update_traces(textinfo="label+percent root", root_color="#EEF1F5",
                      hovertemplate="%{label}<br>%{value:,.0f}<extra></extra>")
    return style(fig, f"Outflows by country and merchant: {fmt_amt(o['abs_amount'].sum())} in total",
                 "Bigger box = more money out. Click a country to zoom in.", legend=False, height=450)


# ----- CHART: risk_vs_flow -----
def chart_risk_vs_flow(df):
    """Risk (x) vs return-like outcome (net cash flow, y), bubble size = number of transactions."""
    cs = customer_summary(df)
    if len(cs) < 3:
        return empty_fig("Need at least 3 matched customers")
    r = cs["risk_score"].corr(cs["net"])
    label = "no clear relationship" if abs(r) < 0.2 else ("positive relationship" if r > 0 else "negative relationship")
    fig = px.scatter(cs, x="risk_score", y="net", size="n_tx", color="country", hover_name="customer_name",
                     color_discrete_map=COUNTRY_COLORS, size_max=18, opacity=0.75,
                     hover_data={"risk_score": ":.1f", "net": ":,.0f", "n_tx": True, "country": False})
    fig.add_hline(y=0, line_color="#888", line_width=1)
    fig.add_vline(x=66, line_dash="dot", line_color="#666", annotation_text="High risk")
    fig.update_xaxes(title="Risk score", range=[0, 100])
    fig.update_yaxes(title="Net cash flow per customer")
    return style(fig, f"Risk score vs net cash flow: {label} (r = {r:+.2f})",
                 "Each bubble is a customer; bubble size = number of transactions", height=450)


# ----- CHART: top_customers -----
def chart_top_customers(df, n=10):
    """Customers with the biggest transaction volume, split into money in and money out."""
    cs = customer_summary(df)
    if cs.empty:
        return empty_fig("No matched customers in the current selection")
    top = cs.nlargest(n, "volume").iloc[::-1]
    names = top["customer_name"] + " (#" + top["account_id"].astype(str) + ")"
    fig = go.Figure()
    fig.add_bar(y=names, x=top["inflow"], name="Inflow", orientation="h", marker_color=INFLOW)
    fig.add_bar(y=names, x=top["outflow"], name="Outflow", orientation="h", marker_color=OUTFLOW)
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Transaction volume (in + out)")
    share = top["volume"].sum() / cs["volume"].sum()
    return style(fig, f"The top {len(top)} customers handle {share:.0%} of matched transaction volume",
                 "Stacked: money in (blue) and money out (red)", height=450)


ALL_CHARTS = [
    chart_monthly_cashflow, chart_cumulative_balance, chart_waterfall_types, chart_top_merchants,
    chart_activity_heatmap, chart_amount_by_type, chart_daily_activity, chart_customers_by_country,
    chart_risk_distribution, chart_risk_by_country, chart_signups, chart_country_net,
    chart_country_type_heatmap, chart_treemap, chart_risk_vs_flow, chart_top_customers,
]
