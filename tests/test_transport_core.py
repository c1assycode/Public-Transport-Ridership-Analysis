import pandas as pd
from transport_core import initialise, import_bytes, integrity, validate_frame

def test_rejects_missing_required_column():
    frame = pd.DataFrame({"route_id": ["A"]})
    _, errors = validate_frame("Routes", frame)
    assert "route_name" in errors[0]

def test_stops_coordinates_are_checked():
    frame = pd.DataFrame({"stop_id":["S1"], "stop_name":["Stop"], "latitude":[99], "longitude":[80]})
    _, errors = validate_frame("Stops", frame)
    assert any("latitude" in e for e in errors)

def test_import_is_persistent_and_deduplicates(tmp_path):
    db = tmp_path / "test.sqlite"; initialise(db)
    raw = b"service_date,route_id,route_name,passengers,trips,revenue\n2026-01-01,R1,Route 1,20,1,0\n"
    assert import_bytes("Ridership", "records.csv", raw, db)["added"] == 1
    assert import_bytes("Ridership", "records.csv", raw, db)["added"] == 0
    assert integrity(db) == "ok"
