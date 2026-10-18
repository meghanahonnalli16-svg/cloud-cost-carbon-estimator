# Multi-Cloud Cost & Carbon Footprint Estimator

Compares estimated monthly cost and CO2 emissions of equivalent virtual machines on AWS, Azure and GCP across regions.

## Features (Phase 1 - prototype)
- Cost comparison across 3 cloud providers and 3 regions each
- Carbon estimate using the Cloud Carbon Footprint (CCF) methodology
- Cheapest and greenest recommendations
- Table and bar chart dashboard

## Tech stack
Python, FastAPI, Chart.js, JSON data

## Run locally
    cd backend
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000

## Carbon method
energy (kWh) = (compute + memory) x PUE
CO2e (kg) = energy x grid carbon intensity (gCO2/kWh) / 1000

## Roadmap
Live pricing APIs, Pareto chart, what-if scenarios, Terraform plan parsing, PDF/CSV reports, Docker, CI/CD, cloud deployment

## Note
Pricing and grid data are snapshots; results are estimates.
