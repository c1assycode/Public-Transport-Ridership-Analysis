# Dataset Reference

All examples below are synthetic schema illustrations, not observed Bareilly data.

## Observed CSV import schemas

| Dataset | Required columns | Optional columns |
|---|---|---|
| Ridership | `service_date`, `passengers` | `route_id`, `route_name`, `trips`, `revenue` |
| Routes | `route_id`, `route_name` | `start_point`, `end_point`, `distance_km`, `frequency_per_hour`, `headway_minutes`, `route_type` |
| Stops | `stop_id`, `stop_name` | `latitude`, `longitude`, `route_id`, `stop_sequence` |
| Fleet | `bus_id`, `capacity`, `status` | `route_id`, `vehicle_type` |
| Operations | `service_date`, `route_id`, `bus_id`, `scheduled_trips`, `actual_trips` | `delay_minutes` |

### Illustrative CSV rows

```csv
service_date,route_id,route_name,passengers,trips,revenue
2026-01-01,EXAMPLE-R1,Illustrative route,120,4,2160
```

```csv
route_id,route_name,start_point,end_point,distance_km,frequency_per_hour,headway_minutes,route_type
EXAMPLE-R1,Illustrative route,North terminal,South terminal,12.5,3,20,Demonstration only
```

```csv
stop_id,stop_name,latitude,longitude,route_id,stop_sequence
EXAMPLE-S1,Illustrative stop,28.36,79.41,EXAMPLE-R1,1
```

```csv
bus_id,route_id,vehicle_type,capacity,status
EXAMPLE-B1,EXAMPLE-R1,Midi,35,Available
```

```csv
service_date,route_id,bus_id,scheduled_trips,actual_trips,delay_minutes
2026-01-01,EXAMPLE-R1,EXAMPLE-B1,4,4,3
```

These examples merely illustrate schema. Coordinates, IDs, passenger values and operating values must never be copied into a real import as facts.

## Validation behavior in the current importer

- Required column names must exist. Required text values cannot be blank.
- Numeric values are parsed; required numerics must be valid; negative values are rejected except signed `delay_minutes`.
- `passengers`, `capacity`, `stop_sequence`, `scheduled_trips`, and `actual_trips` must be whole numbers when supplied.
- Dates must parse; stop coordinates are constrained to latitude [-90, 90] and longitude [-180, 180].
- `actual_trips` may not exceed `scheduled_trips` in the current operations schema.
- Duplicate primary keys within the uploaded file are rejected. Database conflicts use `INSERT OR IGNORE`, so pre-existing route, stop, or bus identifiers are not updated; import history records received and added rows.
- The current importer does **not** enforce foreign keys during upload. Data Quality reports unmatched route and bus identifiers afterward.

## Relationships

`route_id` connects route references to ridership, stops, fleet and operations. `bus_id` identifies a vehicle and connects fleet to operations. `trip_id` exists in simulation outputs but is not a column in the current observed ridership or operations CSV templates. A route row is a parent reference; stop rows describe documented stops for that route. One route may have many stops, buses and service records.

## Simulation-only fields

The in-memory demonstration generator has wider schemas than the CSV importer:

- Simulated ridership: `service_date`, `route_id`, `trip_id`, `passengers`, `time_period`, `revenue`, `source_classification`.
- Simulated routes: route identity/name/classification, `distance_km`, `headway_minutes`, `frequency_per_hour`, start/end points.
- Simulated stops: stop ID/name, route ID, sequence, illustrative latitude/longitude, `coordinate_status`.
- Simulated fleet: bus ID, route ID, capacity, vehicle type, `availability_status`.
- Simulated operations: trip/route/bus IDs, scheduled/actual departures and arrivals, distance, operational status, capacity utilisation, derived delay and on-time flag.

All demonstration identifiers start with `SIM-`; stop coordinates carry `Illustrative only`. These records are generated at runtime using seed `20261031` and are not imported into SQLite.
