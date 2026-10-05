"""Deterministic natural-language router: question -> governed Plan.

Mirrors parse() in web/engine.js. It resolves team vocabulary to certified metrics,
refuses uncertified terms, and asks for clarification on ambiguous words instead
of guessing. An optional LLM router (llm_router.py) produces the same Plan shape.
"""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date

from .data_gen import CARRIERS, CUSTOMERS, PARTS, PLANTS, SUPPLIERS
from .semantic_layer import AS_OF, PRIORITY, Plan, model

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

NOT_CERTIFIED = {
    "otif": "OTIF is proposed but not yet certified. It would combine on-time delivery and fill rate, which are both certified — ask for either.",
    "revenue": "Revenue lives in the finance domain and is not part of the supply chain semantic layer.",
    "sales": "Sales value lives in the finance domain and is not part of the supply chain semantic layer.",
    "margin": "Margin lives in the finance domain and is not part of the supply chain semantic layer.",
    "profit": "Profit lives in the finance domain and is not part of the supply chain semantic layer.",
    "forecast accuracy": "Forecast accuracy is on the roadmap but has no certified definition yet.",
    "headcount": "Headcount is an HR metric, outside this semantic layer.",
}
AMBIGUOUS = {
    "cost": ("Two certified metrics measure cost. Which one do you mean?", [("landed_cost", "landed cost"), ("freight_cost", "freight cost")]),
    "performance": ("“Performance” could mean timeliness or completeness. Which one?", [("otd", "on-time delivery"), ("fill_rate", "fill rate")]),
    "spend": ("“Spend” could mean what you pay per unit or what you pay carriers. Which one?", [("landed_cost", "landed cost"), ("freight_cost", "freight cost")]),
}
DIM_WORDS = [
    ("supplier", r"^(suppliers?|vendors?)\b"), ("category", r"^(part categor(y|ies)|categor(y|ies))\b"), ("part", r"^(parts?|components?|skus?|materials?)\b"),
    ("plant", r"^(plants?|sites?|factor(y|ies)|facilit(y|ies)|warehouses?)\b"), ("region", r"^(regions?)\b"), ("customer", r"^(customers?|accounts?|clients?)\b"),
    ("segment", r"^(segments?|customer segments?)\b"), ("carrier", r"^(carriers?|transporters?|forwarders?)\b"), ("mode", r"^(transport modes?|modes?|shipping modes?)\b"),
    ("month", r"^(months?|monthly)\b"), ("quarter", r"^(quarters?|quarterly)\b"),
]


def _value_index() -> list[dict]:
    out: list[dict] = []

    def add(dim, values, alias=lambda v: [v]):
        for v in values:
            for a in alias(v):
                out.append({"dim": dim, "value": v, "alias": a.lower()})

    add("customer", [c[1] for c in CUSTOMERS], lambda v: [v, "Rio Grande" if v.split(" ")[0] == "Rio" else v.split(" ")[0]])
    add("supplier", [s[1] for s in SUPPLIERS], lambda v: [v, v.split(" ")[0]])
    add("part", [p[1] for p in PARTS])
    add("plant", [p[1] for p in PLANTS])
    add("carrier", [c[1] for c in CARRIERS], lambda v: [v, "Schenker"] if v == "DB Schenker" else [v, "JB Hunt", "Hunt"] if v == "J.B. Hunt" else [v, "DHL"] if v == "DHL Express" else [v])
    add("category", ["Electronics", "Mechanical", "Raw material", "Packaging"], lambda v: [v, "raw materials"] if v == "Raw material" else [v])
    add("region", ["APAC", "EMEA", "Americas"])
    add("segment", ["Retail", "OEM", "Distributor"], lambda v: [v, "distributors"] if v == "Distributor" else [v, "OEMs"] if v == "OEM" else [v])
    add("mode", ["Road", "Ocean", "Air"], lambda v: [v, "sea"] if v == "Ocean" else [v, "air freight"] if v == "Air" else [v, "truck"])
    return sorted(out, key=lambda x: -len(x["alias"]))


VALUE_INDEX = _value_index()


def _word_re(w: str) -> re.Pattern:
    return re.compile(r"(^|[^a-z0-9])" + re.escape(w) + r"(?=$|[^a-z0-9])", re.I)


def _month_start(y: int, m: int) -> str:
    y += m // 12
    m %= 12
    return date(y, m + 1, 1).isoformat()


def _month_end(y: int, m: int) -> str:
    y += m // 12
    m %= 12
    return date(y, m + 1, monthrange(y, m + 1)[1]).isoformat()


MONTH_RE = re.compile(r"\b(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|june?|july?|aug(ust)?|sep(t(ember)?)?|oct(ober)?|nov(ember)?|dec(ember)?)\b", re.I)


def parse_period(q: str) -> dict:
    s = q.lower()
    if re.search(r"\b(last|previous|prior) quarter\b", s):
        return {"from": "2026-07-01", "to": "2026-09-30", "label": "Q3 2026"}
    if re.search(r"\b(this|current) quarter\b", s):
        return {"from": "2026-10-01", "to": "2026-12-31", "label": "Q4 2026"}
    m = re.search(r"\bq([1-4])\b(?:\s*(?:fy)?\s*'?(20)?(2[0-9]))?", s)
    if m:
        qn, y = int(m.group(1)), 2000 + int(m.group(3)) if m.group(3) else 2026
        return {"from": _month_start(y, (qn - 1) * 3), "to": _month_end(y, qn * 3 - 1), "label": f"Q{qn} {y}"}
    if re.search(r"\bh1\b|first half", s):
        return {"from": "2026-01-01", "to": "2026-06-30", "label": "H1 2026"}
    m = re.search(r"\blast (\d+) days\b", s)
    if m:
        n = int(m.group(1))
        return {"from": date.fromordinal(date.fromisoformat(AS_OF).toordinal() - n + 1).isoformat(), "to": AS_OF, "label": f"last {n} days"}
    m = re.search(r"\blast (\d+) months\b", s)
    if m:
        n = int(m.group(1))
        return {"from": _month_start(2026, 9 - n), "to": AS_OF, "label": f"last {n} months"}
    if re.search(r"\blast month\b", s):
        return {"from": "2026-09-01", "to": "2026-09-30", "label": "Sep 2026"}
    months = [["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(x.group(1)[:3].lower()) for x in MONTH_RE.finditer(s)]
    if len(months) >= 2:
        a, b = min(months[0], months[1]), max(months[0], months[1])
        return {"from": _month_start(2026, a), "to": _month_end(2026, b), "label": f"{MONTHS[a]}–{MONTHS[b]} 2026"}
    if len(months) == 1:
        return {"from": _month_start(2026, months[0]), "to": _month_end(2026, months[0]), "label": f"{MONTHS[months[0]]} 2026"}
    if re.search(r"\b(ytd|year to date|this year|2026)\b", s):
        return {"from": "2026-01-01", "to": AS_OF, "label": "year to date 2026"}
    return {"from": "2026-01-01", "to": AS_OF, "label": "year to date 2026", "defaulted": True}


def parse(question: str) -> dict:
    M = model()["metrics"]
    raw = question.strip()
    s = " " + re.sub(r"\s+", " ", re.sub(r"[?!.,;:]", " ", raw.lower())) + " "
    notes: list[str] = []
    filters: list[dict] = []
    for v in VALUE_INDEX:
        rx = _word_re(v["alias"])
        if rx.search(s):
            if not any(f["dim"] == v["dim"] for f in filters):
                filters.append({"dim": v["dim"], "value": v["value"]})
            s = rx.sub(lambda m0: m0.group(1) + " " * (len(m0.group(0)) - len(m0.group(1))), s)
    for term, msg in NOT_CERTIFIED.items():
        if _word_re(term).search(s):
            return {"status": "refused", "term": term, "message": msg}
    metric = matched = None
    for mid in PRIORITY:
        syns = sorted((x["phrase"] for x in M[mid]["synonyms"]), key=lambda w: -len(w))
        hit = next((w for w in syns if _word_re(w).search(s)), None)
        if hit:
            metric, matched = mid, hit
            break
    if not metric:
        for term, (prompt, options) in AMBIGUOUS.items():
            if _word_re(term).search(s):
                return {"status": "clarify", "term": term, "prompt": prompt, "options": [list(o) for o in options]}
        if re.search(r"\binventory|stock\b", s):
            metric, matched = "doi", "inventory"
            notes.append("Read “inventory” as days of inventory, the only certified inventory metric.")
    if not metric:
        return {"status": "unknown"}
    dim = None
    s_no_metric = _word_re(matched).sub(" ", s, count=1)
    for mm in re.finditer(r"\b(by|per|for each|for every|across|split by|broken down by|which|what|each|top|best|worst|bottom|highest|lowest)\s+(?:\d+\s+)?([a-z]+(?: [a-z]+)?)", s_no_metric):
        rest = mm.group(2).strip()
        hit = next((d for d, rx in DIM_WORDS if re.search(rx, rest)), None)
        if hit:
            dim = hit
            break
    if not dim and re.search(r"\b(trend|over time|monthly|month by month|by month)\b", s):
        dim = "month"
    if not dim and re.search(r"\bquarterly\b", s):
        dim = "quarter"
    sort = limit = None
    m = re.search(r"\b(top|best)\s*(\d+)?\b", s)
    if m:
        sort, limit = "best", int(m.group(2)) if m.group(2) else None
    m = re.search(r"\b(worst|bottom)\s*(\d+)?\b", s)
    if m:
        sort, limit = "worst", int(m.group(2)) if m.group(2) else None
    if not sort and re.search(r"\b(highest|most)\b", s):
        sort = "desc"
    if not sort and re.search(r"\b(lowest|least)\b", s):
        sort = "asc"
    if re.search(r"\bwhich\b", s) and dim and not limit and sort:
        limit = 1
    if M[metric]["time_anchor"] == "Snapshot date":
        period = {"from": "2026-01-01", "to": AS_OF, "label": "snapshot 30 Sep 2026", "snapshot": True}
    else:
        period = parse_period(raw)
    if period.get("defaulted"):
        notes.append("No period given, so this uses year to date (1 Jan – 30 Sep 2026).")
    if period.get("snapshot") and re.search(r"\b(q[1-4]|quarter|month|last|ytd|202\d|jan|feb|mar|apr|jun|jul|aug|sep)\b", raw, re.I):
        notes.append("Days of inventory is a point-in-time measure; it uses the 30 Sep 2026 snapshot.")
    plan = Plan(metric=metric, metricVersion=M[metric]["version"], dimension=dim,
                filters=sorted(filters, key=lambda f: f["dim"]),
                period={"from": period["from"], "to": period["to"], "label": period["label"]}, sort=sort, limit=limit)
    return {"status": "ok", "plan": plan, "matched": matched, "notes": notes}
