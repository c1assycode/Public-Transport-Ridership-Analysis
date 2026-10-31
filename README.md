# Public Transport Ridership Analysis

Study area: Bareilly, Uttar Pradesh, India. Academic context: first-year BCA-AI project.

A Streamlit evidence dashboard for a first-year BCA-AI project. It supports traceable analysis across five linked datasets: ridership, routes, stops, fleet, and operations.

## Important evidence boundary

The audit did **not** verify a public, downloadable Bareilly route-day passenger-count dataset. The dashboard therefore shows an honest empty state for observed ridership until a documented source is imported. The bundled CMP route file is a planning reference; the CEEW factsheet is modelled demand. Neither is operational ridership data.

## Features

- Persistent SQLite storage with integrity check and timestamped backups
- CSV templates, validation, duplicate detection, accepted-file archive, import history, and exports
- Route-linked data-quality checks across all five datasets
- Interactive Plotly charts that appear only when their supporting data exists
- Source register and a separate planning-evidence view
- No silent overwrites; backup restore remains supervised/manual by design

## Run on Windows

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local address Streamlit prints (normally `http://localhost:8501`). For automated checks:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Architecture

```text
CSV source → validation → import history + original archive → SQLite evidence store
                                                            ↓
 Ridership ← route_id → Routes ← route_id → Stops / Fleet / Operations
                                            Operations ← bus_id → Fleet
                                                            ↓
             Streamlit filters, Plotly analysis, quality checks, CSV exports
```

## Research sources

See [research/source_register.csv](research/source_register.csv) and `Sources & Planning` in the app. The register links the [Bareilly CMP](https://mohua.gov.in/upload/uploadfiles/files/Final-CMPreport-for-Bareilly.pdf), [CEEW factsheet](https://www.ceew.in/sites/default/files/factsheet-forecasting-urban-bus-demand-web.pdf), [UPSRTC SUGAM Yatra MIS description](https://sugamyatra.up.in/MIS-reporting.html), and [OGD catalogue lead](https://up.data.gov.in/catalog/buses-bareilly-smart-city).

## Academic documentation

See [docs/METHODOLOGY.md](docs/METHODOLOGY.md), [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md), and [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md). They distinguish observed records, historical statistics, planning estimates, and projections.
