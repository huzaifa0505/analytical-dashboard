# Power BI Python visual 3: when do transactions happen? (seaborn heatmap)
# Drag these fields into "Values":  tx_timestamp, transaction_id
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = dataset.copy()
df["tx_timestamp"] = pd.to_datetime(df["tx_timestamp"])
df["weekday"] = df["tx_timestamp"].dt.day_name()
df["block"] = pd.cut(df["tx_timestamp"].dt.hour, bins=[-1, 3, 7, 11, 15, 19, 23],
                     labels=["00-03h", "04-07h", "08-11h", "12-15h", "16-19h", "20-23h"])
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
grid = (df.pivot_table(index="weekday", columns="block", values="transaction_id", aggfunc="count", observed=False)
          .reindex(days).fillna(0).astype(int))

fig, ax = plt.subplots(figsize=(8, 4.6))
sns.heatmap(grid, annot=True, fmt="d", cmap="Blues", linewidths=0.6, linecolor="white",
            cbar_kws={"label": "Transactions"}, ax=ax)
ax.set_xlabel("")
ax.set_ylabel("")
ax.set_title("Transactions by weekday and time of day", loc="left", fontweight="bold")
plt.tight_layout()
plt.show()
