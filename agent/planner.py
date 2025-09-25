import re
from dataclasses import dataclass

@dataclass
class Intent:
    name: str
    month: str|None = None
    extra: dict = None

def parse_intent(q: str) -> Intent:
    s = q.lower().strip()
    # Month pattern like 2025-06 or "june 2025"
    m = re.search(r"(20\d{2}-\d{2})", s)
    month = m.group(1) if m else None
    if "revenue" in s and "budget" in s:
        return Intent("revenue_vs_budget", month=month)
    if "gross margin" in s:
        return Intent("gross_margin_trend", month=month)
    if "opex" in s and ("breakdown" in s or "by category" in s):
        return Intent("opex_breakdown", month=month)
    if "ebitda" in s:
        return Intent("ebitda_trend", month=month)
    if "cash runway" in s or ("runway" in s and "cash" in s):
        return Intent("cash_runway", month=month)
    # Default: show help
    return Intent("help")
