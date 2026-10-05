"""The core claim: the same metric resolves identically across personas."""
import pytest

from throughline import service

PHRASINGS = {
    "otd_by_plant_q3": {
        "planning": "What was our service level by plant last quarter?",
        "procurement": "Show supplier punctuality per plant for Q3 2026",
        "logistics": "Delivery performance by plant, July to September 2026",
    },
    "fill_by_supplier_q3": {
        "planning": "Unit fill by supplier last quarter",
        "procurement": "Fill rate per vendor in Q3 2026",
        "logistics": "Fulfilment rate for each supplier, Jul to Sep",
    },
    "landed_by_category_q3": {
        "planning": "Cost per unit by part category last quarter",
        "procurement": "Total landed cost per category for Q3",
        "logistics": "Landed cost by category, July to September 2026",
    },
    "doi_by_plant": {
        "planning": "Days of supply by plant",
        "procurement": "Inventory days per site",
        "logistics": "Days on hand for each plant",
    },
}


@pytest.mark.parametrize("case", PHRASINGS)
def test_three_teams_one_answer(case):
    answers = {p: service.ask(q, p) for p, q in PHRASINGS[case].items()}
    assert all(a["status"] == "ok" for a in answers.values()), answers
    fps = {a["fingerprint"] for a in answers.values()}
    assert len(fps) == 1, f"plans diverged: {fps}"
    results = {tuple((g["key"], g["value"]) for g in a["groups"]) for a in answers.values()}
    assert len(results) == 1
    assert len({a["sql"] for a in answers.values()}) == 1


def test_persona_does_not_change_metric_values():
    q = "On-time delivery by carrier in Q3"
    vals = {p: service.ask(q, p)["groups"] for p in service.PERSONAS}
    assert vals["planning"] == vals["procurement"] == vals["logistics"]
