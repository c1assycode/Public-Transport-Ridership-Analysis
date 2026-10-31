from pathlib import Path
import sqlite3, hashlib, io
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

ROOT=Path(__file__).parent
DATA=ROOT/"data"
UPLOADS=DATA/"uploads"
DB=DATA/"ridership.sqlite"
UPLOADS.mkdir(parents=True, exist_ok=True)
st.set_page_config(page_title="Public Transport Ridership Analysis",page_icon="🚌",layout="wide")

def conn():
    c=sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS ridership(
    id INTEGER PRIMARY KEY, service_date TEXT, route_id TEXT, route_name TEXT,
    passengers INTEGER, trips REAL, revenue REAL, source_file TEXT, record_hash TEXT UNIQUE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS imports(
    import_id TEXT PRIMARY KEY, filename TEXT, imported_at TEXT, rows_received INTEGER,
    rows_added INTEGER, status TEXT, sha256 TEXT)""")
    return c

def getdata():
    with conn() as c:
        return pd.read_sql_query("SELECT service_date,route_id,route_name,passengers,trips,revenue,source_file FROM ridership",c)

def validate(df):
    missing={"service_date","passengers"}-set(df.columns)
    if missing: return None,[f"Missing required columns: {', '.join(sorted(missing))}"]
    x=df.copy()
    x["service_date"]=pd.to_datetime(x["service_date"],errors="coerce")
    x["passengers"]=pd.to_numeric(x["passengers"],errors="coerce")
    errors=[]
    if x.service_date.isna().any(): errors.append("Invalid or empty service_date values.")
    if x.passengers.isna().any(): errors.append("Invalid or empty passengers values.")
    if (x.passengers.dropna()<0).any(): errors.append("Passenger counts cannot be negative.")
    for col in ["route_id","route_name"]:
        if col not in x: x[col]="Unspecified"
        x[col]=x[col].fillna("Unspecified").astype(str)
    for col in ["trips","revenue"]:
        if col not in x: x[col]=np.nan
        x[col]=pd.to_numeric(x[col],errors="coerce")
    if errors: return None,errors
    x["service_date"]=x.service_date.dt.strftime("%Y-%m-%d")
    return x[["service_date","route_id","route_name","passengers","trips","revenue"]],[]

def import_file(up):
    raw=up.getvalue()
    digest=hashlib.sha256(raw).hexdigest()
    iid=datetime.now().strftime("%Y%m%d%H%M%S%f")
    (UPLOADS/f"{iid}_{Path(up.name).name}").write_bytes(raw)
    source=pd.read_csv(io.BytesIO(raw))
    clean,errors=validate(source)
    if errors:
        with conn() as c:
            c.execute("INSERT INTO imports VALUES(?,?,?,?,?,?,?)",(iid,up.name,datetime.now().isoformat(),len(source),0,"Rejected",digest))
        return len(source),0,errors
    clean["record_hash"]=clean.astype(str).agg("|".join,axis=1).map(lambda s:hashlib.sha256(s.encode()).hexdigest())
    clean["source_file"]=Path(up.name).name
    with conn() as c:
        before=c.total_changes
        clean.to_sql("_new",c,if_exists="replace",index=False)
        c.execute("""INSERT OR IGNORE INTO ridership(service_date,route_id,route_name,passengers,trips,revenue,source_file,record_hash)
        SELECT service_date,route_id,route_name,passengers,trips,revenue,source_file,record_hash FROM _new""")
        added=c.total_changes-before
        c.execute("DROP TABLE _new")
        c.execute("INSERT INTO imports VALUES(?,?,?,?,?,?,?)",(iid,up.name,datetime.now().isoformat(),len(source),added,"Imported",digest))
    return len(source),added,[]

st.title("🚌 Public Transport Ridership Analysis")
st.caption("Academic case study: Bareilly, Uttar Pradesh")
st.warning("Only imported records are treated as observations. Do not present illustrative or synthetic data as actual Bareilly ridership.")
with st.sidebar:
    page=st.radio(
    "Navigation",
    [
        "Overview",
        "Ridership Analysis",
        "Route Analysis",
        "Research & Route Planning",
        "Data Management",
        "Methodology"
    ]
)
df=getdata()

if page=="Overview":
    st.header("Executive Overview")
    if df.empty:
        st.info("No ridership records imported yet. Open Data Management to upload a CSV.")
        a,b,c=st.columns(3); a.metric("Records","0"); b.metric("Routes","0"); c.metric("Passengers","—")
    else:
        df["service_date"]=pd.to_datetime(df.service_date)
        a,b,c,d=st.columns(4)
        a.metric("Records",f"{len(df):,}")
        b.metric("Passenger total",f"{df.passengers.sum():,.0f}")
        c.metric("Routes",df.route_id.nunique())
        d.metric("First date",df.service_date.min().strftime("%d %b %Y"))
        daily=df.groupby("service_date",as_index=False).passengers.sum()
        st.plotly_chart(px.line(daily,x="service_date",y="passengers",markers=True,title="Recorded passengers over time"),use_container_width=True)
        st.caption(f"Imported data through {df.service_date.max():%d %b %Y}. Coverage depends on source records.")
elif page=="Ridership Analysis":
    st.header("Ridership Analysis")
    if df.empty: st.info("Import a dataset to unlock analysis.")
    else:
        df["service_date"]=pd.to_datetime(df.service_date)
        daily=df.groupby("service_date",as_index=False).passengers.sum()
        st.plotly_chart(px.line(daily,x="service_date",y="passengers",markers=True,title="Daily passenger counts"),use_container_width=True)
        df["weekday"]=df.service_date.dt.day_name()
        order=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        w=df.groupby("weekday",as_index=False).passengers.mean()
        w["weekday"]=pd.Categorical(w.weekday,order,ordered=True); w=w.sort_values("weekday")
        st.plotly_chart(px.bar(w,x="weekday",y="passengers",title="Mean record-level passengers by weekday"),use_container_width=True)
        st.dataframe(df,use_container_width=True)
elif page=="Route Analysis":
    st.header("Route Analysis")
    if df.empty: st.info("Import route-level data to unlock analysis.")
    else:
        r=df.groupby(["route_id","route_name"],as_index=False).agg(passengers=("passengers","sum"),records=("passengers","size"),trips=("trips","sum"))
        r=r.sort_values("passengers",ascending=False)
        st.plotly_chart(px.bar(r,x="route_name",y="passengers",hover_data=["route_id","records","trips"],title="Recorded passengers by route"),use_container_width=True)
        st.dataframe(r,use_container_width=True)
        st.caption("Compare routes only when reporting periods and data coverage are comparable.")
elif page=="Data Management":
    st.header("Data Management Centre")
    st.markdown("**Required:** `service_date`, `passengers`  \n**Optional:** `route_id`, `route_name`, `trips`, `revenue`")
    up=st.file_uploader("Upload ridership CSV",type=["csv"])
    if up and st.button("Validate and import",type="primary"):
        try:
            n,a,e=import_file(up)
            if e: st.error("Import rejected: "+" ".join(e))
            else: st.success(f"Imported. Received {n} rows; added {a} new rows."); st.rerun()
        except Exception as ex: st.error(f"Import failed: {ex}")
    st.subheader("Stored records")
    st.dataframe(df,use_container_width=True)
    with conn() as c: hist=pd.read_sql_query("SELECT * FROM imports ORDER BY imported_at DESC",c)
    st.subheader("Import history"); st.dataframe(hist,use_container_width=True)
    if not df.empty: st.download_button("Export stored data",df.to_csv(index=False).encode(),"ridership_export.csv","text/csv")


elif page == "Research & Route Planning":
    st.header("Bareilly — Research & Route Planning")
    st.caption("Planning evidence from the Bareilly Comprehensive Mobility Plan")

    route_file = ROOT / "data" / "reference" / "cmp_phase1_proposed_routes.csv"

    if not route_file.exists():
        st.error("Route reference dataset not found. Check data/reference/")
    else:
        routes = pd.read_csv(route_file)

        st.warning(
            "These are proposed Phase 1 planning routes, not verified "
            "currently operating routes or observed passenger records."
        )

        a, b, c = st.columns(3)
        a.metric("Proposed routes", len(routes))
        b.metric(
            "Combined route length",
            f"{routes['planned_length_km'].sum():.2f} km"
        )
        c.metric(
            "Estimated proposed fleet",
            int(routes["estimated_required_fleet"].sum())
        )

        st.subheader("Proposed route comparison")

        st.plotly_chart(
            px.bar(
                routes,
                x="proposed_route_name",
                y="planned_length_km",
                color="planned_length_km",
                hover_data=["route_id", "route_type"],
                title="Proposed route lengths (km)"
            ),
            use_container_width=True
        )

        st.plotly_chart(
            px.bar(
                routes,
                x="proposed_route_name",
                y="planned_frequency_buses_per_hour",
                title="Proposed service frequency (buses per hour)"
            ),
            use_container_width=True
        )

        st.subheader("Route planning reference data")
        st.dataframe(routes, use_container_width=True)

        st.subheader("Research interpretation")
        st.write(
            "The planning dataset provides proposed route lengths, "
            "headways, service frequencies and estimated fleet requirements. "
            "It can support comparisons of proposed service design."
        )

        st.info(
            "These planning values cannot establish actual ridership, "
            "current operating frequency or actual fleet availability."
        )

        st.caption(
            "Source: Bareilly Comprehensive Mobility Plan, "
            "MoHUA / UMTC, 2023. See research/source_register.csv."
        )


elif page=="Methodology":
    st.header("Methodology and limitations")
    st.markdown("""
**Study area:** Bareilly, Uttar Pradesh.

**Research focus:** Public transport ridership patterns and route-level demand, subject to available records.

**Input unit:** Each row is a passenger-count record for a documented reporting unit. The source must explain whether this is route-day, trip, stop or another unit.

**Validation:** Dates must parse; passenger counts must be numeric and non-negative. Optional route, trip and revenue fields are retained when available. Duplicate records are ignored using a row hash.

**Interpretation:** Metrics describe imported records only. They are not automatically citywide totals. General traffic counts, survey responses and modelled demand projections must not be relabelled as observed bus passenger boardings.

**Data provenance:** Document publisher, file title, URL, download date, geography, time coverage, measurement method and limitations for every dataset.

**Limitations:** Without verified route, stop, trip, fleet and capacity data, the application cannot reliably establish network coverage, occupancy, service reliability or total citywide ridership.

**Synthetic data:** If used for a software demonstration, label it synthetic and keep it separate from observed data.
""")
    st.markdown("**Research leads to verify:** Bareilly Comprehensive Mobility Plan (MoHUA/UMTC, 2023); CEEW's Bareilly urban bus demand factsheet; UPSRTC public information. Planning projections and traffic surveys are not automatically observed bus ridership.")
