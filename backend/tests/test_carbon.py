import pytest
from app.carbon import estimate_kwh, estimate_co2_kg


def test_zero_hours_gives_zero_energy():
    assert estimate_kwh("AWS", 4, 16, 0, 0.5) == 0


def test_double_hours_doubles_energy():
    one = estimate_kwh("AWS", 4, 16, 365, 0.5)
    two = estimate_kwh("AWS", 4, 16, 730, 0.5)
    assert two == pytest.approx(2 * one)


def test_higher_utilization_uses_more_energy():
    low = estimate_kwh("AWS", 4, 16, 730, 0.2)
    high = estimate_kwh("AWS", 4, 16, 730, 0.8)
    assert high > low


def test_aws_known_value():
    # watts = 0.71 + 0.5 * (3.46 - 0.71) = 2.085
    # compute = 2.085 * 4 * 730 / 1000 = 6.0882 kWh
    # memory = 16 * 0.000392 * 730 = 4.57856 kWh
    # total = (6.0882 + 4.57856) * 1.135 = 12.1068 kWh
    assert estimate_kwh("AWS", 4, 16, 730, 0.5) == pytest.approx(12.1068, rel=1e-3)


def test_co2_formula():
    # 100 kWh on a grid of 500 g/kWh = 50 kg
    assert estimate_co2_kg(100, 500) == pytest.approx(50)


def test_mumbai_emits_more_than_stockholm():
    kwh = estimate_kwh("AWS", 4, 16, 730, 0.5)
    assert estimate_co2_kg(kwh, 713) > estimate_co2_kg(kwh, 41)