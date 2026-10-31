# Initial Bareilly Transport Data Audit

## Confirmed useful material

### 1. Bareilly Comprehensive Mobility Plan (MoHUA / UMTC)
The report contains a Phase 1 service-based bus route proposal with four routes, route lengths, headways, frequencies and fleet requirements. These are planning proposals. They must not be described as actual current routes or current ridership.

The accompanying CSV `data/reference/cmp_phase1_proposed_routes.csv` transcribes the four Phase 1 proposed route rows:
- Bhojipura to Mini Bypass Depot: 17.38 km, 20-minute headway, 3 buses/hour, estimated fleet 5.
- Mini Bypass Depot circular: 19.72 km, 15-minute headway, 4 buses/hour, estimated fleet 7.
- Bareilly Junction to Fatehganj Paschimi: 19.56 km, 15-minute headway, 4 buses/hour, estimated fleet 7.
- Bareilly Junction to Invertis University: 13.62 km, 20-minute headway, 3 buses/hour, estimated fleet 4.

The report table gives 23 required fleet plus 2 additional reserve fleet, total 25, for that Phase 1 proposal. Treat these as planning values from the report, not observed fleet counts.

### 2. CEEW Bareilly factsheet
Provides modelled urban bus-demand scenarios for Bareilly. These can support a clearly labelled scenario/planning discussion. They are not actual observed ridership.

### 3. UPSRTC Sugam Yatra MIS description
Describes reporting capabilities and fields such as passenger counts, revenue, route/schedule adherence and maintenance. This is evidence of the types of operational variables a transport MIS can track, not proof that public Bareilly-level records can be downloaded.

### 4. Open Government Data catalogue
A catalogue entry titled "Buses: Bareilly Smart City" was found, but the page/search result returned "No Result Found". Do not claim a usable dataset has been downloaded until a file is actually obtained and inspected.

## What is not yet confirmed
- A public, downloadable daily Bareilly bus ridership time series.
- A verified route-wise passenger count dataset.
- A complete current stop inventory with coordinates.
- A complete public schedule/actual operations dataset.
- A verified current fleet-and-revenue time series.

## Recommended analytical split
1. **Planning analysis:** Use CMP proposed route data and CEEW model scenarios, explicitly labelled as proposals/model estimates.
2. **Observed ridership analysis:** Keep disabled/empty until actual passenger records are obtained.
3. **Data readiness:** Explain what files are needed to unlock route-day, trip-level, stop-level, revenue and reliability analyses.

## Important
Do not upload `cmp_phase1_proposed_routes.csv` into the application's ridership uploader. It is a route-planning reference dataset, not a ridership CSV. It needs a separate reference-data page or route-planning module.
