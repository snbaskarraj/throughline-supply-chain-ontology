-- Throughline on Snowflake. Run from Cortex Code CLI (`cortex -c <connection>`) or SnowSQL.
-- 1) python scripts/export_csv.py     2) run this file     3) run semantic/semantic_views.sql (Part 1)
CREATE DATABASE IF NOT EXISTS THROUGHLINE;
CREATE SCHEMA IF NOT EXISTS THROUGHLINE.SUPPLY_CHAIN;
USE SCHEMA THROUGHLINE.SUPPLY_CHAIN;

CREATE OR REPLACE TABLE dim_supplier (supplier_id STRING, supplier_name STRING, country STRING, reliability FLOAT, tier INT, erp_lifnr STRING, portal_code STRING);
CREATE OR REPLACE TABLE dim_part (part_id STRING, part_name STRING, category STRING, supplier_id STRING, unit_cost FLOAT);
CREATE OR REPLACE TABLE dim_plant (plant_id STRING, plant_name STRING, country STRING, region STRING);
CREATE OR REPLACE TABLE dim_customer (customer_id STRING, customer_name STRING, segment STRING, region STRING);
CREATE OR REPLACE TABLE fct_order_line (order_id STRING, order_date DATE, promised_date DATE, qty_ordered INT, part_id STRING, plant_id STRING, customer_id STRING);
CREATE OR REPLACE TABLE fct_shipment (shipment_id STRING, order_id STRING, ship_date DATE, delivered_date DATE, qty_shipped INT, carrier_id STRING, carrier_name STRING, transport_mode STRING, freight_cost FLOAT, duty_cost FLOAT, iot_excursion BOOLEAN);
CREATE OR REPLACE TABLE fct_inventory_snapshot (snapshot_date DATE, plant_id STRING, part_id STRING, on_hand INT);

CREATE OR REPLACE FILE FORMAT csv_hdr TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"' NULL_IF = ('');
CREATE OR REPLACE STAGE sc_stage FILE_FORMAT = csv_hdr;
-- From the repo root (SnowSQL / snow CLI):
--   PUT file://snowflake/data/*.csv @sc_stage AUTO_COMPRESS=TRUE;
COPY INTO dim_supplier FROM @sc_stage/dim_supplier.csv.gz;
COPY INTO dim_part FROM @sc_stage/dim_part.csv.gz;
COPY INTO dim_plant FROM @sc_stage/dim_plant.csv.gz;
COPY INTO dim_customer FROM @sc_stage/dim_customer.csv.gz;
COPY INTO fct_order_line FROM @sc_stage/fct_order_line.csv.gz;
COPY INTO fct_shipment FROM @sc_stage/fct_shipment.csv.gz;
COPY INTO fct_inventory_snapshot FROM @sc_stage/fct_inventory_snapshot.csv.gz;

-- POL-03 as a native Snowflake masking policy: contract prices visible to procurement only.
CREATE ROLE IF NOT EXISTS SC_PLANNING; CREATE ROLE IF NOT EXISTS SC_PROCUREMENT; CREATE ROLE IF NOT EXISTS SC_LOGISTICS;
CREATE OR REPLACE MASKING POLICY mask_contract_price AS (v FLOAT) RETURNS FLOAT ->
  CASE WHEN IS_ROLE_IN_SESSION('SC_PROCUREMENT') THEN v ELSE NULL END;
-- Applied to a reporting view rather than the base column, so certified metrics still compute on true cost.
CREATE OR REPLACE VIEW v_part_contract_price AS SELECT part_id, part_name, supplier_id, unit_cost AS contract_price FROM dim_part;
ALTER VIEW v_part_contract_price MODIFY COLUMN contract_price SET MASKING POLICY mask_contract_price;

-- Parity check: these must match the prototype (760 lines, freight 31,113.67, Q3 OTD 85.84%).
SELECT COUNT(*) AS order_lines FROM fct_order_line;
SELECT ROUND(SUM(freight_cost), 2) AS freight FROM fct_shipment;
SELECT ROUND(100.0 * SUM(IFF(s.delivered_date <= o.promised_date, 1, 0)) / NULLIF(COUNT(s.delivered_date), 0), 2) AS otd_q3
FROM fct_order_line o LEFT JOIN fct_shipment s ON s.order_id = o.order_id
WHERE o.order_date BETWEEN '2026-07-01' AND '2026-09-30';
