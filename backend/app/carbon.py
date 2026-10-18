# Method based on Cloud Carbon Footprint (CCF)
WATTS = {"AWS": (0.74, 3.5), "Azure": (0.78, 3.76), "GCP": (0.71, 4.26)}  # min, max watts per vCPU
PUE = {"AWS": 1.135, "Azure": 1.185, "GCP": 1.10}
MEM_KWH_PER_GB_HOUR = 0.000392

def estimate_kwh(provider, vcpu, ram_gb, hours, utilization):
    min_w, max_w = WATTS[provider]
    watts = min_w + utilization * (max_w - min_w)
    compute = watts * vcpu * hours / 1000
    memory = ram_gb * MEM_KWH_PER_GB_HOUR * hours
    return (compute + memory) * PUE[provider]

def estimate_co2_kg(kwh, grid_g_per_kwh):
    return kwh * grid_g_per_kwh / 1000