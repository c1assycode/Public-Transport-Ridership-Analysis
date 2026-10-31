# Public Transport Ridership Analysis Quick Start

Study area: Bareilly, Uttar Pradesh, India | Academic context: BCA-AI

## Run on Windows

Open PowerShell in the project folder (`D:\Public-Transport-Ridership-Analysis`) or open that folder in VS Code and choose **Terminal → New Terminal**.

```powershell
py --version
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell blocks activation, do not change system-wide policy; skip activation and call the environment's executable directly:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Open `http://localhost:8501`. Press **Ctrl+C** in the terminal to stop. Run the Streamlit command again to restart.

## Choose a data mode

Use **Analysis mode** in the sidebar. **Research / Observed Data** reads stored records from `data/ridership.sqlite`. **Simulation / Demonstration Data** generates a reproducible 90-day synthetic scenario with seed `20261031`; the app displays a warning banner. Simulated values are generated in memory, not inserted into observed tables.

## Navigate

- **Overview:** evidence KPIs and demand charts when records exist. Empty observed ridership shows a template download.
- **Ridership:** choose routes, date range and daily/weekly/monthly aggregation; inspect trend, moving average, route comparison, time period, distribution, and export filtered rows.
- **Network:** filter route class, compare distances and linked stop counts, select a route and inspect its stop sequence.
- **Operations:** inspect trip delays, on-time rate, completion state, daily operations and fleet assignment metrics when operational data is present.
- **Data Centre:** select one of five observed datasets, download its CSV template, preview an uploaded CSV, validate/import it, explore records and export. Simulation mode explains that generated data is not stored.
- **Data Quality:** inspect missing/duplicate counts, dates, unmatched route/bus IDs and rejected import history.
- **Sources & Planning:** view source catalogue, existing route reference and CMP proposal file.
- **System & Method:** check SQLite integrity, create/download backup, guarded restore and read methodology/limitations.

## Safe operating checklist

1. Keep the downloaded original source file and note URL, publisher, period, units, method and limits.
2. Select **Research / Observed Data** for real imports.
3. Download the matching template and preserve the exact column names.
4. Check the preview and validation feedback before importing.
5. Inspect import history and Data Quality after import.
6. Create a database backup before important changes.
7. State clearly whether any screenshot/chart shows observed records, planning evidence or simulation.

The currently stored database contains 5 route records, 20 stop records and zero ridership, fleet and operation records. The four CMP Phase-1 routes are proposed planning values; do not call them active routes.
