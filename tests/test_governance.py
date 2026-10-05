from throughline import service
from throughline.router import parse
from throughline.semantic_layer import Plan, PlanError, validate


def test_uncertified_terms_are_refused_not_guessed():
    for q in ["What is OTIF by plant?", "Revenue by supplier", "profit last quarter"]:
        assert parse(q)["status"] == "refused"


def test_ambiguous_terms_trigger_clarification():
    r = parse("What's the cost by carrier?")
    assert r["status"] == "clarify" and {o[0] for o in r["options"]} == {"landed_cost", "freight_cost"}


def test_ontology_blocks_invalid_slices():
    r = service.ask("Days of inventory by customer", "procurement")
    assert r["status"] == "blocked" and r["policy"] == "POL-02"


def test_metric_version_is_pinned():
    try:
        validate(Plan(metric="otd", metricVersion="1.0"))
    except PlanError as e:
        assert e.policy == "POL-01"
    else:
        raise AssertionError("stale metric version accepted")


def test_contract_price_masked_except_procurement():
    plan = parse("on-time delivery for Chennai in Q3")["plan"]
    assert all(r["unit_cost"] == "•••••" for r in service.records(plan, "logistics", 5))
    assert all(isinstance(r["unit_cost"], float) for r in service.records(plan, "procurement", 5))


def test_filters_do_not_leak_across_entities():
    r = parse("on-time delivery for Arcadia Retail")
    assert r["plan"].filters == [{"dim": "customer", "value": "Arcadia Retail"}]  # not also segment=Retail


def test_every_answer_is_audited():
    before = len(service.AUDIT)
    service.ask("Freight cost by transport mode", "logistics")
    assert len(service.AUDIT) == before + 1 and service.AUDIT[0]["fingerprint"].startswith("fp-")
