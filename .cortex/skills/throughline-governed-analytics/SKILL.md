---
name: throughline-governed-analytics
description: Deploy and query the Throughline supply chain ontology on Snowflake. Use when asked about on-time delivery, fill rate, days of inventory, landed cost, freight, lead time, late deliveries, IoT excursions or order lines for suppliers, parts, plants, shipments, orders or customers.
---
# Throughline governed analytics

You answer supply chain questions ONLY through certified metrics. Never write ad-hoc KPI SQL.

## Deploy (first run)
1. Run `python scripts/export_csv.py`, then `snowflake/deploy.sql` (PUT the CSVs to `@sc_stage` when prompted).
2. Create the semantic views from `semantic/semantic_views.sql` Part 1 — use the bundled `semantic-view` skill to validate them.
3. Run the parity checks at the end of `deploy.sql`; expect 760 / 31113.67 / 85.84.

## Answering questions
1. Map the user's words to a metric using the synonyms in `semantic/metrics.yaml` (e.g. "service level", "supplier punctuality", "delivery performance" → `otd`).
2. If a term is uncertified (OTIF, revenue, margin) say so and offer certified alternatives. If ambiguous ("cost", "spend", "performance"), ask which metric.
3. Only slice by the metric's `dimensions` list. Days of inventory cannot be split by customer or carrier (ontology rule POL-02).
4. Query the semantic view (`SEMANTIC_VIEW(sc_fulfilment METRICS ... DIMENSIONS ...)`) or call the Throughline MCP tool `query_metric`.
5. Always show: metric definition and version, owner, ontology path, period, and the SQL used.

## Governance
- Contract prices are masked by `mask_contract_price` for every role except SC_PROCUREMENT.
- Metric definitions change only by editing `semantic/metrics.yaml` (version bump) and the semantic view together.
