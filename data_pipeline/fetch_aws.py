import json, tempfile, os
from pathlib import Path
import requests, ijson

ROOT = Path(__file__).resolve().parents[1]
PRICE_FILE = ROOT / "data" / "pricing.json"
BASE = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/{}/index.json"
REGIONS = ["ap-south-1", "eu-north-1", "us-east-1"]
INSTANCE = "m6i.xlarge"

def fetch_price(region):
    print("Downloading", region, "(large file, please wait)...")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    with requests.get(BASE.format(region), stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(1024 * 1024):
            tmp.write(chunk)
    tmp.close()
    try:
        sku = None
        with open(tmp.name, "rb") as f:
            for key, p in ijson.kvitems(f, "products"):
                a = p.get("attributes", {})
                if (a.get("instanceType") == INSTANCE and a.get("operatingSystem") == "Linux"
                        and a.get("tenancy") == "Shared" and a.get("preInstalledSw") == "NA"
                        and a.get("capacitystatus") == "Used"):
                    sku = key
                    break
        if not sku:
            return None
        with open(tmp.name, "rb") as f:
            for key, offers in ijson.kvitems(f, "terms.OnDemand"):
                if key == sku:
                    for offer in offers.values():
                        for dim in offer["priceDimensions"].values():
                            return float(dim["pricePerUnit"]["USD"])
    finally:
        os.remove(tmp.name)

live = {}
for region in REGIONS:
    price = fetch_price(region)
    print(region, "->", price)
    if price:
        live[region] = price

data = json.loads(PRICE_FILE.read_text())
for row in data:
    if row["provider"] == "AWS":
        code = row["region"].split(" ")[0]
        if code in live:
            print(row["region"], row["price_4vcpu"], "->", live[code])
            row["price_4vcpu"] = live[code]
PRICE_FILE.write_text(json.dumps(data, indent=1))
print("pricing.json updated with live AWS prices")