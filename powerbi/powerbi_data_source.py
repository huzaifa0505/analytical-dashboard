# ---------------------------------------------------------------
# Power BI  ->  Home > Get data > More > Python script  -> paste this whole file.
# Power BI will offer every pandas DataFrame defined below as a table.
# ---------------------------------------------------------------
import numpy as np
import pandas as pd

FOLDER = r"D:/Courses/python scripts/dashboard_project/data"          # <- folder that contains the three CSV files

customers = pd.read_csv(FOLDER + "/customers.csv", parse_dates=["signup_date"])
transactions = pd.read_csv(FOLDER + "/transactions.csv", parse_dates=["tx_timestamp"])
users = pd.read_csv(FOLDER + "/users.csv")

# --- small clean-up that is easier in Python than in the Power BI ribbon ---
transactions["merchant"] = transactions["merchant"].fillna("Unknown")
transactions["direction"] = np.where(transactions["amount"] >= 0, "Inflow", "Outflow")
transactions["abs_amount"] = transactions["amount"].abs()
customers["risk_band"] = pd.cut(customers["risk_score"], bins=[-0.01, 33, 66, 100],
                                labels=["Low", "Medium", "High"]).astype(str)
customers["customer_name"] = customers["first_name"] + " " + customers["last_name"]