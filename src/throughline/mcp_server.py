"""MCP server: exposes the governed semantic layer as tools for any MCP-capable agent
(Claude Desktop, Claude Code, Cursor). Agents can only ask certified questions —
there is deliberately no free-form SQL tool.

Run: python -m throughline.mcp_server   (stdio transport)
"""
from __future__ import annotations

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from . import service
from .semantic_layer import Plan, PlanError, model

mcp = _Server("throughline")


@mcp.tool()
def list_metrics() -> dict:
    """Certified supply chain metrics with definitions, owners, versions and allowed dimensions."""
    return {k: {f: v[f] for f in ("label", "definition", "owner", "version", "dimensions", "unit")} for k, v in model()["metrics"].items()}


@mcp.tool()
def describe_ontology() -> dict:
    """Entities, relationships, hierarchies and source-system key mappings."""
    o = model()["ontology"]
    return {"chain": o["chain"], "relationships": o["relationships"], "entities": o["entities"]}


@mcp.tool()
def ask(question: str, persona: str = "planning") -> dict:
    """Answer a natural-language supply chain question from certified metrics only."""
    return service.ask(question, persona)


@mcp.tool()
def query_metric(metric: str, dimension: str | None = None, filters: list[dict] | None = None,
                 period_from: str = "2026-01-01", period_to: str = "2026-09-30") -> dict:
    """Run a structured governed query. filters: [{"dim": "plant", "value": "Chennai"}]."""
    m = model()["metrics"]
    if metric not in m:
        return {"status": "refused", "policy": "POL-01", "message": f"{metric} is not certified", "certified": list(m)}
    plan = Plan(metric=metric, metricVersion=m[metric]["version"], dimension=dimension, filters=sorted(filters or [], key=lambda f: f["dim"]),
                period={"from": period_from, "to": period_to, "label": f"{period_from} to {period_to}"})
    try:
        return service.run_plan(plan)
    except PlanError as e:
        return {"status": "blocked", "policy": e.policy, "message": e.message, "allowed": e.allowed}


if __name__ == "__main__":
    mcp.run()
