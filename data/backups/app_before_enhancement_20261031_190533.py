from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from transport_core import (DATASETS, DB_PATH, SOURCE_CATALOGUE, backup, frame_for, import_bytes,
                            initialise, integrity, restore_from_bytes, template)

st.set_page_config(page_title="Public Transport Ridership Analysis", page_icon="🚌", layout="wide")
initialise()
st.markdown("""<style>.block-container{padding-top:1.5rem;max-width:1400px}[data-testid="stMetric"]{background:#edf3fa;border:1px solid #cbd8e8;border-left:4px solid #1677ff;padding:12px;border-radius:8px}[data-testid="stMetricLabel"],[data-testid="stMetricValue"],[data-testid="stMetricDelta"]{color:#14253d!important}h1,h2,h3{color:#12233f}.stDataFrame{border:1px solid #d8e1ed;border-radius:8px}</style>""", unsafe_allow_html=True)

def data(name): return frame_for(DATASETS[name]["table"])
def empty(message): st.info(message); st.caption("Use Data Centre to download a template, validate a CSV, and retain source evidence.")
def download(df, label, name): st.download_button(label, df.to_csv(index=False).encode(), name, "text/csv")
def group(df, by, agg): return df.groupby(by, dropna=False, as_index=False).agg(**agg)

st.title("🚌 Public Transport Ridership Analysis")
st.caption("BCA-AI academic dashboard — observations, planning evidence, and unknowns are kept separate.")
with st.sidebar:
    page = st.radio("Explore", ["Overview", "Ridership", "Network", "Operations", "Data Centre", "Data Quality", "Sources & Planning", "System & Method"])
    st.divider(); st.caption("Study area: Bareilly, Uttar Pradesh")

ridership, routes, stops, fleet, operations = (data(n) for n in DATASETS)

if page == "Overview":
    st.header("Evidence overview")
    st.warning("No verified public route-day passenger dataset has been found. Do not read planning figures as observed ridership.")
    for col, (label, value) in zip(st.columns(5), [("Ridership records", len(ridership)), ("Routes documented", len(routes)), ("Stops documented", len(stops)), ("Fleet records", len(fleet)), ("Operation records", len(operations))]): col.metric(label, f"{value:,}")
    if ridership.empty: empty("Observed ridership analysis is waiting for a documented dataset.")
    else:
        r=ridership.copy(); r.service_date=pd.to_datetime(r.service_date)
        daily=group(r,"service_date",{"passengers":("passengers","sum")})
        st.plotly_chart(px.line(daily,x="service_date",y="passengers",markers=True,title="Recorded passengers by service date"),use_container_width=True)
    st.subheader("What this system can establish")
    st.write("It calculates only from imported records and exposes coverage, missing links and import history. It cannot estimate city-wide demand without an identified source and reporting scope.")

elif page == "Ridership":
    st.header("Observed ridership")
    if ridership.empty:
        empty("No observed passenger records have been imported.")
        st.markdown("Required fields: `service_date` and `passengers`. Optional fields: `route_id`, `route_name`, `trips`, and `revenue`.")
        st.download_button("Download ridership CSV template",template("Ridership"),"ridership_template.csv","text/csv")
    else:
        r=ridership.copy(); r.service_date=pd.to_datetime(r.service_date); d1,d2=r.service_date.min().date(),r.service_date.max().date()
        dates=st.date_input("Service-date range",(d1,d2),min_value=d1,max_value=d2)
        choices=sorted(r.route_id.fillna("Unspecified").unique()); selected=st.multiselect("Route IDs",choices,default=choices)
        r=r[(r.service_date.dt.date>=dates[0])&(r.service_date.dt.date<=dates[1])&r.route_id.fillna("Unspecified").isin(selected)]
        a,b,c=st.columns(3); a.metric("Recorded passengers",f"{r.passengers.sum():,.0f}"); b.metric("Records",len(r)); c.metric("Routes",r.route_id.nunique())
        daily=group(r,"service_date",{"passengers":("passengers","sum")}); ranking=group(r,["route_id","route_name"],{"passengers":("passengers","sum"),"records":("passengers","size")}).sort_values("passengers",ascending=False)
        left,right=st.columns(2); left.plotly_chart(px.line(daily,x="service_date",y="passengers",markers=True,title="Daily recorded passengers"),use_container_width=True); right.plotly_chart(px.bar(ranking,x="route_name",y="passengers",hover_data=["route_id","records"],title="Route ranking"),use_container_width=True)
        st.caption("Compare routes only when their reporting period and unit are comparable."); st.dataframe(r,use_container_width=True); download(r,"Export filtered ridership","ridership_export.csv")

elif page == "Network":
    st.header("Network analysis")
    r=routes.copy(); s=stops.copy()
    r["classification"]=r.route_type.fillna("").map(lambda v:"Proposed" if "propos" in v.lower() else "Existing reference" if "existing" in v.lower() else "Unclassified")
    r["documented_stop_count"]=r.route_id.map(s.groupby("route_id").stop_id.nunique() if not s.empty else {}).fillna(0).astype(int)
    classes=st.multiselect("Route classification",sorted(r.classification.unique()),default=sorted(r.classification.unique()))
    filtered=r[r.classification.isin(classes)]
    a,b,c=st.columns(3); a.metric("Routes in view",len(filtered)); b.metric("Documented stops",int(filtered.documented_stop_count.sum())); c.metric("Stops with coordinates",int(s.latitude.notna().sum()) if not s.empty else 0)
    left,right=st.columns(2)
    if not filtered.empty:
        left.plotly_chart(px.bar(filtered,x="route_name",y="distance_km",color="classification",hover_data=["route_id","documented_stop_count"],title="Route distance comparison (km)"),use_container_width=True)
        right.plotly_chart(px.bar(filtered,x="route_name",y="documented_stop_count",color="classification",hover_data=["route_id"],title="Documented stops by route"),use_container_width=True)
        st.subheader("Route details")
        chosen=st.selectbox("Select route",filtered.route_id.tolist(),format_func=lambda rid:f"{rid} — {filtered.loc[filtered.route_id==rid,'route_name'].iloc[0]}")
        detail=filtered[filtered.route_id==chosen].iloc[0]; st.write(f"**{detail.route_name}** · {detail.classification} · {detail.distance_km if pd.notna(detail.distance_km) else 'Not documented'} km · {detail.documented_stop_count} linked stops")
        route_stops=s[s.route_id==chosen].sort_values("stop_sequence",na_position="last")
        if not route_stops.empty:
            route_stops["sequence_label"]=route_stops.stop_sequence.fillna(-1).astype(int).astype(str)
            st.plotly_chart(px.line(route_stops,x="sequence_label",y="stop_name",markers=True,hover_data=["stop_id"],title="Stop sequence (documented order)"),use_container_width=True)
            st.dataframe(route_stops.drop(columns=["record_hash","sequence_label"],errors="ignore"),use_container_width=True)
        else: st.info("No stops are linked to this route in the stored records.")
        st.subheader("Route comparison table"); st.dataframe(filtered[["route_id","route_name","classification","distance_km","documented_stop_count","route_type","source_file"]],use_container_width=True)
    else: empty("No routes match the selected classification.")
    if not fleet.empty:
        st.subheader("Fleet availability and capacity"); available=fleet[fleet.status.str.lower().isin(["available","active","in service"])]; st.metric("Available/active buses",len(available)); st.dataframe(fleet.drop(columns=["record_hash"],errors="ignore"),use_container_width=True)
    if routes.empty and stops.empty and fleet.empty: empty("No network data has been imported.")

elif page == "Operations":
    st.header("Service delivery")
    if operations.empty: empty("No scheduled-versus-actual trip records have been imported.")
    else:
        o=operations.copy(); a,b,c=st.columns(3); a.metric("Scheduled trips",int(o.scheduled_trips.sum())); b.metric("Actual trips",int(o.actual_trips.sum())); c.metric("Completion rate",f"{100*o.actual_trips.sum()/o.scheduled_trips.sum():.1f}%" if o.scheduled_trips.sum() else "—")
        route=group(o,"route_id",{"scheduled":("scheduled_trips","sum"),"actual":("actual_trips","sum"),"mean_delay":("delay_minutes","mean")}); route["completion %"]=(100*route.actual/route.scheduled).round(1)
        st.plotly_chart(px.bar(route,x="route_id",y=["scheduled","actual"],barmode="group",title="Scheduled and actual trips"),use_container_width=True); st.dataframe(route,use_container_width=True); download(o,"Export operations","operations_export.csv")

elif page == "Data Centre":
    st.header("Data Centre"); st.caption("Imports append only. Existing records are never overwritten; duplicate keys and hashes are ignored and logged.")
    dataset=st.selectbox("Dataset",list(DATASETS)); st.download_button(f"Download {dataset} template",template(dataset),f"{dataset.lower()}_template.csv","text/csv")
    uploaded=st.file_uploader("CSV file",type="csv")
    if uploaded and st.button("Validate and import",type="primary"):
        result=import_bytes(dataset,uploaded.name,uploaded.getvalue())
        if result["errors"]: st.error("Import rejected"); [st.write("• "+e) for e in result["errors"]]
        else: st.success(f"Received {result['received']} rows; added {result['added']} new rows.")
    st.subheader("Stored data and exports"); chosen=st.selectbox("Explore dataset",list(DATASETS),key="explore"); shown=data(chosen); st.dataframe(shown,use_container_width=True); download(shown,f"Export {chosen}",f"bareilly_{chosen.lower()}.csv")
    st.subheader("Import history"); history=frame_for("dataset_imports"); st.dataframe(history.sort_values("imported_at",ascending=False) if not history.empty else history,use_container_width=True)

elif page == "Data Quality":
    st.header("Data quality and relationship checks")
    checks=[{"Dataset":label,"Records":len(df),"Source file present":int(df.source_file.notna().sum()) if not df.empty else 0} for label,df in [("Ridership",ridership),("Routes",routes),("Stops",stops),("Fleet",fleet),("Operations",operations)]]; st.dataframe(pd.DataFrame(checks),use_container_width=True)
    route_ids=set(routes.route_id.dropna()); links=[]
    for label,df in [("Stops",stops),("Fleet",fleet),("Operations",operations),("Ridership",ridership)]:
        refs=set(df.route_id.dropna().astype(str)) if not df.empty else set(); links.append({"Dataset":label,"Route references":len(refs),"Unmatched references":", ".join(sorted(refs-route_ids)) or "None"})
    st.subheader("Route-linkage check"); st.dataframe(pd.DataFrame(links),use_container_width=True); st.caption("Unmatched IDs are completeness warnings, not evidence of an error.")

elif page == "Sources & Planning":
    st.header("Source register and planning evidence"); st.info("Planning proposals and modelled demand are intentionally not loaded into operational tables.")
    catalogue=pd.DataFrame(SOURCE_CATALOGUE,columns=["Category","Source name","Publisher","Original URL","Publication/collection date","Coverage","Units","Collection method","Limitations"]); st.dataframe(catalogue,use_container_width=True); download(catalogue,"Export source register","source_register.csv")
    ref=Path("data/reference/cmp_phase1_proposed_routes.csv")
    if ref.exists():
        st.subheader("CMP Phase-1 proposed routes (reference only)"); plan=pd.read_csv(ref); st.dataframe(plan,use_container_width=True); download(plan,"Export planning reference","cmp_phase1_proposed_routes.csv"); st.caption("These are 2023 CMP service-based proposals, not confirmed current routes, fleet or operations.")
    st.subheader("Register another source")
    with st.form("source_form"):
        name=st.text_input("Source name"); publisher=st.text_input("Publisher"); url=st.text_input("Original URL")
        date=st.text_input("Publication or collection date"); geography=st.text_input("Geographical coverage",value="Bareilly, Uttar Pradesh"); units=st.text_input("Measurement units")
        method=st.text_input("Data collection method"); limitations=st.text_area("Limitations"); submitted=st.form_submit_button("Save source")
    if submitted:
        if not (name.strip() and publisher.strip() and url.strip()): st.error("Source name, publisher, and original URL are required.")
        else:
            import sqlite3
            with sqlite3.connect(DB_PATH) as c: c.execute("INSERT INTO data_sources(dataset_type,source_name,publisher,source_url,publication_date,geography,measurement_unit,measurement_method,limitations,added_at) VALUES(?,?,?,?,?,?,?,?,?,datetime('now'))",("User registered",name.strip(),publisher.strip(),url.strip(),date.strip(),geography.strip(),units.strip(),method.strip(),limitations.strip()))
            st.success("Source registered.")

else:
    st.header("System, method and recovery"); st.success("SQLite integrity check: "+integrity())
    st.subheader("Backup")
    if st.button("Create database backup",type="primary"):
        saved=backup(); st.success(f"Backup created: {saved.name}")
    st.download_button("Download current database",DB_PATH.read_bytes(),"public_transport_backup.sqlite","application/x-sqlite3")
    st.subheader("Controlled recovery")
    restore_file=st.file_uploader("SQLite backup to restore",type=["sqlite","db"],key="restore")
    confirmation=st.text_input("Type RESTORE to confirm replacement of the current database")
    if restore_file and confirmation == "RESTORE" and st.button("Validate and restore backup"):
        try:
            preserved=restore_from_bytes(restore_file.getvalue()); st.success(f"Backup restored. Previous database saved as {preserved.name}.")
        except Exception as ex: st.error(f"Restore rejected: {ex}")
    st.caption("Recovery validates the uploaded SQLite file and makes a timestamped backup of the current database first.")
    st.subheader("Method")
    st.markdown("""**Data types.** Observed records are imported CSV rows. Published aggregate statistics, planning estimates and modelled projections remain labelled separately.

**Workflow.** Download template → retain source URL/method → validate/import → inspect history and quality checks → filter/export results.

**Limits.** No public downloadable Bareilly route-day ridership series was verified during the audit. The dashboard therefore shows an honest empty state until traceable records are supplied. `route_id` connects the five datasets; `bus_id` connects operations to fleet.""")
