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
- Storage (not yet used in the tool): SSD 0.0012 kWh per terabyte-hour (CCF coefficient).

PUE (Power Usage Effectiveness) is total data centre energy divided by IT equipment energy.
Values used: AWS 1.135, Azure 1.185, GCP 1.10.

## Emissions
CO2e (kg) = total energy (kWh) x grid carbon intensity (gCO2/kWh) / 1000

Grid intensity values (gCO2/kWh): India 708, USA 416, Finland 181, Sweden 8, Singapore 408.5, Germany 338.
Watts per vCPU (min/max): AWS 0.71/3.46, Azure 0.77/3.74, GCP 1.34/4.98 (CCF provider averages).

## Sources
- Cloud Carbon Footprint methodology: https://www.cloudcarbonfootprint.org/docs/methodology/
- CCF Appendix I (energy coefficients and PUE) and Appendix IV (grid emission factors). Grid sources inside CCF: carbonfootprint.com 2020 (India), EEA (Sweden), Google region carbon data (Finland), EPA eGRID (USA).
- AWS Price List, Azure Retail Prices API, GCP Cloud Billing Catalog API
- Status: all constants verified against the CCF methodology page. Grid factors are older (pre-2020) averages; newer Ember data can replace them later.

## Assumptions and limitations
- Utilization is assumed (default 50%), not measured.
- Only Linux on-demand pricing for one VM size per provider.
- Grid values are yearly averages, not real-time.
- Results are estimates, not measurements.
- One grid value is used per country. CCF's GCP values differ slightly (for example India 723, Iowa 479,          Singapore 493, Germany 319).
- CCF lists Azure PUE as 1.185 (fleet average) in its text and 1.125 in its appendix. This tool uses 1.185.