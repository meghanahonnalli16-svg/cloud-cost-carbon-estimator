import json, os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
PRICE_FILE = ROOT / "data" / "pricing.json"
KEY = os.environ.get("GCP_API_KEY")
if not KEY:
    raise SystemExit("Set GCP_API_KEY first")

URL = "https://cloudbilling.googleapis.com/v1/services/6F81-5844-456A/skus"
REGIONS = ["asia-south1", "europe-north1", "us-central1"]
VCPU, RAM_GB = 4, 16  # n2-standard-4

core, ram = {}, {}
token = None
while True:
    params = {"key": KEY, "pageSize": 5000}
    if token:
        params["pageToken"] = token
    r = requests.get(URL, params=params)
    r.raise_for_status()
    data = r.json()
    for sku in data.get("skus", []):
        d = sku["description"]
        if sku["category"].get("usageType") != "OnDemand" or "Custom" in d:
            continue
        kind = core if d.startswith("N2 Instance Core running in") else \
               ram if d.startswith("N2 Instance Ram running in") else None
        if kind is None:
            continue
        rate = sku["pricingInfo"][0]["pricingExpression"]["tieredRates"][0]["unitPrice"]
        price = int(rate.get("units", 0)) + rate.get("nanos", 0) / 1e9
        for reg in sku["serviceRegions"]:
            if reg in REGIONS:
                kind[reg] = price
    token = data.get("nextPageToken")
    if not token:
        break

live = {reg: round(core[reg] * VCPU + ram[reg] * RAM_GB, 4)
        for reg in REGIONS if reg in core and reg in ram}
print("Live n2-standard-4 prices:", live)

rows = json.loads(PRICE_FILE.read_text())
for row in rows:
    if row["provider"] == "GCP":
        code = row["region"].split(" ")[0]
        if code in live:
            print(row["region"], row["price_4vcpu"], "->", live[code])
            row["price_4vcpu"] = live[code]
PRICE_FILE.write_text(json.dumps(rows, indent=1))
print("pricing.json updated with live GCP prices")