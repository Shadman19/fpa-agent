import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from agent.planner import parse_intent
from agent.tools import (
    summarize_revenue_vs_budget, gross_margin_pct, opex_breakdown,
    ebitda_series, cash_runway_months
)

st.set_page_config(page_title="CFO Copilot", page_icon="📊", layout="wide")
st.title("📊 FP&A CFO Copilot")

st.sidebar.header("Data Sources")
default_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPAvun4Gcow4ZNgHAAdE5b36kJgnqeVNNCQLfbzc_T6-IGLxJJsxmms9TJPDn61Q/pub?output=xlsx"
data_src = st.sidebar.text_input("Google Sheets (published) XLSX URL", value=default_url, help="Leave as is to use the assignment data.")

@st.cache_data(show_spinner=False)
def load_data(xlsx_url: str):
    try:
        df_dict = pd.read_excel(xlsx_url, sheet_name=None)
        actuals = df_dict.get("actuals")
        budget = df_dict.get("budget")
        cash = df_dict.get("cash")
        fx = df_dict.get("fx")
    except Exception:
        # Fallback to uploaded CSVs
        actuals = pd.read_csv("fixtures/actuals.csv")
        budget = pd.read_csv("fixtures/budget.csv")
        cash = pd.read_csv("fixtures/cash.csv")
        fx = pd.read_csv("fixtures/fx.csv")
    # Normalize column names
    for d in (actuals, budget):
        d.columns = [c.strip().lower() for c in d.columns]
        if "account_c" not in d.columns and "account" in d.columns:
            d.rename(columns={"account":"account_c"}, inplace=True)
        d["month"] = d["month"].astype(str).str[:7]
        d["currency"] = d["currency"].astype(str)
    cash.columns = [c.strip().lower() for c in cash.columns]
    cash["month"] = cash["month"].astype(str).str[:7]
    fx.columns = [c.strip().lower() for c in fx.columns]
    fx["month"] = fx["month"].astype(str).str[:7]
    return actuals, budget, cash, fx

actuals, budget, cash, fx = load_data(data_src)

q = st.text_input("Ask a finance question", value="What was June 2025 revenue vs budget?")

intent = parse_intent(q)
st.caption(f"Intent: **{intent.name}**  | Month: **{intent.month or 'auto'}**")

if intent.name == "revenue_vs_budget":
    # If month not given, pick latest common month
    if not intent.month:
        m = sorted(set(actuals["month"]).intersection(set(budget["month"])))[-1]
    else:
        m = intent.month
    res = summarize_revenue_vs_budget(actuals, budget, fx, m)
    st.subheader(f"Revenue vs Budget — {m}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Actual (USD)", f"{res['actual_usd']:,.0f}")
    c2.metric("Budget (USD)", f"{res['budget_usd']:,.0f}")
    delta_label = f"{res['delta_usd']:,.0f}" + (f"  ({res['delta_pct']:.1f}%)" if res['delta_pct'] is not None else "")
    c3.metric("Δ vs Budget", delta_label, delta = res['delta_usd'])
    # Bar chart
    chart_df = pd.DataFrame({"Series":["Actual","Budget"], "USD":[res['actual_usd'], res['budget_usd']]})
    fig = px.bar(chart_df, x="Series", y="USD", text="USD")
    fig.update_layout(height=360, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

elif intent.name == "gross_margin_trend":
    gm = gross_margin_pct(actuals, fx).tail(6)
    st.subheader("Gross Margin % Trend")
    fig = px.line(gm, x="month", y="gross_margin_pct", markers=True)
    fig.update_layout(yaxis_title="GM %", height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(gm)

elif intent.name == "opex_breakdown":
    m = intent.month or sorted(actuals["month"].unique())[-1]
    ob = opex_breakdown(actuals, fx, m)
    st.subheader(f"Opex Breakdown — {m}")
    if ob.empty:
        st.info("No Opex rows for selected month.")
    else:
        fig = px.pie(ob, names="account_c", values="usd")
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(ob)

elif intent.name == "ebitda_trend":
    eb = ebitda_series(actuals, fx).tail(12)
    st.subheader("EBITDA Trend (USD)")
    fig = px.line(eb, x="month", y="ebitda_usd", markers=True)
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(eb)

elif intent.name == "cash_runway":
    months = cash_runway_months(cash, actuals, fx)
    st.subheader("Cash Runway")
    if months is None:
        st.warning("Insufficient data to compute runway.")
    elif months == float("inf"):
        st.success("No burn in the last 3 months — runway is ∞.")
    else:
        st.metric("Runway (months)", f"{months:.1f}")
    st.line_chart(cash.set_index("month")["cash_usd"])

else:
    st.info("Try: 'What was June 2025 revenue vs budget?', 'Show Gross Margin % trend', 'Break down Opex by category for June 2025', 'What is our cash runway?'")

# ---- Optional: Export 1-page PDF ----
from fpdf import FPDF

def export_pdf():
    gm = gross_margin_pct(actuals, fx).tail(6)
    rb_month = sorted(set(actuals["month"]).intersection(set(budget["month"])))[-1]
    res = summarize_revenue_vs_budget(actuals, budget, fx, rb_month)
    eb = ebitda_series(actuals, fx).tail(6)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "CFO Snapshot", ln=1, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Revenue vs Budget ({rb_month}): Actual ${res['actual_usd']:,.0f}  |  Budget ${res['budget_usd']:,.0f}  |  Δ ${res['delta_usd']:,.0f}", ln=1)
    if res['delta_pct'] is not None:
        pdf.cell(0, 8, f"Delta %: {res['delta_pct']:.1f}%", ln=1)

    if not gm.empty:
        last = gm.iloc[-1]
        pdf.cell(0, 8, f"Latest GM% ({last['month']}): {last['gross_margin_pct']:.1f}%", ln=1)

    if not eb.empty:
        last_eb = eb.iloc[-1]["ebitda_usd"]
        pdf.cell(0, 8, f"Latest EBITDA (USD): {last_eb:,.0f}", ln=1)

    out = "snapshot.pdf"
    pdf.output(out)
    return out

if st.button("Export PDF (1-page)"):
    path = export_pdf()
    with open(path, "rb") as f:
        st.download_button("Download PDF", f, file_name="cfo_snapshot.pdf")
