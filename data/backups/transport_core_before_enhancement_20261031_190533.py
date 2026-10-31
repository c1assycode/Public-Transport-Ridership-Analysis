"""Persistent storage, validation and import services for the dashboard.

This module deliberately contains no Streamlit code so its data rules can be tested.
"""
from __future__ import annotations

import hashlib
import io
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "ridership.sqlite"
UPLOAD_DIR = DATA_DIR / "uploads"
BACKUP_DIR = DATA_DIR / "backups"

DATASETS = {
    "Ridership": {
        "table": "ridership", "key": ["service_date", "route_id", "route_name", "passengers", "trips", "revenue"],
        "required": ["service_date", "passengers"],
        "columns": ["service_date", "route_id", "route_name", "passengers", "trips", "revenue"],
        "numeric": ["passengers", "trips", "revenue"], "integer": ["passengers"],
    },
    "Routes": {
        "table": "routes", "key": ["route_id"], "required": ["route_id", "route_name"],
        "columns": ["route_id", "route_name", "start_point", "end_point", "distance_km", "frequency_per_hour", "headway_minutes", "route_type"],
        "numeric": ["distance_km", "frequency_per_hour", "headway_minutes"], "integer": [],
    },
    "Stops": {
        "table": "stops", "key": ["stop_id"], "required": ["stop_id", "stop_name"],
        "columns": ["stop_id", "stop_name", "latitude", "longitude", "route_id", "stop_sequence"],
        "numeric": ["latitude", "longitude", "stop_sequence"], "integer": ["stop_sequence"],
    },
    "Fleet": {
        "table": "fleet", "key": ["bus_id"], "required": ["bus_id", "capacity", "status"],
        "columns": ["bus_id", "route_id", "vehicle_type", "capacity", "status"],
        "numeric": ["capacity"], "integer": ["capacity"],
    },
    "Operations": {
        "table": "operations", "key": ["service_date", "route_id", "bus_id", "scheduled_trips", "actual_trips", "delay_minutes"],
        "required": ["service_date", "route_id", "bus_id", "scheduled_trips", "actual_trips"],
        "columns": ["service_date", "route_id", "bus_id", "scheduled_trips", "actual_trips", "delay_minutes"],
        "numeric": ["scheduled_trips", "actual_trips", "delay_minutes"], "integer": ["scheduled_trips", "actual_trips"],
    },
}

SOURCE_CATALOGUE = [
    ("Planning routes", "Comprehensive Mobility Plan for Bareilly — Final Report", "Ministry of Housing and Urban Affairs / UMTC", "https://mohua.gov.in/upload/uploadfiles/files/Final-CMPreport-for-Bareilly.pdf", "2023", "Bareilly urban area", "km, minutes, buses/hour, fleet", "CMP surveys and planning analysis", "Phase-1 routes/fleet are proposals, not confirmed current operations or observed ridership."),
    ("Planning demand", "Forecasting Urban Bus Demand in Bareilly", "Council on Energy, Environment and Water (CEEW)", "https://www.ceew.in/sites/default/files/factsheet-forecasting-urban-bus-demand-web.pdf", "2025 (web publication)", "Bareilly", "passengers/day, buses, routes", "Scenario model", "Forecasts/scenarios; not observed passenger counts."),
    ("Operations capability", "SUGAM Yatra — MIS & Reporting", "Uttar Pradesh State Road Transport Corporation", "https://sugamyatra.up.in/MIS-reporting.html", "Accessed 2026-10-31", "Uttar Pradesh", "dashboard fields", "System description", "Describes available MIS capabilities; it is not a Bareilly-level downloadable dataset."),
    ("Catalogue lead", "Buses: Bareilly Smart City", "Open Government Data Platform India", "https://up.data.gov.in/catalog/buses-bareilly-smart-city", "Catalogue checked 2026-10-31", "Bareilly", "not verified", "Catalogue entry", "Catalogue page returns no result; no file has been integrated."),
]

def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c

def initialise(path: Path = DB_PATH) -> None:
    with connect(path) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS routes(route_id TEXT PRIMARY KEY, route_name TEXT NOT NULL, start_point TEXT, end_point TEXT, distance_km REAL, frequency_per_hour REAL, headway_minutes REAL, route_type TEXT, source_file TEXT, record_hash TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS stops(stop_id TEXT PRIMARY KEY, stop_name TEXT NOT NULL, latitude REAL, longitude REAL, route_id TEXT, stop_sequence INTEGER, source_file TEXT, record_hash TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS fleet(bus_id TEXT PRIMARY KEY, route_id TEXT, vehicle_type TEXT, capacity INTEGER, status TEXT NOT NULL, source_file TEXT, record_hash TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS ridership(id INTEGER PRIMARY KEY, service_date TEXT NOT NULL, route_id TEXT, route_name TEXT, passengers INTEGER NOT NULL, trips REAL, revenue REAL, source_file TEXT, record_hash TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS operations(operation_id INTEGER PRIMARY KEY AUTOINCREMENT, service_date TEXT NOT NULL, route_id TEXT NOT NULL, bus_id TEXT NOT NULL, scheduled_trips INTEGER NOT NULL, actual_trips INTEGER NOT NULL, delay_minutes REAL, source_file TEXT, record_hash TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS dataset_imports(import_id TEXT PRIMARY KEY, dataset_type TEXT NOT NULL, filename TEXT NOT NULL, imported_at TEXT NOT NULL, rows_received INTEGER NOT NULL, rows_added INTEGER NOT NULL, status TEXT NOT NULL, sha256 TEXT NOT NULL, notes TEXT);
        CREATE TABLE IF NOT EXISTS data_sources(source_id INTEGER PRIMARY KEY AUTOINCREMENT, dataset_type TEXT, source_name TEXT NOT NULL, publisher TEXT NOT NULL, source_url TEXT NOT NULL, publication_date TEXT, geography TEXT, coverage_period TEXT, measurement_unit TEXT, measurement_method TEXT, limitations TEXT, added_at TEXT NOT NULL);
        """)
        _add_column(c, "dataset_imports", "notes TEXT")
        _add_column(c, "data_sources", "publication_date TEXT")
        _add_column(c, "data_sources", "measurement_unit TEXT")
        for table in ("routes", "stops", "fleet"):
            _add_column(c, table, "record_hash TEXT")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_routes_hash ON routes(record_hash) WHERE record_hash IS NOT NULL")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_stops_hash ON stops(record_hash) WHERE record_hash IS NOT NULL")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fleet_hash ON fleet(record_hash) WHERE record_hash IS NOT NULL")

def _add_column(c, table, column):
    name = column.split()[0]
    if name not in {r[1] for r in c.execute(f"PRAGMA table_info({table})")}:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column}")

def template(dataset: str) -> bytes:
    return pd.DataFrame(columns=DATASETS[dataset]["columns"]).to_csv(index=False).encode("utf-8")

def _clean_text(value) -> str:
    return "" if pd.isna(value) else str(value).strip()

def validate_frame(dataset: str, frame: pd.DataFrame):
    cfg = DATASETS[dataset]
    missing = set(cfg["required"]) - set(frame.columns)
    if missing:
        return None, ["Missing required columns: " + ", ".join(sorted(missing))]
    x = frame.copy()
    for col in cfg["columns"]:
        if col not in x:
            x[col] = pd.NA
    errors = []
    for col in set(cfg["columns"]) - set(cfg["numeric"]):
        x[col] = x[col].map(_clean_text)
    for col in cfg["required"]:
        if col not in cfg["numeric"] and (x[col] == "").any():
            errors.append(f"{col} contains empty values.")
    for col in cfg["numeric"]:
        x[col] = pd.to_numeric(x[col], errors="coerce")
        if col in cfg["required"] and x[col].isna().any():
            errors.append(f"{col} contains missing or invalid numbers.")
        if (x[col].dropna() < 0).any() and col != "delay_minutes":
            errors.append(f"{col} cannot contain negative values.")
    for col in cfg["integer"]:
        vals = x[col].dropna()
        if not vals.empty and not (vals % 1 == 0).all(): errors.append(f"{col} must contain whole numbers.")
    if "service_date" in x:
        dates = pd.to_datetime(x["service_date"], errors="coerce")
        if dates.isna().any(): errors.append("service_date contains invalid or empty dates.")
        else: x["service_date"] = dates.dt.strftime("%Y-%m-%d")
    if dataset == "Stops":
        if ((x.latitude.dropna() < -90) | (x.latitude.dropna() > 90)).any(): errors.append("latitude must be between -90 and 90.")
        if ((x.longitude.dropna() < -180) | (x.longitude.dropna() > 180)).any(): errors.append("longitude must be between -180 and 180.")
    if dataset == "Operations" and (x.actual_trips > x.scheduled_trips).any():
        errors.append("actual_trips cannot exceed scheduled_trips in this record format.")
    key_dupes = x.duplicated(cfg["key"], keep=False)
    if key_dupes.any(): errors.append(f"File contains {int(key_dupes.sum())} duplicate row(s) by dataset key.")
    return (None, errors) if errors else (x[cfg["columns"]], [])

def import_bytes(dataset: str, filename: str, raw: bytes, path: Path = DB_PATH):
    initialise(path)
    iid = datetime.now().strftime("%Y%m%d%H%M%S%f")
    digest = hashlib.sha256(raw).hexdigest(); safe_name = Path(filename).name
    try: frame = pd.read_csv(io.BytesIO(raw))
    except Exception as exc: return _record_failure(iid, dataset, safe_name, digest, 0, f"Unreadable CSV: {exc}", path)
    clean, errors = validate_frame(dataset, frame)
    if errors: return _record_failure(iid, dataset, safe_name, digest, len(frame), "; ".join(errors), path)
    cfg = DATASETS[dataset]; clean["source_file"] = safe_name
    clean["record_hash"] = clean[cfg["key"]].fillna("").astype(str).agg("|".join, axis=1).map(lambda s: hashlib.sha256(s.encode()).hexdigest())
    cols = cfg["columns"] + ["source_file", "record_hash"]
    values = [tuple(None if pd.isna(v) else v for v in row) for row in clean[cols].itertuples(index=False, name=None)]
    with connect(path) as c:
        before = c.total_changes
        c.executemany(f"INSERT OR IGNORE INTO {cfg['table']} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})", values)
        added = c.total_changes - before
        c.execute("INSERT INTO dataset_imports VALUES(?,?,?,?,?,?,?,?,?)", (iid, dataset, safe_name, datetime.now().isoformat(timespec="seconds"), len(frame), added, "Imported" if added else "No new rows", digest, "Rows with an existing key or record hash were not altered."))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True); (UPLOAD_DIR / f"{iid}_{safe_name}").write_bytes(raw)
    return {"received": len(frame), "added": added, "errors": []}

def _record_failure(iid, dataset, name, digest, rows, notes, path):
    with connect(path) as c: c.execute("INSERT INTO dataset_imports VALUES(?,?,?,?,?,?,?,?,?)", (iid, dataset, name, datetime.now().isoformat(timespec="seconds"), rows, 0, "Rejected", digest, notes))
    return {"received": rows, "added": 0, "errors": [notes]}

def frame_for(table: str, path: Path = DB_PATH) -> pd.DataFrame:
    initialise(path)
    with connect(path) as c: return pd.read_sql_query(f"SELECT * FROM {table}", c)

def backup(path: Path = DB_PATH) -> Path:
    initialise(path); BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"ridership_{datetime.now():%Y%m%d_%H%M%S}.sqlite"
    with connect(path) as source, sqlite3.connect(dest) as target: source.backup(target)
    return dest

def integrity(path: Path = DB_PATH) -> str:
    initialise(path)
    with connect(path) as c: return c.execute("PRAGMA integrity_check").fetchone()[0]

def restore_from_bytes(raw: bytes, path: Path = DB_PATH) -> Path:
    """Validate a supplied SQLite backup, then preserve and replace the live DB."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    candidate = BACKUP_DIR / f".restore_candidate_{datetime.now():%Y%m%d%H%M%S%f}.sqlite"
    candidate.write_bytes(raw)
    try:
        with sqlite3.connect(candidate) as c:
            if c.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("The uploaded backup does not pass SQLite integrity_check.")
        previous = backup(path)
        shutil.copy2(candidate, path)
        initialise(path)
        return previous
    finally:
        candidate.unlink(missing_ok=True)
