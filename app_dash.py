"""
app_dash.py - the same dashboard idea built with Plotly Dash.
Run from this folder with:   python app_dash.py      then open http://127.0.0.1:8050
"""
import pandas as pd
from dash import Dash, Input, Output, dash_table, dcc, html

import dashboard_lib as dl

# ------------------------------------------------------------------ data (loaded once when the server starts)
customers, transactions, users = dl.load_data()
master = dl.prepare_master(customers, transactions)
MIN_D, MAX_D = master["date"].min().date(), master["date"].max().date()
COUNTRIES = sorted(master["country"].unique())

# ------------------------------------------------------------------ which charts go where: (component id, chart function)
OVERVIEW = [
    ("g-monthly", dl.chart_monthly_cashflow),
    ("g-cumulative", dl.chart_cumulative_balance),
    ("g-waterfall", dl.chart_waterfall_types),
    ("g-merchants", dl.chart_top_merchants),
    ("g-heatmap", dl.chart_activity_heatmap),
    ("g-country", dl.chart_country_net),
]
CUSTOMERS = [
    ("g-risk-flow", dl.chart_risk_vs_flow),
    ("g-risk-dist", dl.chart_risk_distribution),
    ("g-top-customers", dl.chart_top_customers),
    ("g-cust-country", dl.chart_customers_by_country),
]
GRAPHS = OVERVIEW + CUSTOMERS
TABLE_COLS = ["transaction_id", "tx_timestamp", "customer_name", "country", "tx_type", "merchant", "amount"]

# ------------------------------------------------------------------ small styling helpers
CARD = {"background": "#F7F8FA", "borderLeft": "5px solid #A40000", "padding": "10px 16px",
        "borderRadius": "6px", "flex": "1", "minWidth": "150px"}
GRID = {"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(420px, 1fr))", "gap": "12px"}


def kpi_card(label, value):
    return html.Div([html.Div(label, style={"fontSize": "13px", "color": "#555"}),
                     html.Div(value, style={"fontSize": "26px", "fontWeight": "bold", "color": "#222"})], style=CARD)


def graph(component_id):
    return dcc.Graph(id=component_id, config={"displaylogo": False})


# ------------------------------------------------------------------ layout = WHAT the page looks like
app = Dash(__name__, title="Cash Flow & Customer Risk (Dash)")
server = app.server                      # used by production servers, e.g.  gunicorn app_dash:server

app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "maxWidth": "1300px", "margin": "0 auto", "padding": "16px"},
    children=[
        html.H1("Cash Flow & Customer Risk Dashboard", style={"color": "#A40000", "marginBottom": "4px"}),
        html.Div("Built with Plotly Dash. Change a filter and every number and chart updates.",
                 style={"color": "#666", "marginBottom": "14px"}),
        # ---- filters
        html.Div(style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginBottom": "14px"}, children=[
            html.Div([html.Label("Date range"),
                      dcc.DatePickerRange(id="date-range", min_date_allowed=MIN_D, max_date_allowed=MAX_D,
                                          start_date=MIN_D, end_date=MAX_D)]),
            html.Div([html.Label("Country"),
                      dcc.Dropdown(id="country", options=COUNTRIES, value=COUNTRIES, multi=True)],
                     style={"minWidth": "320px", "flex": "1"}),
            html.Div([html.Label("Transaction type"),
                      dcc.Dropdown(id="types", options=dl.TYPE_ORDER, value=dl.TYPE_ORDER, multi=True)],
                     style={"minWidth": "320px", "flex": "1"}),
        ]),
        # ---- KPI cards (filled by the callback)
        html.Div(id="kpi-row", style={"display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "10px"}),
        html.Div(id="note", style={"color": "#666", "fontSize": "13px", "marginBottom": "6px"}),
        # ---- tabs
        dcc.Tabs([
            dcc.Tab(label="Overview", children=[html.Div([graph(i) for i, _ in OVERVIEW], style=GRID)]),
            dcc.Tab(label="Customers & risk", children=[html.Div([graph(i) for i, _ in CUSTOMERS], style=GRID)]),
            dcc.Tab(label="Biggest transactions", children=[
                dash_table.DataTable(id="tbl", columns=[{"name": c, "id": c} for c in TABLE_COLS], page_size=12,
                                     sort_action="native", style_header={"backgroundColor": "#A40000", "color": "white"},
                                     style_cell={"padding": "6px", "fontSize": "13px"})]),
        ]),
    ],
)


# ------------------------------------------------------------------ logic = a plain function we can test without a server
def build_dashboard(start, end, countries, types):
    """Filter the data and return everything the page needs: KPI cards, note, 10 figures, table rows."""
    countries, types = countries or [], types or []
    df = master[master["date"].between(pd.Timestamp(start), pd.Timestamp(end))
                & master["country"].isin(countries) & master["tx_type"].isin(types)]
    if df.empty:
        cards = [kpi_card("Transactions", "0")]
        return (cards, "No transactions match these filters.", *[dl.empty_fig() for _ in GRAPHS], [])
    k = dl.kpis(df)
    cards = [kpi_card("Transactions", f"{k['transactions']:,}"), kpi_card("Total inflow", dl.fmt_amt(k["inflow"])),
             kpi_card("Total outflow", dl.fmt_amt(k["outflow"])),
             kpi_card("Net cash flow", dl.fmt_amt(k["net"], signed=True)),
             kpi_card("Avg risk score", "n/a" if pd.isna(k["avg_risk"]) else f"{k['avg_risk']:.1f}")]
    note = f"{len(df):,} of {len(master):,} transactions selected. Takeaway: " + dl.insights(df)[0].replace("**", "")
    figs = [fn(df) for _, fn in GRAPHS]
    rows = df.nlargest(200, "abs_amount")[TABLE_COLS].assign(
        tx_timestamp=lambda d: d["tx_timestamp"].dt.strftime("%Y-%m-%d %H:%M")).to_dict("records")
    return (cards, note, *figs, rows)


# ------------------------------------------------------------------ callback = connects the filters (Inputs) to the page (Outputs)
@app.callback(
    [Output("kpi-row", "children"), Output("note", "children")]
    + [Output(i, "figure") for i, _ in GRAPHS] + [Output("tbl", "data")],
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("country", "value"), Input("types", "value")],
)
def update_dashboard(start, end, countries, types):
    return build_dashboard(start, end, countries, types)


if __name__ == "__main__":
    app.run(debug=True)
