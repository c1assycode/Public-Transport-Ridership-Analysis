# Data dictionary

| Dataset | Field | Type | Required | Meaning / validation |
|---|---|---|---:|---|
| Ridership | `service_date` | ISO date | Yes | Date for the documented reporting unit. |
| Ridership | `passengers` | non-negative integer | Yes | Observed passenger count only; not traffic or a projection. |
| Ridership | `route_id`, `route_name`, `trips`, `revenue` | text/number | No | Must share passenger reporting scope. |
| Routes | `route_id`, `route_name` | text | Yes | Stable source route code and label. |
| Routes | `distance_km`, `frequency_per_hour`, `headway_minutes`, `route_type` | number/text | No | Values require source evidence; label planning proposals. |
| Stops | `stop_id`, `stop_name` | text | Yes | Source-issued/documented identifiers and names. |
| Stops | `latitude`, `longitude` | decimal degrees | No | Valid geographic bounds only; never inferred. |
| Stops | `route_id`, `stop_sequence` | text/integer | No | Relationship to route and documented order. |
| Fleet | `bus_id`, `capacity`, `status` | text/integer/text | Yes | Source vehicle ID, whole capacity and status. |
| Operations | `service_date`, `route_id`, `bus_id`, `scheduled_trips`, `actual_trips` | date/text/integer | Yes | Daily service record; actual cannot exceed scheduled. |
| Operations | `delay_minutes` | number | No | Signed delay value where source definition is retained. |

System fields (`source_file`, `record_hash`, import timestamps) preserve provenance and duplicate detection. Record source name, publisher, URL, collection date, coverage, units, method, and limitations in the source register.
