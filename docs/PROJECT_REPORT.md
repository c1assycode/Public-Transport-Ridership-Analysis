# Project report: Public Transport Ridership Analysis

## Abstract

This project delivers a traceable dashboard for analysing public-transport evidence for Bareilly, Uttar Pradesh. It uses five connected datasets—ridership, routes, stops, fleet, and operations—stored in SQLite and presented through Streamlit. The system validates CSV files, records imports, detects duplicates, exports results, and separates observations from planning and modelled evidence.

## Problem statement and objectives

Bareilly transport information is fragmented and readily available public sources do not provide a verified route-day ridership file. The project aims to organise evidence responsibly, accept future traceable operational files, show analysis only where data permits, and make data gaps visible rather than filling them with assumptions.

## Methodology and system architecture

Source files are preserved after validation. Required fields, dates, numeric ranges, coordinates, duplicate keys, and operational constraints are checked before append-only import. `route_id` links datasets; `bus_id` links fleet and operations. The dashboard aggregates imported data only and labels coverage limitations.

## Results and discussion

The supplied project contains a CMP Phase-1 proposal and a documented 20-stop list, but no verified observed passenger-count series. The app correctly withholds passenger trends, rankings, and completion measures until appropriate records are supplied. It can show stop documentation and planning material without relabelling it as operations.

## Limitations, future scope, and conclusion

Public current route, stop-coordinate, fleet, schedule, and route-day ridership datasets remain incomplete. Future work should seek permissioned/official extracts, record exact reporting units, add source metadata at import, and compare like-for-like periods. The system is a reliable analytical foundation, not a substitute for unavailable evidence.
