import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from app.carbon import estimate_kwh, estimate_co2_kg

ROOT = Path(__file__).resolve().parents[2]
PRICES = json.loads((ROOT / "data" / "pricing.json").read_text())
GRID = json.loads((ROOT / "data" / "grid_intensity.json").read_text())

app = FastAPI(title="Multi-Cloud Cost & Carbon Estimator")

@app.get("/")
def home():
    return FileResponse(ROOT / "frontend" / "index.html")

@app.get("/compare")
def compare(vcpu: int = 4, hours: int = 730, utilization: float = 0.5):
    ram = vcpu * 4
    results = []
    for p in PRICES:
        cost = p["price_4vcpu"] * (vcpu / 4) * hours
        kwh = estimate_kwh(p["provider"], vcpu, ram, hours, utilization)
        co2 = estimate_co2_kg(kwh, GRID[p["grid"]])
        results.append({"provider": p["provider"], "region": p["region"],
                        "instance": p["instance"], "cost_usd": round(cost, 2),
                        "kwh": round(kwh, 1), "co2_kg": round(co2, 1)})
    return {"results": results,
            "cheapest": min(results, key=lambda r: r["cost_usd"]),
            "greenest": min(results, key=lambda r: r["co2_kg"])}