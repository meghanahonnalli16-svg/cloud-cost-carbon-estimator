import csv, io, json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from app.carbon import estimate_kwh, estimate_co2_kg

ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="Multi-Cloud Cost & Carbon Estimator")


def build_results(vcpu, hours, utilization):
    prices = json.loads((ROOT / "data" / "pricing.json").read_text())
    grid = json.loads((ROOT / "data" / "grid_intensity.json").read_text())
    ram = vcpu * 4
    results = []
    for p in prices:
        cost = p["price_4vcpu"] * (vcpu / 4) * hours
        kwh = estimate_kwh(p["provider"], vcpu, ram, hours, utilization)
        co2 = estimate_co2_kg(kwh, grid[p["grid"]])
        results.append({"provider": p["provider"], "region": p["region"],
                        "instance": p["instance"], "cost_usd": round(cost, 2),
                        "kwh": round(kwh, 1), "co2_kg": round(co2, 2)})
    for r in results:
        r["pareto"] = not any(
            o["cost_usd"] <= r["cost_usd"] and o["co2_kg"] <= r["co2_kg"]
            and (o["cost_usd"] < r["cost_usd"] or o["co2_kg"] < r["co2_kg"])
            for o in results)
    return results


@app.get("/")
def home():
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/compare")
def compare(vcpu: int = 4, hours: int = 730, utilization: float = 0.5):
    results = build_results(vcpu, hours, utilization)
    return {"results": results,
            "cheapest": min(results, key=lambda r: r["cost_usd"]),
            "greenest": min(results, key=lambda r: r["co2_kg"])}


@app.get("/export.csv")
def export_csv(vcpu: int = 4, hours: int = 730, utilization: float = 0.5):
    results = build_results(vcpu, hours, utilization)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["provider", "region", "instance", "cost_usd_per_month",
                     "kwh_per_month", "co2_kg_per_month", "best_tradeoff"])
    for r in results:
        writer.writerow([r["provider"], r["region"], r["instance"], r["cost_usd"],
                         r["kwh"], r["co2_kg"], "yes" if r["pareto"] else "no"])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=cloud-estimate.csv"})