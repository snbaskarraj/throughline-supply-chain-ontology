-- Throughline semantic views.
-- Part 1: Snowflake semantic view DDL (target platform for production).
-- Part 2: portable views used by the DuckDB reference service.

-- ============================================================
-- Part 1 — Snowflake
-- ============================================================
CREATE OR REPLACE SEMANTIC VIEW sc_fulfilment
  TABLES (
    orders    AS fct_order_line PRIMARY KEY (order_id)  COMMENT = 'Ontology entity: Order',
    shipments AS fct_shipment   PRIMARY KEY (shipment_id) COMMENT = 'Ontology entity: Shipment',
    parts     AS dim_part       PRIMARY KEY (part_id)   COMMENT = 'Ontology entity: Part',
    suppliers AS dim_supplier   PRIMARY KEY (supplier_id) COMMENT = 'Ontology entity: Supplier',
    plants    AS dim_plant      PRIMARY KEY (plant_id)  COMMENT = 'Ontology entity: Plant',
    customers AS dim_customer   PRIMARY KEY (customer_id) COMMENT = 'Ontology entity: Customer'
  )
  RELATIONSHIPS (
    shipment_fulfils_order AS shipments (order_id)   REFERENCES orders,
    order_for_part         AS orders (part_id)       REFERENCES parts,
    supplier_supplies_part AS parts (supplier_id)    REFERENCES suppliers,
    plant_dispatches       AS orders (plant_id)      REFERENCES plants,
    order_placed_by        AS orders (customer_id)   REFERENCES customers
  )
  FACTS (
    shipments.is_delivered AS CASE WHEN delivered_date IS NOT NULL THEN 1 ELSE 0 END,
    shipments.landed_value AS qty_shipped * parts.unit_cost + freight_cost + duty_cost
  )
  DIMENSIONS (
    suppliers.supplier AS supplier_name  WITH SYNONYMS = ('vendor'),
    parts.part         AS part_name      WITH SYNONYMS = ('component', 'sku', 'material'),
    parts.category     AS category,
    plants.plant       AS plant_name     WITH SYNONYMS = ('site', 'factory', 'facility'),
    plants.region      AS region,
    customers.customer AS customer_name  WITH SYNONYMS = ('account', 'client'),
    customers.segment  AS segment,
    shipments.carrier  AS carrier_name   WITH SYNONYMS = ('transporter', 'forwarder'),
    shipments.mode     AS transport_mode,
    orders.order_month AS DATE_TRUNC('month', order_date)
  )
  METRICS (
    shipments.otd_pct AS 100.0 * SUM(CASE WHEN shipments.delivered_date <= orders.promised_date THEN 1 ELSE 0 END) / NULLIF(COUNT(shipments.delivered_date), 0)
      WITH SYNONYMS = ('on-time delivery', 'service level', 'supplier punctuality', 'delivery performance')
      COMMENT = 'Certified v2.1 · owner Head of Logistics Excellence',
    orders.fill_rate_pct AS 100.0 * SUM(COALESCE(shipments.qty_shipped, 0)) / NULLIF(SUM(orders.qty_ordered), 0)
      WITH SYNONYMS = ('unit fill', 'fulfilment rate')
      COMMENT = 'Certified v1.4 · lines with promised_date <= as-of only',
    shipments.landed_cost_per_unit AS SUM(shipments.landed_value) / NULLIF(SUM(shipments.qty_shipped), 0)
      WITH SYNONYMS = ('landed cost', 'cost per unit', 'all-in cost')
      COMMENT = 'Certified v3.0 · purchase price + freight + duty',
    shipments.freight_cost AS SUM(shipments.freight_cost) COMMENT = 'Certified v1.2',
    shipments.lead_time_days AS AVG(DATEDIFF('day', orders.order_date, shipments.delivered_date)) COMMENT = 'Certified v1.1',
    shipments.excursion_pct AS 100.0 * SUM(IFF(shipments.iot_excursion, 1, 0)) / NULLIF(COUNT(shipments.delivered_date), 0) COMMENT = 'Certified v1.0',
    shipments.late_deliveries AS SUM(CASE WHEN shipments.delivered_date > orders.promised_date THEN 1 ELSE 0 END) COMMENT = 'Certified v2.1',
    orders.order_lines AS COUNT(orders.order_id) COMMENT = 'Certified v1.0'
  )
  COMMENT = 'Supply chain fulfilment semantic view, grounded in the Throughline ontology';

-- Days of inventory lives in its own view because its grain (plant x part snapshot)
-- has no relationship to Customer or Carrier — which is what POL-02 enforces.
CREATE OR REPLACE SEMANTIC VIEW sc_inventory
  TABLES (
    inv   AS fct_inventory_snapshot PRIMARY KEY (snapshot_date, plant_id, part_id),
    cogs  AS v_cogs_90d PRIMARY KEY (plant_id, part_id),
    parts AS dim_part PRIMARY KEY (part_id), suppliers AS dim_supplier PRIMARY KEY (supplier_id), plants AS dim_plant PRIMARY KEY (plant_id)
  )
  RELATIONSHIPS (
    inv_part AS inv (part_id) REFERENCES parts, inv_plant AS inv (plant_id) REFERENCES plants,
    part_supplier AS parts (supplier_id) REFERENCES suppliers, inv_cogs AS inv (plant_id, part_id) REFERENCES cogs
  )
  DIMENSIONS (suppliers.supplier AS supplier_name, parts.part AS part_name, parts.category AS category, plants.plant AS plant_name, plants.region AS region)
  METRICS (
    inv.days_of_inventory AS SUM(inv.on_hand * parts.unit_cost) / NULLIF(SUM(cogs.cogs_90d) / 90.0, 0)
      WITH SYNONYMS = ('days of supply', 'inventory cover', 'days on hand') COMMENT = 'Certified v2.0'
  );

-- ============================================================
-- Part 2 — portable views (DuckDB reference implementation)
-- ============================================================
CREATE OR REPLACE VIEW v_cogs_90d AS
SELECT o.plant_id, o.part_id, SUM(s.qty_shipped * pt.unit_cost) AS cogs_90d
FROM fct_shipment s JOIN fct_order_line o ON o.order_id = s.order_id JOIN dim_part pt ON pt.part_id = o.part_id
WHERE s.ship_date > DATE '2026-09-30' - INTERVAL 90 DAY AND s.ship_date <= DATE '2026-09-30'
GROUP BY 1, 2;

CREATE OR REPLACE VIEW sc_fulfilment AS
SELECT o.*, s.shipment_id, s.ship_date, s.delivered_date, s.qty_shipped, s.carrier_name, s.transport_mode,
       s.freight_cost, s.duty_cost, s.iot_excursion,
       pt.part_name, pt.category, pt.unit_cost, sup.supplier_name, pl.plant_name, pl.region AS plant_region,
       c.customer_name, c.segment, c.region AS customer_region
FROM fct_order_line o
LEFT JOIN fct_shipment s ON s.order_id = o.order_id
JOIN dim_part pt ON pt.part_id = o.part_id
JOIN dim_supplier sup ON sup.supplier_id = pt.supplier_id
JOIN dim_plant pl ON pl.plant_id = o.plant_id
JOIN dim_customer c ON c.customer_id = o.customer_id;
