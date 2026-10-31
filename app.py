from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from simulation import generate_simulation
from transport_core import DATASETS, DB_PATH, SOURCE_CATALOGUE, backup, frame_for, import_bytes, initialise, integrity, restore_from_bytes, template

st.set_page_config(page_title="Public Transport Ridership Analysis",page_icon="🚌",layout="wide")
initialise()
st.markdown("""<style>.block-container{padding-top:1.2rem;max-width:1450px}[data-testid="stMetric"]{background:#edf3fa;border:1px solid #cbd8e8;border-left:4px solid #1677ff;padding:12px;border-radius:8px}[data-testid="stMetricLabel"],[data-testid="stMetricValue"],[data-testid="stMetricDelta"]{color:#14253d!important}h1,h2,h3{color:#12233f}.stDataFrame{border:1px solid #d8e1ed;border-radius:8px}</style>""",unsafe_allow_html=True)

def stored(dataset): return frame_for(DATASETS[dataset]["table"])
def download(df,label,name): st.download_button(label,df.to_csv(index=False).encode(),name,"text/csv")
def group(df,by,agg): return df.groupby(by,dropna=False,as_index=False).agg(**agg)

st.title("🚌 Public Transport Ridership Analysis")
st.caption("Bareilly, Uttar Pradesh, India · BCA-AI academic project")
with st.sidebar:
    st.header("Analysis mode")
    mode=st.radio("Select data mode",["Research / Observed Data","Simulation / Demonstration Data"])
    page=st.radio("Navigation",["Overview","Ridership","Network","Operations","Data Centre","Data Quality","Sources & Planning","System & Method"])
if mode.startswith("Simulation"):
    st.warning("SIMULATION MODE — all figures and coordinates shown are synthetic demonstrations. They are not observed Bareilly transport statistics.",icon="⚠️")
    sim=generate_simulation()
    ds={"Ridership":sim["ridership"],"Routes":sim["routes"],"Stops":sim["stops"],"Fleet":sim["fleet"],"Operations":sim["operations"]}
else:
    ds={k:stored(k) for k in DATASETS}
ridership,routes,stops,fleet,operations=(ds[k] for k in ["Ridership","Routes","Stops","Fleet","Operations"])
source_label="Simulated demonstration" if mode.startswith("Simulation") else "Observed / documented records"

if page=="Overview":
    st.header("Executive overview")
    if ridership.empty:
        st.info("No observed ridership records are available. Import a verified dataset in Data Centre.")
        st.download_button("Download ridership CSV template",template("Ridership"),"ridership_template.csv","text/csv")
    else:
        passenger_col="passengers"; trip_count=ridership.trip_id.nunique() if "trip_id" in ridership else ridership.trips.sum() if "trips" in ridership else len(ridership)
        operational_routes=routes[~routes.classification.astype(str).str.contains("propos",case=False)] if "classification" in routes else routes[~routes.route_type.astype(str).str.contains("propos",case=False)] if "route_type" in routes else routes
        available=fleet.status.astype(str).str.lower().isin(["available","active","in service"]).sum() if "status" in fleet else fleet.availability_status.astype(str).str.lower().eq("available").sum() if "availability_status" in fleet else 0
        occupancy=operations.capacity_utilisation.mean()*100 if "capacity_utilisation" in operations and len(operations) else None
        ontime=operations.on_time.mean()*100 if "on_time" in operations and len(operations) else None
        revenue=ridership.revenue.sum() if "revenue" in ridership else None
        k=st.columns(7)
        vals=[("Passengers",f"{ridership.passengers.sum():,.0f}"),("Trips",f"{trip_count:,.0f}"),("Active routes",str(operational_routes.route_id.nunique() if not operational_routes.empty else 0)),("Available fleet",str(available)),("Avg. occupancy",f"{occupancy:.1f}%" if occupancy is not None else "—"),("On-time",f"{ontime:.1f}%" if ontime is not None else "—"),("Revenue",f"₹{revenue:,.0f}" if revenue is not None else "—")]
        for col,(label,value) in zip(k,vals): col.metric(label,value,help=f"Calculated from {source_label.lower()} currently selected.")
        r=ridership.copy(); r["service_date"]=pd.to_datetime(r.service_date)
        if "time_period" not in r: r["time_period"]="Unspecified"
        routes_list=sorted(r.route_id.dropna().unique()); selected=st.multiselect("Routes",routes_list,default=routes_list,key="overview_routes")
        r=r[r.route_id.isin(selected)]
        daily=group(r,"service_date",{"passengers":("passengers","sum")})
        left,right=st.columns(2)
        left.plotly_chart(px.line(daily,x="service_date",y="passengers",markers=True,title=f"Daily passengers · {source_label}",labels={"service_date":"Service date","passengers":"Passengers"}),use_container_width=True)
        rank=group(r,"route_id",{"passengers":("passengers","sum")}).sort_values("passengers",ascending=False)
        right.plotly_chart(px.bar(rank,x="route_id",y="passengers",title="Passenger demand by route",labels={"route_id":"Route ID","passengers":"Passengers"}),use_container_width=True)
        c1,c2=st.columns(2)
        c1.plotly_chart(px.bar(group(r,"time_period",{"passengers":("passengers","mean")}),x="time_period",y="passengers",title="Average demand by time period",labels={"time_period":"Time period","passengers":"Mean passengers"}),use_container_width=True)
        r["day_type"]=pd.to_datetime(r.service_date).dt.dayofweek.map(lambda d:"Weekend" if d>=5 else "Weekday")
        c2.plotly_chart(px.bar(group(r,"day_type",{"passengers":("passengers","mean")}),x="day_type",y="passengers",title="Weekday vs weekend average per record",labels={"day_type":"Day type","passengers":"Mean passengers"}),use_container_width=True)
    if page=="Overview" and mode.startswith("Research"):
        st.caption("KPI values reflect imported records only. Proposed routes are excluded from active-route counts.")

elif page=="Ridership":
    st.header("Ridership analysis")
    if ridership.empty:
        st.info("No observed passenger records have been imported. Required: service_date and passengers.")
        st.download_button("Download ridership CSV template",template("Ridership"),"ridership_template.csv","text/csv")
    else:
        r=ridership.copy(); r.service_date=pd.to_datetime(r.service_date)
        route_options=sorted(r.route_id.dropna().unique()); selected=st.multiselect("Routes",route_options,default=route_options)
        lo,hi=r.service_date.min().date(),r.service_date.max().date(); dates=st.date_input("Date range",(lo,hi),min_value=lo,max_value=hi)
        r=r[r.route_id.isin(selected)&r.service_date.dt.date.between(dates[0],dates[1])]
        if not r.empty:
            r["week"]=r.service_date.dt.to_period("W").dt.start_time; r["month"]=r.service_date.dt.to_period("M").dt.start_time; r["day_type"]=r.service_date.dt.dayofweek.map(lambda d:"Weekend" if d>=5 else "Weekday")
            if "time_period" not in r:r["time_period"]="Unspecified"
            period=st.radio("Trend granularity",["Daily","Weekly","Monthly"],horizontal=True)
            col="service_date" if period=="Daily" else "week" if period=="Weekly" else "month"
            trend=group(r,col,{"passengers":("passengers","sum")}).sort_values(col); trend["moving_average"]=trend.passengers.rolling(7 if period=="Daily" else 4,min_periods=1).mean()
            st.plotly_chart(px.line(trend,x=col,y=["passengers","moving_average"],markers=True,title=f"{period} passengers and moving average",labels={col:period,"value":"Passengers","variable":"Series"}),use_container_width=True)
            a,b=st.columns(2); route=group(r,"route_id",{"passengers":("passengers","sum")}).sort_values("passengers",ascending=False); a.plotly_chart(px.bar(route,x="route_id",y="passengers",title="Route comparison"),use_container_width=True)
            b.plotly_chart(px.bar(group(r,"time_period",{"passengers":("passengers","mean")}),x="time_period",y="passengers",title="Peak-period demand"),use_container_width=True)
            st.plotly_chart(px.histogram(r,x="passengers",nbins=25,title="Passenger count distribution"),use_container_width=True)
            st.caption(f"Highest period: {trend.loc[trend.passengers.idxmax(),col]} · lowest period: {trend.loc[trend.passengers.idxmin(),col]}.")
            st.dataframe(r,use_container_width=True); download(r,"Export filtered ridership","ridership_filtered.csv")
        else: st.info("No records match the selected filters.")

elif page=="Network":
    st.header("Network analysis")
    if routes.empty: st.info("No route records are available.")
    else:
        r=routes.copy(); typ="classification" if "classification" in r else "route_type"; r["route_class"]=r[typ].fillna("Unclassified")
        classes=st.multiselect("Route classification",sorted(r.route_class.unique()),default=sorted(r.route_class.unique())); r=r[r.route_class.isin(classes)]
        if stops.empty: r["documented_stop_count"]=0
        else:r["documented_stop_count"]=r.route_id.map(stops.groupby("route_id").stop_id.nunique()).fillna(0).astype(int)
        operational=r[~r.route_class.str.contains("propos",case=False)]
        a,b,c=st.columns(3); a.metric("Routes shown",len(r)); b.metric("Documented stops linked",int(r.documented_stop_count.sum())); c.metric("Operationally classified",len(operational))
        left,right=st.columns(2); left.plotly_chart(px.bar(r,x="route_name",y="distance_km",color="route_class",hover_data=["route_id"],title="Route distance comparison",labels={"distance_km":"Distance (km)"}),use_container_width=True); right.plotly_chart(px.bar(r,x="route_name",y="documented_stop_count",color="route_class",title="Documented stops by route"),use_container_width=True)
        chosen=st.selectbox("Route details",r.route_id,format_func=lambda x:f"{x} — {r.loc[r.route_id==x,'route_name'].iloc[0]}"); detail=r[r.route_id==chosen].iloc[0]; st.write(f"**{detail.route_name}** · {detail.route_class} · {detail.distance_km if pd.notna(detail.distance_km) else 'Unknown'} km · {detail.documented_stop_count} linked stops")
        rs=stops[stops.route_id==chosen].sort_values("stop_sequence") if not stops.empty else stops
        if not rs.empty:
            st.plotly_chart(px.line(rs,x="stop_sequence",y="stop_name",markers=True,title="Stop sequence",hover_data=["stop_id"]),use_container_width=True); st.dataframe(rs,use_container_width=True)
            if "latitude" in rs and rs.latitude.notna().all() and ("coordinate_status" not in rs or rs.coordinate_status.eq("Illustrative only").any()): st.caption("Map coordinates are illustrative simulation coordinates.")
            elif "latitude" in rs and rs.latitude.notna().any(): st.map(rs.dropna(subset=["latitude","longitude"])[["latitude","longitude"]])
        else: st.info("No stops are linked to this route in the selected data mode.")
        st.dataframe(r[["route_id","route_name","route_class","distance_km","documented_stop_count"]],use_container_width=True)

elif page=="Operations":
    st.header("Operations and fleet analysis")
    if operations.empty: st.info("No operation records are available. Import documented scheduled and actual service records in Data Centre.")
    else:
        o=operations.copy()
        if "delay_minutes" not in o:o["delay_minutes"]=(pd.to_datetime(o.actual_departure)-pd.to_datetime(o.scheduled_departure)).dt.total_seconds()/60
        if "on_time" not in o:o["on_time"]=o.delay_minutes.le(5)
        a,b,c,d=st.columns(4); a.metric("Trips",len(o)); b.metric("On-time",f"{o.on_time.mean()*100:.1f}%"); c.metric("Mean departure delay",f"{o.delay_minutes.mean():.1f} min"); d.metric("Completed",int(o.operational_status.eq("Completed").sum()))
        route=group(o,"route_id",{"trips":("trip_id","nunique"),"mean_delay":("delay_minutes","mean"),"on_time_rate":("on_time","mean")}); route["on_time_rate"]*=100
        st.plotly_chart(px.bar(route,x="route_id",y="mean_delay",color="on_time_rate",title="Route reliability and mean delay",labels={"mean_delay":"Mean departure delay (minutes)","on_time_rate":"On-time (%)"}),use_container_width=True)
        daily=o.assign(service_date=pd.to_datetime(o.scheduled_departure).dt.date).groupby("service_date",as_index=False).agg(trips=("trip_id","nunique"),delay=("delay_minutes","mean")); st.plotly_chart(px.line(daily,x="service_date",y="trips",title="Daily scheduled demonstration trips"),use_container_width=True)
        st.subheader("Fleet")
        avail=fleet.availability_status.eq("Available") if "availability_status" in fleet else fleet.status.astype(str).str.lower().eq("available")
        a,b,c=st.columns(3); a.metric("Fleet size",len(fleet)); b.metric("Available",int(avail.sum())); c.metric("Average capacity",f"{fleet.capacity.mean():.1f}" if len(fleet) and "capacity" in fleet else "—")
        utilization=o.groupby("bus_id",as_index=False).agg(trips=("trip_id","nunique")); st.plotly_chart(px.bar(utilization,x="bus_id",y="trips",title="Vehicle trip assignments"),use_container_width=True)
        st.subheader("Operational exceptions"); st.dataframe(o[(o.delay_minutes>10)|(~o.operational_status.eq("Completed"))],use_container_width=True)

elif page=="Data Centre":
    st.header("Data Centre")
    if mode.startswith("Simulation"): st.info("Simulation datasets are generated in memory and never imported into the observed SQLite tables.")
    else:
        dataset=st.selectbox("Dataset to import",list(DATASETS)); st.download_button("Download CSV template",template(dataset),f"{dataset.lower()}_template.csv","text/csv")
        upload=st.file_uploader("Select CSV file",type=["csv"])
        if upload:
            try:
                preview=pd.read_csv(upload); st.subheader("Preview"); st.dataframe(preview.head(20),use_container_width=True)
                st.caption(f"{len(preview):,} rows · {len(preview.columns)} columns")
            except Exception as exc: preview=None; st.error(f"Could not preview CSV: {exc}")
            if preview is not None and st.button("Validate and import",type="primary"):
                result=import_bytes(dataset,upload.name,upload.getvalue())
                if result["errors"]: st.error("Import rejected: "+"; ".join(result["errors"]))
                else: st.success(f"Imported {result['added']} new rows from {result['received']} received.")
        source=st.expander("Register source metadata")
        with source:
            with st.form("source_metadata"):
                name=st.text_input("Source name"); publisher=st.text_input("Publisher"); url=st.text_input("Original URL"); pubdate=st.text_input("Publication/collection date"); units=st.text_input("Units"); period=st.text_input("Reference period"); limitation=st.text_area("Limitations"); save=st.form_submit_button("Save source")
            if save and name and publisher and url:
                import sqlite3
                with sqlite3.connect(DB_PATH) as c:c.execute("INSERT INTO data_sources(dataset_type,source_name,publisher,source_url,publication_date,geography,coverage_period,measurement_unit,limitations,added_at) VALUES(?,?,?,?,?,?,?,?,?,datetime('now'))",(dataset,name,publisher,url,pubdate,"Bareilly",period,units,limitation))
                st.success("Source metadata saved.")
        chosen=st.selectbox("Explore stored dataset",list(DATASETS),key="explorer"); frame=stored(chosen); st.dataframe(frame,use_container_width=True); download(frame,"Export dataset",f"{chosen.lower()}_export.csv")
        history=frame_for("dataset_imports"); st.subheader("Import history"); st.dataframe(history.sort_values("imported_at",ascending=False),use_container_width=True) if not history.empty else st.info("No imports recorded yet.")

elif page=="Data Quality":
    st.header("Data quality")
    summary=[]
    for name,df in ds.items():
        summary.append({"Dataset":name,"Rows":len(df),"Missing cells":int(df.isna().sum().sum()) if not df.empty else 0,"Duplicate rows":int(df.duplicated().sum()) if not df.empty else 0,"Date coverage":f"{df.service_date.min()} to {df.service_date.max()}" if "service_date" in df and not df.empty else "Not applicable / no records"})
    st.dataframe(pd.DataFrame(summary),use_container_width=True)
    route_ids=set(routes.route_id.astype(str)) if not routes.empty else set(); bus_ids=set(fleet.bus_id.astype(str)) if not fleet.empty else set()
    for name,df in [("Ridership",ridership),("Stops",stops),("Fleet",fleet),("Operations",operations)]:
        if df.empty: continue
        if "route_id" in df:
            unmatched=sorted(set(df.route_id.dropna().astype(str))-route_ids)
            if unmatched: st.warning(f"{name}: route IDs without route records: {', '.join(unmatched[:12])}")
        if "bus_id" in df:
            unmatched=sorted(set(df.bus_id.dropna().astype(str))-bus_ids)
            if unmatched: st.warning(f"{name}: bus IDs without fleet records: {', '.join(unmatched[:12])}")
    if not mode.startswith("Simulation"):
        history=frame_for("dataset_imports"); rejected=history[history.status=="Rejected"] if not history.empty else history
        st.subheader("Import errors"); st.dataframe(rejected,use_container_width=True) if not rejected.empty else st.success("No rejected imports in recorded history.")
    st.caption("Missing links and incomplete date coverage indicate where evidence collection can improve.")

elif page=="Sources & Planning":
    st.header("Sources, published evidence and planning")
    catalogue=pd.DataFrame(SOURCE_CATALOGUE,columns=["Category","Source name","Publisher","Original URL","Publication/collection date","Geography","Units","Method","Limitations"]); st.dataframe(catalogue,use_container_width=True); download(catalogue,"Export source register","source_register.csv")
    st.subheader("Existing route and stop references"); st.caption("Existing route references are kept distinct from proposed CMP routes.")
    existing=routes[~routes.get("route_type",pd.Series(dtype=str)).astype(str).str.contains("propos",case=False)] if not routes.empty and "route_type" in routes else pd.DataFrame()
    proposed=pd.read_csv("data/reference/cmp_phase1_proposed_routes.csv") if Path("data/reference/cmp_phase1_proposed_routes.csv").exists() else pd.DataFrame()
    a,b=st.columns(2); a.markdown("**Documented existing reference**"); a.dataframe(existing,use_container_width=True); b.markdown("**CMP Phase-1 proposals**"); b.dataframe(proposed,use_container_width=True)
    if mode.startswith("Simulation"): st.subheader("Simulation scenario"); st.caption("Synthetic outputs are reproducible with fixed seed 20261031 and cover 90 days.")

else:
    st.header("System and methodology"); st.success("SQLite integrity check: "+integrity())
    if st.button("Create database backup",type="primary"): st.success(f"Backup saved: {backup().name}")
    st.download_button("Download database backup",DB_PATH.read_bytes(),"public_transport_backup.sqlite","application/x-sqlite3")
    restore=st.file_uploader("Recovery file",type=["sqlite","db"]); confirm=st.text_input("Type RESTORE to confirm")
    if restore and confirm=="RESTORE" and st.button("Validate and restore"):
        try: st.success(f"Restored; prior database retained as {restore_from_bytes(restore.getvalue()).name}")
        except Exception as exc: st.error(f"Restore rejected: {exc}")
    st.markdown("**Observed data** comes from user-imported operational files and documented references. **Published aggregate data** retains its original unit and coverage. **Planning data** describes proposals. **Simulation data** is generated with a fixed seed, held in memory, and never written to observed database tables. No verified public daily Bareilly ridership series was found during the project audit; current stop coordinates are also incomplete. Simulated stop coordinates are illustrative only.")
