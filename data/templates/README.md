# CSV import templates

The five templates define the connected evidence model. Their headers are the expected import headers; the ridership example row is not real data.

| Dataset | Required fields | Notes |
|---|---|---|
| Ridership | `service_date`, `passengers` | Record a documented reporting unit such as route-day. |
| Routes | `route_id`, `route_name` | Clearly label observed, historical, or proposed routes. |
| Stops | `stop_id`, `stop_name` | Coordinates are optional; never guess them. |
| Fleet | `bus_id`, `capacity`, `status` | Use a source-issued bus identifier only. |
| Operations | `service_date`, `route_id`, `bus_id`, `scheduled_trips`, `actual_trips` | Actual trips cannot exceed scheduled trips. |

Keep the original source file, URL, period, method, units, geography, and limitations. The importer rejects invalid files, retains an import record, archives accepted originals, and ignores duplicate records without overwriting stored evidence.
