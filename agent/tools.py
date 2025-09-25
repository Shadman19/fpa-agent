import pandas as pd
import numpy as np
from typing import Tuple, Dict

REVENUE_ACCT = "Revenue"
COGS_ACCT = "COGS"

def _usd(df: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """Convert amounts to USD using fx[rate_to_usd] on (month, currency)."""
    fx_idx = fx.set_index(["month","currency"])["rate_to_usd"]
    df = df.copy()
    # If amount column differs (e.g., cash), pass through unchanged
    amt_col = "amount" if "amount" in df.columns else "cash_usd" if "cash_usd" in df.columns else None
    if amt_col is None:
        return df
    rates = df.set_index(["month","currency"]).index.map(lambda k: fx_idx.get(k, 1.0))
    df["usd"] = df[amt_col].values * np.array(list(rates))
    return df

def opex_mask(account: str) -> bool:
    return account.startswith("Opex:")

def summarize_revenue_vs_budget(actuals: pd.DataFrame, budget: pd.DataFrame, fx: pd.DataFrame, month: str, entity: str|None=None) -> Dict:
    a = actuals.copy()
    b = budget.copy()
    if entity:
        a = a[a["entity"].eq(entity)]
        b = b[b["entity"].eq(entity)]
    a = a[(a["month"].eq(month)) & (a["account_c"].eq(REVENUE_ACCT))]
    b = b[(b["month"].eq(month)) & (b["account_c"].eq(REVENUE_ACCT))]
    a = _usd(a, fx)
    b = _usd(b, fx)
    actual = a["usd"].sum() if not a.empty else 0.0
    budg = b["usd"].sum() if not b.empty else 0.0
    diff = actual - budg
    perc = (diff / budg * 100.0) if budg else None
    return {"month": month, "entity": entity or "All", "actual_usd": actual, "budget_usd": budg, "delta_usd": diff, "delta_pct": perc}

def gross_margin_pct(actuals: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    a = _usd(actuals, fx)
    grp = a.groupby(["month","account_c"], as_index=False)["usd"].sum()
    rev = grp[grp["account_c"].eq(REVENUE_ACCT)].set_index("month")["usd"]
    cogs = grp[grp["account_c"].eq(COGS_ACCT)].set_index("month")["usd"]
    months = sorted(set(rev.index).union(set(cogs.index)))
    data = []
    for m in months:
        R = rev.get(m, 0.0)
        C = cogs.get(m, 0.0)
        gm = ((R - C)/R*100.0) if R else None
        data.append({"month": m, "revenue_usd": R, "cogs_usd": C, "gross_margin_pct": gm})
    return pd.DataFrame(data).sort_values("month")

def opex_breakdown(actuals: pd.DataFrame, fx: pd.DataFrame, month: str) -> pd.DataFrame:
    a = _usd(actuals, fx)
    opex = a[(a["month"].eq(month)) & (a["account_c"].map(opex_mask))]
    if opex.empty:
        return pd.DataFrame(columns=["account_c","usd"])
    return opex.groupby("account_c", as_index=False)["usd"].sum().sort_values("usd", ascending=False)

def ebitda_series(actuals: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    a = _usd(actuals, fx)
    grp = a.groupby(["month","account_c"], as_index=False)["usd"].sum()
    rev = grp[grp["account_c"].eq(REVENUE_ACCT)].set_index("month")["usd"]
    cogs = grp[grp["account_c"].eq(COGS_ACCT)].set_index("month")["usd"]
    opex = grp[grp["account_c"].map(opex_mask)].groupby("month")["usd"].sum()
    months = sorted(set(rev.index) | set(cogs.index) | set(opex.index))
    rows = []
    for m in months:
        R = rev.get(m, 0.0)
        C = cogs.get(m, 0.0)
        O = opex.get(m, 0.0)
        ebitda = R - C - O
        rows.append({"month": m, "revenue_usd": R, "cogs_usd": C, "opex_usd": O, "ebitda_usd": ebitda})
    return pd.DataFrame(rows).sort_values("month")

def cash_runway_months(cash: pd.DataFrame, actuals: pd.DataFrame, fx: pd.DataFrame) -> float|None:
    # Net burn = -(EBITDA) if EBITDA is negative; otherwise zero burn
    eb = ebitda_series(actuals, fx).set_index("month")
    last3 = eb.tail(3)["ebitda_usd"]
    if last3.empty:
        return None
    avg_burn = -last3[last3 < 0].mean() if (last3 < 0).any() else 0.0
    if avg_burn is None or avg_burn == 0.0:
        return np.inf
    latest_cash = cash.sort_values("month")["cash_usd"].iloc[-1]
    return latest_cash / avg_burn
