"""Governed semantic layer: loads the ontology + certified metrics, validates plans
against the ontology, fingerprints them and compiles them to SQL."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
AS_OF = "2026-09-30"
PRIORITY = ["excursion", "late_count", "otd", "fill_rate", "doi", "landed_cost", "freight_cost", "lead_time", "order_lines"]


@dataclass
class Plan:
    metric: str
    metricVersion: str
    dimension: str | None = None
    filters: list[dict] = field(default_factory=list)
    period: dict = field(default_factory=lambda: {"from": "2026-01-01", "to": AS_OF, "label": "year to date 2026"})
    sort: str | None = None
    limit: int | None = None

    def to_dict(self) -> dict:
        return {"metric": self.metric, "metricVersion": self.metricVersion, "dimension": self.dimension, "filters": self.filters,
                "period": self.period, "sort": self.sort, "limit": self.limit}


@lru_cache
def model() -> dict:
    onto = yaml.safe_load((ROOT / "ontology" / "supply_chain.yaml").read_text())
    metrics = yaml.safe_load((ROOT / "semantic" / "metrics.yaml").read_text())["metrics"]
    policies = yaml.safe_load((ROOT / "policies" / "policies.yaml").read_text())
    return {"ontology": onto, "metrics": metrics, "dimensions": onto["dimensions"], "policies": policies}


class PlanError(ValueError):
    def __init__(self, policy: str, message: str, allowed: list[str] | None = None):
        super().__init__(message)
        self.policy, self.message, self.allowed = policy, message, allowed or []


def validate(plan: Plan) -> None:
    m = model()
    if plan.metric not in m["metrics"]:
        raise PlanError("POL-01", f"'{plan.metric}' is not a certified metric.", list(m["metrics"]))
    M, dims = m["metrics"][plan.metric], m["dimensions"]
    if plan.metricVersion != M["version"]:
        raise PlanError("POL-01", f"{M['label']} is certified at v{M['version']}, not v{plan.metricVersion}.")
    asked = [plan.dimension] + [f["dim"] for f in plan.filters]
    unknown = [x for x in asked if x and x not in dims]
    if unknown:
        raise PlanError("POL-02", f"'{unknown[0]}' is not an attribute in the ontology.", list(dims))
    bad = [x for x in asked if x and x not in M["dimensions"]]
    if bad:
        ent = dims[bad[0]]["entity"]
        raise PlanError("POL-02", f"{M['label']} is defined at {M['grain'].lower()} grain and has no path to {ent} in the ontology, "
                                  f"so it cannot be split or filtered by {dims[bad[0]]['label'].lower()}.",
                        [dims[x]["label"] for x in M["dimensions"]])


def fingerprint(plan: Plan) -> str:
    """FNV-1a over the canonical plan. Persona is deliberately not an input."""
    s = json.dumps({"m": plan.metric, "v": plan.metricVersion, "d": plan.dimension, "f": plan.filters,
                    "p": [plan.period["from"], plan.period["to"]], "s": plan.sort, "l": plan.limit},
                   separators=(",", ":"), ensure_ascii=False)
    h = 0x811C9DC5
    for ch in s.encode("utf-16-le").decode("utf-16-le"):
        h = ((h ^ ord(ch)) * 0x01000193) & 0xFFFFFFFF
    return f"fp-{h:08x}"


def _lit(v: str) -> str:
    return "'" + str(v).replace("'", "''") + "'"


def _order(plan: Plan, M: dict) -> str:
    if plan.dimension in ("month", "quarter"):
        return "ORDER BY 1"
    lower = M["better"] == "lower"
    direction = {"asc": "ASC", "desc": "DESC", "worst": "DESC" if lower else "ASC"}.get(plan.sort or "", "ASC" if lower else "DESC")
    return f"ORDER BY 2 {direction}"


def entities_touched(plan: Plan) -> list[str]:
    m = model()
    chain = m["ontology"]["chain"]
    ents = set(m["metrics"][plan.metric]["entities"])
    if plan.dimension:
        ents.add(m["dimensions"][plan.dimension]["entity"])
    ents |= {m["dimensions"][f["dim"]]["entity"] for f in plan.filters}
    if plan.dimension == "supplier" or any(f["dim"] == "supplier" for f in plan.filters):
        ents.add("Supplier")
    idx = [chain.index(e) for e in ents if e in chain]
    return chain[min(idx): max(idx) + 1]


def compile_sql(plan: Plan) -> str:
    """Compile a validated plan to warehouse SQL. The LLM never writes SQL; this does."""
    m = model()
    M, dims = m["metrics"][plan.metric], m["dimensions"]
    dim = dims[plan.dimension] if plan.dimension else None
    ents = set(M["entities"])
    if dim:
        ents.add(dim["entity"])
    for f in plan.filters:
        ents.add(dims[f["dim"]]["entity"])
    uses_supplier = plan.dimension == "supplier" or any(f["dim"] == "supplier" for f in plan.filters)
    if uses_supplier:
        ents.add("Part")
    where = [f"{dims[f['dim']]['column']} = {_lit(f['value'])}" for f in plan.filters]

    if plan.metric == "doi":
        sel = f"{dim['column']} AS {plan.dimension},\n  " if dim else ""
        lines = [
            f"-- semantic view: sc_inventory  |  metric: days_of_inventory v{M['version']}",
            "WITH cogs AS (",
            "  SELECT o.plant_id, o.part_id, SUM(s.qty_shipped * pt.unit_cost) AS cogs_90d",
            "  FROM fct_shipment s JOIN fct_order_line o ON o.order_id = s.order_id",
            "  JOIN dim_part pt ON pt.part_id = o.part_id",
            f"  WHERE s.ship_date > DATE '{AS_OF}' - INTERVAL 90 DAY AND s.ship_date <= DATE '{AS_OF}'",
            "  GROUP BY 1, 2)",
            f"SELECT {sel}ROUND({M['sql']}, 1) AS days_of_inventory",
            "FROM fct_inventory_snapshot i",
            "JOIN dim_part pt ON pt.part_id = i.part_id",
            "JOIN dim_supplier sup ON sup.supplier_id = pt.supplier_id" if uses_supplier else None,
            "JOIN dim_plant pl ON pl.plant_id = i.plant_id",
            "LEFT JOIN cogs ON cogs.plant_id = i.plant_id AND cogs.part_id = i.part_id",
            f"WHERE i.snapshot_date = DATE '{AS_OF}'" + ("\n  AND " + "\n  AND ".join(where) if where else ""),
            "GROUP BY 1" if dim else None, _order(plan, M) if dim else None,
        ]
        return "\n".join(x for x in lines if x) + ";"

    conds = [f"o.order_date BETWEEN DATE '{plan.period['from']}' AND DATE '{plan.period['to']}'"]
    if M.get("where"):
        conds.append(M["where"])
    conds += where
    joins = []
    if "Shipment" in ents:
        joins.append("LEFT JOIN fct_shipment s ON s.order_id = o.order_id")
    if "Part" in ents:
        joins.append("JOIN dim_part pt ON pt.part_id = o.part_id")
    if uses_supplier:
        joins.append("JOIN dim_supplier sup ON sup.supplier_id = pt.supplier_id")
    if "Plant" in ents:
        joins.append("JOIN dim_plant pl ON pl.plant_id = o.plant_id")
    if "Customer" in ents:
        joins.append("JOIN dim_customer c ON c.customer_id = o.customer_id")
    lines = [
        f"-- semantic view: {M['view']}  |  metric: {plan.metric} v{M['version']}",
        "SELECT " + (f"{dim['column']} AS {plan.dimension},\n       " if dim else "") + f"ROUND({M['sql']}, 2) AS {plan.metric}",
        "FROM fct_order_line o", *joins,
        "WHERE " + "\n  AND ".join(conds),
        "GROUP BY 1" if dim else None, _order(plan, M) if dim else None,
        f"LIMIT {plan.limit}" if plan.limit else None,
    ]
    return "\n".join(x for x in lines if x) + ";"
