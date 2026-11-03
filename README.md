# Cash Flow & Customer Risk dashboards

Built in Module 11 with Python, Plotly, Streamlit and Dash.

## Run it
    pip install -r requirements.txt
    streamlit run app.py          # Streamlit dashboard  -> http://localhost:8501
    python app_dash.py            # Plotly Dash dashboard -> http://127.0.0.1:8050

## Files
- dashboard_lib.py : data preparation, KPIs, insights and 16 Plotly charts (shared)
- app.py           : full Streamlit dashboard
- hello_streamlit.py : minimal Streamlit example
- app_dash.py      : Plotly Dash version
- powerbi/         : Power BI data-source script, three Python visuals, theme.json
- data/            : customers.csv, transactions.csv, users.csv

Tested with pandas 3.0, Plotly 7.1, Streamlit 1.66 and Dash 4.4.
Amounts have no currency in the source files, so none is shown.
