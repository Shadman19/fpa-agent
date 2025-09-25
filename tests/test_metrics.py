import pandas as pd
from agent.tools import summarize_revenue_vs_budget, gross_margin_pct, ebitda_series, cash_runway_months

def load_fx():
    return pd.read_csv("fixtures/fx.csv")

def load_actuals():
    return pd.read_csv("fixtures/actuals.csv")

def load_budget():
    return pd.read_csv("fixtures/budget.csv")

def load_cash():
    return pd.read_csv("fixtures/cash.csv")

def test_revenue_vs_budget_june_2025():
    a, b, fx = load_actuals(), load_budget(), load_fx()
    res = summarize_revenue_vs_budget(a, b, fx, "2025-06")
    assert round(res["actual_usd"], 2) == 460000 + 115000*1.09
    assert res["budget_usd"] > 0

def test_gm_pct_exists():
    a, fx = load_actuals(), load_fx()
    gm = gross_margin_pct(a, fx)
    assert "gross_margin_pct" in gm.columns
    assert not gm.empty

def test_ebitda_and_runway():
    a, fx, cash = load_actuals(), load_fx(), load_cash()
    eb = ebitda_series(a, fx)
    assert "ebitda_usd" in eb.columns
    months = cash_runway_months(cash, a, fx)
    assert months is not None
