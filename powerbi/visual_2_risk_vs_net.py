# Power BI Python visual 2: risk score vs net cash flow per customer (seaborn scatter)
# Drag these fields into "Values":  account_id, risk_score, amount, country, transaction_id
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = dataset.dropna(subset=["risk_score"]).copy()      # unmatched accounts have no risk score
per_customer = (df.groupby("account_id")
                  .agg(risk_score=("risk_score", "first"), country=("country", "first"),
                       net=("amount", "sum"), n_tx=("transaction_id", "count"))
                  .reset_index())
r = per_customer["risk_score"].corr(per_customer["net"])

sns.set_theme(style="whitegrid")
fig, ax = plt.subplots(figsize=(9, 4.8))
sns.scatterplot(data=per_customer, x="risk_score", y="net", hue="country", size="n_tx",
                sizes=(25, 160), alpha=0.75, palette="colorblind", ax=ax)
ax.axhline(0, color="#888", lw=1)
ax.axvline(66, color="#666", ls=":", lw=1)
ax.set_xlabel("Risk score")
ax.set_ylabel("Net cash flow per customer")
ax.set_title(f"Risk vs net cash flow (correlation r = {r:+.2f})", loc="left", fontweight="bold")
ax.legend(frameon=False, fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
sns.despine()
plt.tight_layout()
plt.show()
