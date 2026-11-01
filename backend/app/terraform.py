import re
from app.carbon import estimate_kwh, estimate_co2_kg

# Terraform resource type -> (our provider name, attribute holding the size)
SUPPORTED = {
    "aws_instance": ("AWS", "instance_type"),
    "azurerm_linux_virtual_machine": ("Azure", "size"),
    "google_compute_instance": ("GCP", "machine_type"),
}
# name used by Terraform in configuration.provider_config
PROVIDER_KEY = {"AWS": "aws", "Azure": "azurerm", "GCP": "google"}


def vcpus_for(provider, size):
    """Same VM families as the app: AWS m6i.*, Azure Standard_D*s_v5, GCP n2-standard-*."""
    size = (size or "").split("/")[-1]
    if provider == "AWS":
        m = re.fullmatch(r"m6i\.(large|xlarge|(\d+)xlarge)", size)
        if not m:
            return None
        if m.group(1) == "large":
            return 2
        if m.group(1) == "xlarge":
            return 4
        return 4 * int(m.group(2))
    if provider == "Azure":
        m = re.fullmatch(r"Standard_D(\d+)s_v5", size)
        return int(m.group(1)) if m else None
    if provider == "GCP":
        m = re.fullmatch(r"n2-standard-(\d+)", size)
        return int(m.group(1)) if m else None
    return None


def find_region(plan, provider, after):
    """Region from the resource itself, otherwise from the provider block."""
    if provider == "AWS" and after.get("availability_zone"):
        return after["availability_zone"][:-1]
    if provider == "Azure" and after.get("location"):
        return after["location"]
    if provider == "GCP" and after.get("zone"):
        return after["zone"].rsplit("-", 1)[0]
    key = PROVIDER_KEY[provider]
    for cfg in plan.get("configuration", {}).get("provider_config", {}).values():
        if cfg.get("name") == key:
            expr = cfg.get("expressions", {})
            for field in ("region", "location"):
                if field in expr and "constant_value" in expr[field]:
                    return expr[field]["constant_value"]
    return None


def price_row(prices, provider, region):
    if not region:
        return None
    for row in prices:
        if row["provider"] != provider:
            continue
        if provider == "Azure":
            same = row["region"].lower().replace(" ", "") == region.lower().replace(" ", "")
        else:
            same = row["region"].split(" ")[0] == region
        if same:
            return row
    return None


def estimate_plan(plan, prices, grid, hours=730, utilization=0.5):
    resources, unsupported = [], []
    for rc in plan.get("resource_changes", []):
        if rc.get("type") not in SUPPORTED:
            continue
        change = rc.get("change", {})
        after = change.get("after")
        if not after:                      # resource is being deleted
            continue
        provider, size_field = SUPPORTED[rc["type"]]
        size = after.get(size_field)
        vcpu = vcpus_for(provider, size)
        region = find_region(plan, provider, after)
        row = price_row(prices, provider, region)
        if vcpu is None or row is None:
            reason = "VM size not supported" if vcpu is None else "region not in our price data"
            unsupported.append({"address": rc["address"], "size": size,
                                "region": region, "reason": reason})
            continue
        cost = row["price_4vcpu"] * (vcpu / 4) * hours
        kwh = estimate_kwh(provider, vcpu, vcpu * 4, hours, utilization)
        co2 = estimate_co2_kg(kwh, grid[row["grid"]])
        resources.append({"address": rc["address"], "provider": provider,
                          "action": "+".join(change.get("actions", [])),
                          "size": size, "region": row["region"], "vcpu": vcpu,
                          "cost_usd": round(cost, 2), "kwh": round(kwh, 1),
                          "co2_kg": round(co2, 2)})
    return {"resources": resources, "unsupported": unsupported,
            "total_cost_usd": round(sum(r["cost_usd"] for r in resources), 2),
            "total_co2_kg": round(sum(r["co2_kg"] for r in resources), 2)}