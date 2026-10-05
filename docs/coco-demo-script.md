# Demo video script — 4 minutes, recorded in Cortex Code CLI

The form asks for: an end-to-end workflow executed via CoCo CLI, Input → Processing → Output, at least one fully working workflow, and 2–3 modular skills. This script covers all four.

## Before recording (not on camera)
1. Snowflake trial account + a connection in `~/.snowflake/connections.toml` (e.g. `[hack]`).
2. In the repo: `python scripts/export_csv.py` (writes `snowflake/data/*.csv`).
3. Do one full dry run of steps 1–4 below. If the semantic-view DDL needs syntax fixes for your account, let the `semantic-view` skill correct it during the dry run and commit the fix, so the recording runs clean.
4. Terminal font 16pt+, dark theme, close notifications. Use QuickTime / OBS / Loom; upload to YouTube (unlisted) or Google Drive (anyone with link).

## Recording

**0:00–0:25 — Problem (voice over the prototype's "Why this exists" tab)**
"Supply chain systems disagree. Q3 on-time delivery is 98.3% in the ERP, 91.6% in the TMS and 85.7% in the planning sheet. Throughline gives every team one governed answer, built and run with Cortex Code CLI."

**0:25–0:45 — Start CoCo in the repo**
```
cortex -c hack
/skill list
```
Point at `throughline-governed-analytics` (project skill), `semantic-view` and `cortex-agent` (bundled).

**0:45–1:40 — Skill 1, project skill: deploy (Input → Processing)**
Prompt: `Deploy Throughline to Snowflake.`
Show CoCo running `snowflake/deploy.sql`: tables, stage, COPY, the masking policy, then the parity checks returning **760**, **31113.67**, **85.84**.

**1:40–2:20 — Skill 2, semantic-view: build the semantic layer**
Prompt: `Create and validate the semantic views in semantic/semantic_views.sql.`
Show `sc_fulfilment` and `sc_inventory` created; scroll the certified metrics and synonyms ("service level", "supplier punctuality", "delivery performance").

**2:20–3:20 — The governed question (Processing → Output)**
Prompt: `What was our service level by plant last quarter?`
Point out: "service level" → on-time delivery v2.1, ontology path Plant → Shipment → Order, SQL against `sc_fulfilment`, answer **85.8% overall, Chennai lowest at 81.6%**.
Then: `Show supplier punctuality per plant for Q3 2026.` → same numbers. "Procurement's words, the same certified answer."

**3:20–3:50 — Guardrails**
- `What is OTIF by plant?` → refused, not certified; offers alternatives.
- `Days of inventory by customer` → blocked; no ontology path.
- Optional: run `SELECT * FROM v_part_contract_price` under `SC_LOGISTICS` → prices masked.

**3:50–4:10 — Skill 3 / close**
Option A — `cortex-agent`: `Create a Cortex Agent over sc_fulfilment for supply chain questions.` Ask it one question.
Option B — show the GitHub Pages prototype's "Same answer, every team" tab with fingerprint `fp-e0b39158`.
Close: "One ontology, certified metrics, governed answers. Repo and live prototype are in the submission."
