"""FastAPI service. Run: uvicorn throughline.api:app --reload"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import service
from .semantic_layer import Plan, PlanError, model

app = FastAPI(title="Throughline", version="1.0.0",
              description="Supply chain ontology and governed conversational analytics")
WEB = Path(__file__).resolve().parents[2] / "web" / "index.html"


class AskIn(BaseModel):
    question: str = Field(..., examples=["What was our service level by plant last quarter?"])
    persona: str = Field("planning", pattern="^(planning|procurement|logistics)$")


class PlanIn(BaseModel):
    metric: str
    dimension: str | None = None
    filters: list[dict] = []
    period_from: str = "2026-01-01"
    period_to: str = "2026-09-30"
    sort: str | None = None
    limit: int | None = None
    persona: str = "planning"

    def to_plan(self) -> Plan:
        m = model()["metrics"]
        if self.metric not in m:
            raise HTTPException(422, f"'{self.metric}' is not a certified metric")
        return Plan(metric=self.metric, metricVersion=m[self.metric]["version"], dimension=self.dimension,
                    filters=sorted(self.filters, key=lambda f: f["dim"]),
                    period={"from": self.period_from, "to": self.period_to, "label": f"{self.period_from} to {self.period_to}"},
                    sort=self.sort, limit=self.limit)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/ontology")
def ontology():
    return model()["ontology"]


@app.get("/metrics")
def metrics():
    return model()["metrics"]


@app.get("/policies")
def policies():
    return model()["policies"]


@app.post("/ask")
def ask(body: AskIn):
    return service.ask(body.question, body.persona)


@app.post("/query")
def query(body: PlanIn):
    """Structured entry point for agents and LLM routers: a plan in, a governed answer out."""
    try:
        return service.run_plan(body.to_plan())
    except PlanError as e:
        raise HTTPException(422, {"policy": e.policy, "message": e.message, "allowed": e.allowed})


@app.post("/records")
def records(body: PlanIn):
    try:
        return service.records(body.to_plan(), body.persona)
    except PlanError as e:
        raise HTTPException(422, {"policy": e.policy, "message": e.message})


@app.get("/audit")
def audit():
    return service.AUDIT[:200]
