# Manual smoke tests
1. Run app.py; confirm empty state loads.
2. Upload CSV with service_date and passengers; confirm import.
3. Upload same CSV again; confirm duplicates are ignored.
4. Restart app; confirm records persist.
5. Upload CSV missing required columns; confirm rejection.
6. Export stored records and inspect CSV.
