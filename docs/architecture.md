# Architecture

## Request lifecycle

1. **Route.** A question and persona arrive. The router finds entity values first (blanking matched spans so "Arcadia Retail" doesn't also set segment = Retail), then checks uncertified terms (refuse), then matches team vocabulary to one certified metric in priority order, then dimensions, period, sort and limit. Ambiguous words with no metric ("cost", "spend", "performance") return a clarification instead of a guess.
2. **Validate.** The plan is checked against the ontology: the metric exists and its version is pinned (POL-01); every dimension and filter is reachable from the metric's grain (POL-02).
3. **Fingerprint.** FNV-1a over `{metric, version, dimension, filters, period, sort, limit}`. Persona is not an input, so equal fingerprints prove equal logic across teams.
4. **Compile.** The semantic layer emits SQL from the metric's certified expression and the ontology's join paths. Only the entities the plan touches are joined.
5. **Execute and govern.** Results are flagged where a group has fewer than five records (POL-04); record drill-downs mask supplier contract prices for non-procurement personas (POL-03).
6. **Explain and audit.** The answer carries the definition, owner, version, ontology path, semantic view, compiled SQL and fingerprint; the request is logged (POL-05).

## Ontology

| Entity | Canonical key | Mapped from |
|---|---|---|
| Supplier | supplier_id | ERP LIFNR, supplier portal vendor_code, TMS shipper name |
| Part | part_id | ERP MATNR, supplier SKU |
| Plant | plant_id | ERP WERKS, WMS site_code, TMS origin |
| Shipment | shipment_id | TMS load_id, IoT tracker → load, ERP delivery (VBELN) |
| Order | order_id | ERP/OMS order line, planning sheet ref |
| Customer | customer_id | CRM account_id, ERP KUNNR |

Relationships: Supplier *supplies* Part (1:N); Part *stocked at* Plant (N:M via Inventory); Plant *dispatches* Shipment (1:N); Shipment *fulfils* Order (N:1); Order *placed by* Customer (N:1).

## Why the LLM never writes SQL

Free-form text-to-SQL re-derives business logic on every question, which is exactly the inconsistency this project removes. The optional Claude router fills a tool schema whose enums are the certified metrics, ontology dimensions and known values. Its output goes through the same validator as the deterministic router; anything invalid falls back to the deterministic path. The MCP server exposes the same constraint to external agents.

## Parity between browser and warehouse

`web/engine.js` and `src/throughline/` share the seeded Mulberry32 generator (ported bit-for-bit), the metric definitions and the fingerprint function. `tests/test_parity.py` runs the browser engine in Node and the service on DuckDB over twelve questions and fails on any difference in fingerprint, total or group value.
