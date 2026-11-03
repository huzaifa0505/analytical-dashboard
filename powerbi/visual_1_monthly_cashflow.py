# Power BI Python visual 1: monthly inflow, outflow and net cash flow
# Drag these fields into "Values":  tx_timestamp, amount, transaction_id
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

df = dataset.copy()                                   # Power BI supplies the selected fields as "dataset"
df["tx_timestamp"] = pd.to_datetime(df["tx_timestamp"])
df["month"] = df["tx_timestamp"].dt.to_period("M").dt.to_timestamp()
m = (df.assign(inflow=df["amount"].clip(lower=0), outflow=df["amount"].clip(upper=0))
       .groupby("month")[["inflow", "outflow"]].sum())
m["net"] = m["inflow"] + m["outflow"]

fig, ax = plt.subplots(figsize=(9, 4.5))
bars_in = ax.bar(m.index, m["inflow"], width=20, color="#2F5D8A", label="Inflow")
bars_out = ax.bar(m.index, m["outflow"], width=20, color="#A40000", label="Outflow")
if df["tx_timestamp"].max() < (m.index[-1] + pd.offsets.MonthEnd(0)).normalize():   # last month incomplete?
    bars_in[-1].set_alpha(0.4)
    bars_out[-1].set_alpha(0.4)
    ax.annotate("partial month", (m.index[-1], m["inflow"].iloc[-1]), xytext=(0, 12), textcoords="offset points",
                ha="center", fontsize=8, color="#555")
ax.plot(m.index, m["net"], color="#222222", marker="o", lw=2, label="Net")
ax.axhline(0, color="#888", lw=1)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x/1e3:,.0f}K"))
ax.set_title(f"Net cash flow was negative in {(m['net'] < 0).sum()} of {len(m)} months", loc="left", fontweight="bold")
ax.legend(frameon=False, ncol=3, loc="upper left")
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
plt.tight_layout()
plt.show()
