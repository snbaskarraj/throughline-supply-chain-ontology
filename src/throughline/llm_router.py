"""Optional LLM router. Claude maps free-form questions to a Plan via a tool whose
JSON schema enumerates only certified metrics, ontology dimensions and known
values. The plan is then validated by the same semantic layer, so the model can
never invent a metric, a join or a SQL statement. Falls back to the deterministic
router when no API key is configured or the model output fails validation.
"""
from __future__ import annotations

import os

from .router import VALUE_INDEX, parse, parse_period
from .semantic_layer import Plan, PlanError, model, validate


def _tool_schema() -> dict:
    m = model()
    values = sorted({v["value"] for v in VALUE_INDEX})
    return {
        "name": "governed_plan",
        "description": "Express the user's question as a governed supply chain query plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "enum": list(m["metrics"])},
                "dimension": {"type": ["string", "null"], "enum": list(m["dimensions"]) + [None]},
                "filters": {"type": "array", "items": {"type": "object", "properties": {
                    "dim": {"type": "string", "enum": list(m["dimensions"])}, "value": {"type": "string", "enum": values}},
                    "required": ["dim", "value"]}},
                "period_phrase": {"type": "string", "description": "The time phrase from the question, verbatim, or empty."},
                "sort": {"type": ["string", "null"], "enum": ["best", "worst", "asc", "desc", None]},
                "limit": {"type": ["integer", "null"]},
            },
            "required": ["metric"],
        },
    }


def route(question: str) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return parse(question)
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=key)
        glossary = "; ".join(f"{k}: {v['definition']} (team words: {', '.join(s['phrase'] for s in v['synonyms'])})" for k, v in model()["metrics"].items())
        msg = client.messages.create(
            model=os.getenv("THROUGHLINE_MODEL", "claude-sonnet-5-5"), max_tokens=500,
            system="You translate supply chain questions into governed plans. Use only the tool. If no certified metric fits, pick the closest and the validator will decide. Certified metrics: " + glossary,
            tools=[_tool_schema()], tool_choice={"type": "tool", "name": "governed_plan"},
            messages=[{"role": "user", "content": question}])
        args = next(b.input for b in msg.content if b.type == "tool_use")
        m = model()["metrics"][args["metric"]]
        period = parse_period(args.get("period_phrase") or "")
        plan = Plan(metric=args["metric"], metricVersion=m["version"], dimension=args.get("dimension"),
                    filters=sorted(args.get("filters") or [], key=lambda f: f["dim"]),
                    period={k: period[k] for k in ("from", "to", "label")}, sort=args.get("sort"), limit=args.get("limit"))
        validate(plan)
        return {"status": "ok", "plan": plan, "matched": "(LLM)", "notes": ["Routed by Claude, validated by the semantic layer."]}
    except (PlanError, Exception):  # noqa: BLE001 — any failure falls back to the deterministic, auditable path
        return parse(question)
