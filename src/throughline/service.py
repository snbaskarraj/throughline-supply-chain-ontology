"""Answer service: route -> validate -> compile -> execute on DuckDB -> govern -> audit."""
from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime, timezone

from . import data_gen
from .router import parse
from .semantic_layer import Plan, PlanError, compile_sql, entities_touched, fingerprint, model, validate

PERSONAS = ("planning", "procurement", "logistics")
_lock = threading.Lock()
_con = None
AUDIT: list[dict] = []


def con():
    global _con
    with _lock:
        if _con is None:
            _con = data_gen.load()
        return _con


def run_plan(plan: Plan) -> dict:
    validate(plan)
    sql = compile_sql(plan)
    c = con().cursor()
    rows = c.execute(sql).fetchall()
    total_plan = replace(plan, dimension=None, sort=None, limit=None)
    total = c.execute(compile_sql(total_plan)).fetchone()[0]
    min_n = model()["policies"]["min_group_size"]
    groups = [{"key": r[0], "value": r[1]} for r in rows] if plan.dimension else []
    if plan.dimension:  # POL-04 small-sample flag
        counts = dict(c.execute(_count_sql(plan)).fetchall())
        for g in groups:
            g["n"] = counts.get(g["key"], 0)
            g["low_confidence"] = g["n"] < min_n
    return {"plan": plan.to_dict(), "fingerprint": fingerprint(plan), "sql": sql, "total": total, "groups": groups,
            "path": entities_touched(plan), "metric": model()["metrics"][plan.metric]}


def _count_sql(plan: Plan) -> str:
    # Reuse the compiled FROM/WHERE so counts follow exactly the same joins and filters.
    sql = compile_sql(replace(plan, sort=None, limit=None)).rstrip(";")
    head, body = sql.split("\nFROM ", 1) if plan.metric != "doi" else sql.split("\nFROM fct_inventory_snapshot", 1)
    dim_col = model()["dimensions"][plan.dimension]["column"]
    body = body.split("\nGROUP BY")[0]
    if plan.metric == "doi":
        cte = head.split("\nSELECT")[0]
        return f"{cte}\nSELECT {dim_col}, COUNT(*) FROM fct_inventory_snapshot{body} GROUP BY 1"
    return f"SELECT {dim_col}, COUNT(*) FROM {body} GROUP BY 1"


def ask(question: str, persona: str = "planning") -> dict:
    if persona not in PERSONAS:
        raise ValueError(f"persona must be one of {PERSONAS}")
    parsed = parse(question)
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "persona": persona, "question": question}
    if parsed["status"] != "ok":
        entry |= {"outcome": parsed["status"], "fingerprint": None}
        AUDIT.insert(0, entry)
        return parsed
    plan = parsed["plan"]
    try:
        out = run_plan(plan)
    except PlanError as e:
        entry |= {"outcome": f"blocked ({e.policy})", "fingerprint": None}
        AUDIT.insert(0, entry)
        return {"status": "blocked", "policy": e.policy, "message": e.message, "allowed": e.allowed}
    entry |= {"outcome": plan.metric, "fingerprint": out["fingerprint"]}
    AUDIT.insert(0, entry)
    return {"status": "ok", "matched": parsed["matched"], "notes": parsed["notes"], **out}


def records(plan: Plan, persona: str, limit: int = 20) -> list[dict]:
    """Row-level drill-down with POL-03 contract-price masking."""
    validate(plan)
    dims = model()["dimensions"]
    where = [f"o.order_date BETWEEN DATE '{plan.period['from']}' AND DATE '{plan.period['to']}'"]
    where += [f"{dims[f['dim']]['column']} = '{str(f['value']).replace(chr(39), chr(39) * 2)}'" for f in plan.filters]
    sql = f"""SELECT o.order_id, o.order_date, pt.part_name, sup.supplier_name, pl.plant_name, c.customer_name,
                     s.carrier_name, o.promised_date, s.delivered_date, o.qty_ordered, s.qty_shipped, pt.unit_cost
              FROM fct_order_line o LEFT JOIN fct_shipment s ON s.order_id = o.order_id
              JOIN dim_part pt ON pt.part_id = o.part_id JOIN dim_supplier sup ON sup.supplier_id = pt.supplier_id
              JOIN dim_plant pl ON pl.plant_id = o.plant_id JOIN dim_customer c ON c.customer_id = o.customer_id
              WHERE {' AND '.join(where)} ORDER BY o.order_id LIMIT {int(limit)}"""
    cur = con().cursor().execute(sql)
    cols = [d[0] for d in cur.description]
    visible = persona in model()["policies"]["masking"]["dim_part.unit_cost"]["visible_to"]
    out = []
    for r in cur.fetchall():
        row = dict(zip(cols, r))
        if not visible:
            row["unit_cost"] = "•••••"
        out.append({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()})
    return out
