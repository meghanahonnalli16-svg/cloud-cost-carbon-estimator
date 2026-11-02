import pytest
from app.terraform import estimate_plan, vcpus_for

PRICES = [
    {"provider": "AWS", "region": "ap-south-1 (Mumbai)", "grid": "India",
     "instance": "m6i.xlarge", "price_4vcpu": 0.2},
    {"provider": "Azure", "region": "Central India", "grid": "India",
     "instance": "D4s_v5", "price_4vcpu": 0.2},
    {"provider": "GCP", "region": "asia-south1 (Mumbai)", "grid": "India",
     "instance": "n2-standard-4", "price_4vcpu": 0.2},
]
GRID = {"India": 708}


def plan_with(resources):
    return {"resource_changes": resources,
            "configuration": {"provider_config": {
                "aws": {"name": "aws", "expressions": {"region": {"constant_value": "ap-south-1"}}}}}}


def aws(address, size, actions=("create",)):
    after = None if actions == ("delete",) else {"instance_type": size}
    return {"address": address, "type": "aws_instance",
            "change": {"actions": list(actions), "after": after}}


def test_vcpu_parsing():
    assert vcpus_for("AWS", "m6i.large") == 2
    assert vcpus_for("AWS", "m6i.xlarge") == 4
    assert vcpus_for("AWS", "m6i.4xlarge") == 16
    assert vcpus_for("Azure", "Standard_D8s_v5") == 8
    assert vcpus_for("GCP", "n2-standard-4") == 4
    assert vcpus_for("AWS", "t3.micro") is None


def test_cost_scales_with_size():
    out = estimate_plan(plan_with([aws("a", "m6i.xlarge"), aws("b", "m6i.2xlarge")]), PRICES, GRID)
    small, big = out["resources"]
    assert small["cost_usd"] == pytest.approx(0.2 * 730)
    assert big["cost_usd"] == pytest.approx(2 * small["cost_usd"])


def test_totals_add_up():
    out = estimate_plan(plan_with([aws("a", "m6i.xlarge"), aws("b", "m6i.xlarge")]), PRICES, GRID)
    assert out["total_cost_usd"] == pytest.approx(sum(r["cost_usd"] for r in out["resources"]))


def test_unsupported_size_is_reported_not_guessed():
    out = estimate_plan(plan_with([aws("a", "t3.micro")]), PRICES, GRID)
    assert out["resources"] == []
    assert out["unsupported"][0]["reason"] == "VM size not supported"


def test_deleted_resources_are_skipped():
    out = estimate_plan(plan_with([aws("a", "m6i.xlarge", actions=("delete",))]), PRICES, GRID)
    assert out["resources"] == [] and out["unsupported"] == []


def test_unknown_region_is_reported():
    plan = {"resource_changes": [aws("a", "m6i.xlarge")], "configuration": {"provider_config": {}}}
    out = estimate_plan(plan, PRICES, GRID)
    assert out["unsupported"][0]["reason"] == "region not in our price data"