"""The browser prototype (web/engine.js) and the DuckDB service must agree exactly."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from throughline import service

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = [
    "What was our service level by plant last quarter?", "Fill rate by part category year to date", "Days of inventory by plant",
    "Landed cost per unit by supplier", "Freight cost by transport mode", "Late shipments by carrier in Q3",
    "Temperature excursions on ocean shipments", "Average lead time by mode", "Monthly fill rate trend", "OTD for Arcadia Retail",
    "Days of inventory by supplier", "Order lines by customer segment in H1",
]
JS = """
const E=require(process.argv[1]); const qs=JSON.parse(process.argv[2]); const out={};
for(const q of qs){const p=E.parse(q).plan; const r=E.execute(p);
 out[q]={fp:E.fingerprint(p), total:r.total.value, groups:r.groups.map(g=>[g.key,g.value])};}
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_browser_and_warehouse_agree():
    js = json.loads(subprocess.check_output(["node", "-e", JS, str(ROOT / "web" / "engine.js"), json.dumps(QUESTIONS)]))
    for q in QUESTIONS:
        py = service.ask(q, "planning")
        assert py["fingerprint"] == js[q]["fp"], q
        assert py["total"] == pytest.approx(js[q]["total"], abs=0.051), q
        pg = {k: v for k, v in ((g["key"], g["value"]) for g in py["groups"])}
        jg = {k: v for k, v in js[q]["groups"]}
        assert set(pg) == set(jg), q
        for k in jg:
            assert pg[k] == pytest.approx(jg[k], abs=0.051), (q, k)
