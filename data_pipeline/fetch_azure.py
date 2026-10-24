import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
PRICE_FILE = ROOT / "data" / "pricing.json"
URL = "https://prices.azure.com/api/retail/prices"
REGIONS = {"centralindia": "Central India", "swedencentral": "Sweden Central", "eastus": "East US"}
SKU = "Standard_D4s_v5"

live = {}
for code, name in REGIONS.items():
    flt = (f"serviceName eq 'Virtual Machines' and armRegionName eq '{code}' "
           f"and armSkuName eq '{SKU}' and priceType eq 'Consumption'")
    items = requests.get(URL, params={"$filter": flt}).json()["Items"]
    for i in items:
        if "Windows" in i["productName"] or "Spot" in i["skuName"] or "Low Priority" in i["skuName"]:
            continue
        live[name] = i["retailPrice"]
        break

data = json.loads(PRICE_FILE.read_text())
for row in data:
    if row["provider"] == "Azure" and row["region"] in live:
        print(row["region"], row["price_4vcpu"], "->", live[row["region"]])
        row["price_4vcpu"] = live[row["region"]]
PRICE_FILE.write_text(json.dumps(data, indent=1))
print("pricing.json updated with live Azure prices")