"""Synthetic supply chain data, generated with the same seeded PRNG as web/engine.js.

Every call order below mirrors the JavaScript generator line for line, so the
browser prototype and the DuckDB service see byte-identical data.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

import duckdb

EPOCH = date(1970, 1, 1)


def d(s: str) -> int:
    return (date.fromisoformat(s) - EPOCH).days


def iso(n: int) -> date:
    return EPOCH + timedelta(days=n)


AS_OF = d("2026-09-30")
YEAR_START = d("2026-01-01")


def _i32(x: int) -> int:
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x & 0x80000000 else x


def _imul(a: int, b: int) -> int:
    return _i32((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF))


class Mulberry32:
    def __init__(self, seed: int):
        self.seed = _i32(seed)

    def __call__(self) -> float:
        self.seed = _i32(self.seed + 0x6D2B79F5)
        s = self.seed
        t = _imul(s ^ ((s & 0xFFFFFFFF) >> 15), 1 | s)
        t = _i32(_i32(t + _imul(t ^ ((t & 0xFFFFFFFF) >> 7), 61 | t)) ^ t)
        return ((t ^ ((t & 0xFFFFFFFF) >> 14)) & 0xFFFFFFFF) / 4294967296


def js_round(x: float) -> int:
    return math.floor(x + 0.5)


SUPPLIERS = [
    ("S01", "Kaveri Castings", "IN", 0.93, 1, "0000100023", "KAV-IN-01"),
    ("S02", "Nordhavn Electronics", "DK", 0.95, 1, "0000100031", "NOR-DK-02"),
    ("S03", "Shenzhen Lumen", "CN", 0.82, 1, "0000100044", "SZL-CN-07"),
    ("S04", "Saltillo Polymers", "MX", 0.88, 2, "0000100052", "SAL-MX-03"),
    ("S05", "Osaka Precision", "JP", 0.97, 1, "0000100067", "OSK-JP-01"),
    ("S06", "Ruhr Steelworks", "DE", 0.90, 2, "0000100071", "RUH-DE-04"),
    ("S07", "Penang Microsystems", "MY", 0.85, 1, "0000100088", "PEN-MY-02"),
    ("S08", "Ohio Fasteners", "US", 0.91, 2, "0000100090", "OHF-US-05"),
]
PARTS = [
    ("P101", "Motor controller board", "Electronics", "S02", 42), ("P102", "Li-ion cell pack", "Electronics", "S03", 65),
    ("P103", "Display module", "Electronics", "S07", 38), ("P104", "Sensor array", "Electronics", "S05", 27),
    ("P105", "Battery management IC", "Electronics", "S07", 9.5), ("P106", "Power switch", "Electronics", "S03", 3.2),
    ("P107", "Aluminium housing", "Mechanical", "S01", 18), ("P108", "Gear assembly", "Mechanical", "S05", 24),
    ("P109", "Steel bracket", "Mechanical", "S06", 4.1), ("P110", "Fastener kit", "Mechanical", "S08", 1.8),
    ("P111", "Wiring harness", "Mechanical", "S04", 6.5), ("P112", "Thermal pad", "Raw material", "S04", 0.9),
    ("P113", "Polymer resin", "Raw material", "S04", 2.4), ("P114", "Cold-rolled steel coil", "Raw material", "S06", 1.1),
    ("P115", "Corrugated carton", "Packaging", "S01", 0.6), ("P116", "Foam insert", "Packaging", "S08", 0.4),
]
PLANTS = [("PL1", "Chennai", "IN", "APAC"), ("PL2", "Pune", "IN", "APAC"), ("PL3", "Monterrey", "MX", "Americas"), ("PL4", "Rotterdam", "NL", "EMEA")]
CUSTOMERS = [
    ("C01", "Arcadia Retail", "Retail", "Americas"), ("C02", "Bharat Mobility", "OEM", "APAC"), ("C03", "Lindqvist Distribution", "Distributor", "EMEA"),
    ("C04", "Sakura Home", "Retail", "APAC"), ("C05", "Volta Motors", "OEM", "EMEA"), ("C06", "Pacific Wholesale", "Distributor", "APAC"),
    ("C07", "Meridian Appliances", "OEM", "Americas"), ("C08", "Hanse Handel", "Distributor", "EMEA"), ("C09", "Deccan Electricals", "Retail", "APAC"),
    ("C10", "Rio Grande Supply", "Distributor", "Americas"),
]
CARRIERS = [
    ("CR1", "BlueDart", "Road", "APAC", 0.90), ("CR2", "Delhivery", "Road", "APAC", 0.84), ("CR3", "DB Schenker", "Road", "EMEA", 0.92),
    ("CR4", "J.B. Hunt", "Road", "Americas", 0.89), ("CR5", "Maersk", "Ocean", None, 0.78), ("CR6", "DHL Express", "Air", None, 0.95),
    ("CR7", "FedEx", "Air", None, 0.91),
]
LEAD = {"Road": 7, "Air": 6, "Ocean": 32}
RATE = {"Road": 0.12, "Ocean": 0.08, "Air": 0.55}


def generate(seed: int = 20261005, n_orders: int = 760):
    R = Mulberry32(seed)
    ri = lambda a, b: a + math.floor(R() * (b - a + 1))  # noqa: E731
    pick = lambda arr: arr[math.floor(R() * len(arr))]  # noqa: E731
    sup = {s[0]: s for s in SUPPLIERS}
    car = {c[0]: c for c in CARRIERS}
    orders, shipments = [], []
    for i in range(n_orders):
        od = YEAR_START + ri(0, 266)
        cust = pick(CUSTOMERS)
        local = [p for p in PLANTS if p[3] == cust[3]]
        plant = pick(local) if R() < 0.65 else pick(PLANTS)
        part = pick(PARTS)
        s = sup[part[3]]
        cross = plant[3] != cust[3]
        if not cross:
            carrier = pick([c for c in CARRIERS if c[2] == "Road" and c[3] == plant[3]])
        else:
            carrier = car["CR5"] if R() < 0.62 else pick([car["CR6"], car["CR7"]])
        mode = carrier[2]
        promised = od + LEAD[mode]
        proc = ri(1, 2)
        sup_delay = ri(2, 7) if R() > s[3] else 0
        ship = od + proc + sup_delay
        transit = ri(3, 4) if mode == "Road" else ri(2, 3) if mode == "Air" else ri(24, 28)
        car_delay = ri(1, 6) if R() > carrier[4] else 0
        deliv = ship + transit + car_delay
        qo = ri(5, 60) * 10
        qs = qo
        partial = R() > 0.86
        if partial or (sup_delay > 0 and R() < 0.35):
            qs = js_round(qo * (0.55 + R() * 0.4))
        shipped = ship <= AS_OF
        if not shipped:
            qs = 0
        delivered = shipped and deliv <= AS_OF
        freight = js_round(qs * RATE[mode] * (0.5 + part[4] / 40) * 100) / 100 if shipped else 0
        duty = js_round(qs * part[4] * 0.06 * 100) / 100 if (shipped and s[2] != plant[2]) else 0
        e = R()
        excursion = bool(delivered and ((part[2] == "Electronics" and mode == "Ocean" and e < 0.18) or e < 0.02))
        oid = f"SO-{240001 + i}"
        orders.append((oid, iso(od), iso(promised), qo, part[0], plant[0], cust[0]))
        if shipped:
            shipments.append((f"LD-{240001 + i}", oid, iso(ship), iso(deliv) if delivered else None, qs, carrier[0], carrier[1], mode, freight, duty, excursion))
    inventory = []
    for p in PLANTS:
        for pt in PARTS:
            if R() < 0.8:
                inventory.append((iso(AS_OF), p[0], pt[0], js_round((100 + R() * 2900) * (12 / (pt[4] + 12))) + 20))
    return orders, shipments, inventory


def load(con: duckdb.DuckDBPyConnection | None = None) -> duckdb.DuckDBPyConnection:
    """Create the star schema the semantic layer compiles against."""
    con = con or duckdb.connect()
    orders, shipments, inventory = generate()
    con.execute("CREATE OR REPLACE TABLE dim_supplier(supplier_id VARCHAR, supplier_name VARCHAR, country VARCHAR, reliability DOUBLE, tier INT, erp_lifnr VARCHAR, portal_code VARCHAR)")
    con.executemany("INSERT INTO dim_supplier VALUES (?,?,?,?,?,?,?)", SUPPLIERS)
    con.execute("CREATE OR REPLACE TABLE dim_part(part_id VARCHAR, part_name VARCHAR, category VARCHAR, supplier_id VARCHAR, unit_cost DOUBLE)")
    con.executemany("INSERT INTO dim_part VALUES (?,?,?,?,?)", PARTS)
    con.execute("CREATE OR REPLACE TABLE dim_plant(plant_id VARCHAR, plant_name VARCHAR, country VARCHAR, region VARCHAR)")
    con.executemany("INSERT INTO dim_plant VALUES (?,?,?,?)", PLANTS)
    con.execute("CREATE OR REPLACE TABLE dim_customer(customer_id VARCHAR, customer_name VARCHAR, segment VARCHAR, region VARCHAR)")
    con.executemany("INSERT INTO dim_customer VALUES (?,?,?,?)", CUSTOMERS)
    con.execute("CREATE OR REPLACE TABLE fct_order_line(order_id VARCHAR, order_date DATE, promised_date DATE, qty_ordered INT, part_id VARCHAR, plant_id VARCHAR, customer_id VARCHAR)")
    con.executemany("INSERT INTO fct_order_line VALUES (?,?,?,?,?,?,?)", orders)
    con.execute("CREATE OR REPLACE TABLE fct_shipment(shipment_id VARCHAR, order_id VARCHAR, ship_date DATE, delivered_date DATE, qty_shipped INT, carrier_id VARCHAR, carrier_name VARCHAR, transport_mode VARCHAR, freight_cost DOUBLE, duty_cost DOUBLE, iot_excursion BOOLEAN)")
    con.executemany("INSERT INTO fct_shipment VALUES (?,?,?,?,?,?,?,?,?,?,?)", shipments)
    con.execute("CREATE OR REPLACE TABLE fct_inventory_snapshot(snapshot_date DATE, plant_id VARCHAR, part_id VARCHAR, on_hand INT)")
    con.executemany("INSERT INTO fct_inventory_snapshot VALUES (?,?,?,?)", inventory)
    return con
