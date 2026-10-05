"""Export the seeded dataset to CSV for loading into Snowflake (snowflake/deploy.sql)."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from throughline import data_gen  # noqa: E402

out = Path(__file__).resolve().parents[1] / "snowflake" / "data"
out.mkdir(parents=True, exist_ok=True)
con = data_gen.load()
for t in ["dim_supplier", "dim_part", "dim_plant", "dim_customer", "fct_order_line", "fct_shipment", "fct_inventory_snapshot"]:
    cur = con.execute(f"SELECT * FROM {t}")
    with open(out / f"{t}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([d[0] for d in cur.description])
        w.writerows(cur.fetchall())
    print("wrote", out / f"{t}.csv")
