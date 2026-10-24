# Methodology

## Goal
Estimate the monthly cost and CO2 emissions of a virtual machine on AWS, Azure and GCP.

## Cost
Monthly cost = hourly on-demand price (Linux, from each provider's pricing API) x hours per month.
Prices are fetched by the scripts in `data_pipeline/`.

## Energy (Cloud Carbon Footprint method)
- Watts per vCPU = min watts + utilization x (max watts - min watts)
- Compute energy (kWh) = watts per vCPU x vCPUs x hours / 1000
- Memory energy (kWh) = RAM in GB x 0.000392 x hours
- Total energy (kWh) = (compute + memory) x PUE

PUE (Power Usage Effectiveness) is total data centre energy divided by IT equipment energy.
Values used: AWS 1.135, Azure 1.185, GCP 1.10.

## Emissions
CO2e (kg) = total energy (kWh) x grid carbon intensity (gCO2/kWh) / 1000

Grid intensity values (gCO2/kWh): India 713, USA 369, Finland 79, Sweden 41.

## Sources
- Cloud Carbon Footprint methodology: https://www.cloudcarbonfootprint.org/docs/methodology/
- Ember electricity data: https://ember-energy.org/data/
- AWS Price List, Azure Retail Prices API, GCP Cloud Billing Catalog API

## Assumptions and limitations
- Utilization is assumed (default 50%), not measured.
- Only Linux on-demand pricing for one VM size per provider.
- Grid values are yearly averages, not real-time.
- Results are estimates, not measurements.