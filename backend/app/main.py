import csv, io, json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from app.carbon import estimate_kwh, estimate_co2_kg
from app.terraform import estimate_plan

ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="Multi-Cloud Cost & Carbon Estimator")


def load_data():
    prices = json.loads((ROOT / "data" / "pricing.json").read_text())
    grid = json.loads((ROOT / "data" / "grid_intensity.json").read_text())
    return prices, grid


def build_results(vcpu, hours, utilization):
    prices, grid = load_data()
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


@app.get("/terraform")
def terraform_page():
    return FileResponse(ROOT / "frontend" / "terraform.html")


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


SPOT_DISCOUNT = 0.60      # assumption: typical spot discount, varies by provider and region
RESERVED_DISCOUNT = 0.35  # assumption: typical 1-year commitment discount, varies


@app.get("/whatif")
def whatif(provider: str, region: str, vcpu: int = 4, hours: int = 730, utilization: float = 0.5):
    results = build_results(vcpu, hours, utilization)
    base = next((r for r in results if r["provider"] == provider and r["region"] == region), None)
    if base is None:
        return {"error": "option not found"}

    def scenario(name, cost, co2, note):
        return {"name": name, "cost_usd": round(cost, 2), "co2_kg": round(co2, 2),
                "saving_usd": round(base["cost_usd"] - cost, 2),
                "saving_co2": round(base["co2_kg"] - co2, 2), "note": note}

    out = [
        scenario("Spot instance", base["cost_usd"] * (1 - SPOT_DISCOUNT), base["co2_kg"],
                 f"Assumes {int(SPOT_DISCOUNT * 100)}% discount; can be interrupted"),
        scenario("1-year reserved", base["cost_usd"] * (1 - RESERVED_DISCOUNT), base["co2_kg"],
                 f"Assumes {int(RESERVED_DISCOUNT * 100)}% discount for a commitment"),
    ]
    if vcpu >= 2:
        small = build_results(vcpu // 2, hours, min(1.0, utilization * 2))
        s = next(r for r in small if r["provider"] == provider and r["region"] == region)
        out.append(scenario("Right-size (half the vCPUs)", s["cost_usd"], s["co2_kg"],
                            "Same workload on half the vCPUs at double utilization"))
    cheapest = min(results, key=lambda r: r["cost_usd"])
    greenest = min(results, key=lambda r: r["co2_kg"])
    out.append(scenario("Move to cheapest: " + cheapest["provider"] + " " + cheapest["region"],
                        cheapest["cost_usd"], cheapest["co2_kg"], "Region and provider change"))
    out.append(scenario("Move to greenest: " + greenest["provider"] + " " + greenest["region"],
                        greenest["cost_usd"], greenest["co2_kg"], "Region and provider change"))
    return {"baseline": base, "scenarios": out}


@app.post("/estimate-plan")
async def estimate_plan_endpoint(request: Request, hours: int = 730, utilization: float = 0.5):
    try:
        plan = await request.json()
    except Exception:
        return {"error": "File is not valid JSON. Use: terraform show -json tfplan"}
    if not isinstance(plan, dict) or "resource_changes" not in plan:
        return {"error": "No resource_changes found. Use: terraform show -json tfplan"}
    prices, grid = load_data()
    return estimate_plan(plan, prices, grid, hours, utilization)