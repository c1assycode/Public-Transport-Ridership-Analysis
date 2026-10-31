"""Deterministic, isolated demonstration data for the academic dashboard."""
from __future__ import annotations
import numpy as np
import pandas as pd

SEED = 20261031

def generate_simulation(days: int = 90, seed: int = SEED):
    rng = np.random.default_rng(seed)
    routes = pd.DataFrame([
        ("SIM-R1", "Bhojipura to Mini Bypass Depot", "Proposed route scenario", 17.38, 20, 3, "Bhojipura", "Mini Bypass Depot"),
        ("SIM-R2", "Mini Bypass Depot Circular", "Proposed route scenario", 19.72, 15, 4, "Mini Bypass Depot", "Mini Bypass Depot"),
        ("SIM-R3", "Junction to Fatehganj Paschimi", "Proposed route scenario", 19.56, 15, 4, "Bareilly Junction", "Fatehganj Paschimi"),
        ("SIM-R4", "Junction to Invertis University", "Proposed route scenario", 13.62, 20, 3, "Bareilly Junction", "Invertis University"),
    ], columns=["route_id","route_name","classification","distance_km","headway_minutes","frequency_per_hour","start_point","end_point"])
    route_weight = {"SIM-R1":0.82,"SIM-R2":1.10,"SIM-R3":1.24,"SIM-R4":0.95}
    stops=[]
    for i, route in routes.iterrows():
        for seq in range(1, 9):
            # These coordinates are explicitly illustrative and confined to simulation.
            stops.append((f"{route.route_id}-S{seq:02d}",f"Illustrative stop {seq}",route.route_id,seq,28.35 + i*.012 + seq*.0011,79.40 + i*.014 + seq*.0008,"Illustrative only"))
    stops=pd.DataFrame(stops,columns=["stop_id","stop_name","route_id","stop_sequence","latitude","longitude","coordinate_status"])
    fleet=[]
    for i in range(24):
        route_id=routes.route_id[i%4]
        fleet.append((f"SIM-B{i+1:03d}",route_id,35 if i%3 else 40,"Midi" if i%3 else "Standard","Available" if i%8 else "Unavailable"))
    fleet=pd.DataFrame(fleet,columns=["bus_id","route_id","capacity","vehicle_type","availability_status"])
    ridership=[]; operations=[]; trip_num=0
    dates=pd.date_range(end=pd.Timestamp.today().normalize(),periods=days)
    for day in dates:
        weekend=day.dayofweek>=5
        for _,route in routes.iterrows():
            daily_scale=0.76 if weekend else 1.0
            for period,peak in [("Morning peak",1.48),("Off-peak",0.68),("Evening peak",1.57)]:
                base=115*route_weight[route.route_id]*daily_scale*peak
                passengers=max(0,int(rng.normal(base,base*.12)))
                trip_num+=1; trip_id=f"SIM-T{trip_num:06d}"
                available_buses=fleet.loc[(fleet.route_id==route.route_id)&(fleet.availability_status=="Available"),"bus_id"].tolist()
                assigned=available_buses[trip_num%len(available_buses)]
                cap=int(fleet.loc[fleet.bus_id==assigned,"capacity"].iloc[0])
                ridership.append((day.date().isoformat(),route.route_id,trip_id,passengers,period,round(passengers*18.0,2),"SIMULATED"))
                start_hour={"Morning peak":7,"Off-peak":12,"Evening peak":17}[period]
                scheduled=pd.Timestamp(day.date())+pd.Timedelta(hours=start_hour,minutes=int(rng.integers(0,30)))
                delay=max(-3,int(rng.normal(4.5 if period!="Off-peak" else 2,5)))
                duration=max(20,int(route.distance_km/24*60+rng.normal(5,4)))
                actual=scheduled+pd.Timedelta(minutes=delay)
                arrival=scheduled+pd.Timedelta(minutes=duration)
                actual_arrival=arrival+pd.Timedelta(minutes=max(0,delay+int(rng.integers(-2,5))))
                load=min(1.0,passengers/cap)
                operations.append((trip_id,route.route_id,assigned,scheduled,actual,arrival,actual_arrival,route.distance_km,"Completed",load))
    ridership=pd.DataFrame(ridership,columns=["service_date","route_id","trip_id","passengers","time_period","revenue","source_classification"])
    operations=pd.DataFrame(operations,columns=["trip_id","route_id","bus_id","scheduled_departure","actual_departure","scheduled_arrival","actual_arrival","distance_km","operational_status","capacity_utilisation"])
    operations["delay_minutes"]=(operations.actual_departure-operations.scheduled_departure).dt.total_seconds()/60
    operations["on_time"] = operations.delay_minutes.le(5)
    return {"routes":routes,"stops":stops,"fleet":fleet,"ridership":ridership,"operations":operations}
