"""
dash_app.py

Run:
    pip install dash pandas plotly
    python dash_app.py

Expect a CSV file named 'cleaned_fordgobike.csv' in the same folder.
If the file is missing, the script will generate a small dummy dataset so the app runs immediately.
"""

import os
import pandas as pd
import numpy as np
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import datetime

CSV_PATH = "cleaned_fordgobike.csv"

def generate_dummy(n=500):
    rng = pd.date_range("2020-01-01", periods=90, freq="H")
    start = np.random.choice(rng, size=n)
    dur = np.random.exponential(scale=600, size=n).astype(int)  # seconds
    stations = ["Market St @ 7th", "Howard St", "Embarcadero", "Mission St", "Van Ness"]
    df = pd.DataFrame({
        "trip_id": range(1, n+1),
        "start_time": start,
        "duration_sec": dur,
        "start_station_name": np.random.choice(stations, size=n),
        "start_station_latitude": np.random.uniform(37.76, 37.80, size=n),
        "start_station_longitude": np.random.uniform(-122.45, -122.39, size=n),
        "user_type": np.random.choice(["Subscriber", "Customer"], size=n, p=[0.7,0.3]),
        "member_gender": np.random.choice(["Male","Female","Other"], size=n, p=[0.5,0.45,0.05]),
        "age": np.random.randint(18, 70, size=n)
    })
    df["day_of_week"] = df["start_time"].dt.day_name()
    df["month"] = df["start_time"].dt.strftime("%b")
    df["age_group"] = pd.cut(df["age"], bins=[0,29,50,200], labels=["Young","Adult","Senior"])
    return df

def load_data():
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH, parse_dates=["start_time"])
    else:
        print(f"[warning] {CSV_PATH} not found. Generating dummy dataset for demo.")
        df = generate_dummy(1500)
    # ensure columns
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["trip_duration_min"] = df["duration_sec"] / 60.0
    if "age_group" not in df.columns:
        df["age_group"] = pd.cut(df["age"], bins=[0,29,50,200], labels=["Young","Adult","Senior"])
    return df

df = load_data()

app = Dash(__name__)
app.title = "Ford GoBike Dashboard (Demo)"

# unique filter values
user_types = sorted(df["user_type"].dropna().unique())
genders = sorted(df["member_gender"].dropna().unique())
age_groups = sorted(df["age_group"].dropna().unique())

def kpi_cards(total_trips, avg_dur, active_users, popular_station):
    style_card = {
        "padding":"18px","borderRadius":"8px","background":"#fff","boxShadow":"0 1px 3px rgba(0,0,0,0.08)",
        "textAlign":"center","width":"23%","display":"inline-block","marginRight":"1%"
    }
    return html.Div([
        html.Div([
            html.Div(f"{total_trips:,}", style={"fontSize":"28px","fontWeight":"700"}),
            html.Div("Total Trips")
        ], style=style_card),
        html.Div([
            html.Div(f"{avg_dur:.1f} mins", style={"fontSize":"28px","fontWeight":"700"}),
            html.Div("Avg Duration")
        ], style=style_card),
        html.Div([
            html.Div(f"{active_users:,}", style={"fontSize":"28px","fontWeight":"700"}),
            html.Div("Active Users")
        ], style=style_card),
        html.Div([
            html.Div(popular_station, style={"fontSize":"18px","fontWeight":"700"}),
            html.Div("Popular Station")
        ], style=style_card)
    ], style={"display":"flex","justifyContent":"space-between","marginBottom":"18px"})

app.layout = html.Div([
    html.Div([
        # Sidebar filters
        html.Div([
            html.H3("Filters", style={"marginBottom":"10px"}),
            html.Label("Date range"),
            dcc.DatePickerRange(
                id="date_range",
                min_date_allowed=df["start_time"].min().date(),
                max_date_allowed=df["start_time"].max().date(),
                start_date=df["start_time"].min().date(),
                end_date=df["start_time"].max().date()
            ),
            html.Br(), html.Br(),
            html.Label("User Type"),
            dcc.Dropdown(id="user_type", options=[{"label":u,"value":u} for u in user_types], value=None, multi=True, placeholder="All"),
            html.Br(),
            html.Label("Gender"),
            dcc.Dropdown(id="gender", options=[{"label":g,"value":g} for g in genders], value=None, multi=True, placeholder="All"),
            html.Br(),
            html.Label("Age Group"),
            dcc.Checklist(id="age_group", options=[{"label":a,"value":a} for a in age_groups], value=age_groups),
            html.Hr(),
            html.Div("Tip: use filters to update all charts.", style={"fontSize":"12px","color":"#666"})
        ], style={"width":"20%","display":"inline-block","verticalAlign":"top","padding":"20px","background":"#f7f9fc","height":"100vh","boxSizing":"border-box"}),
        
        # Main content
        html.Div([
            html.H2("Ford GoBike Interactive Dashboard", style={"textAlign":"center"}),
            html.Div(id="kpi_row"),
            # Two-column grid for top charts
            html.Div([
                dcc.Graph(id="trips_by_weekday", style={"display":"inline-block","width":"48%"}),
                dcc.Graph(id="trips_by_month", style={"display":"inline-block","width":"48%"})
            ]),
            html.Div([
                dcc.Graph(id="age_distribution", style={"display":"inline-block","width":"48%"}),
                dcc.Graph(id="gender_pie", style={"display":"inline-block","width":"48%"})
            ]),
            html.Div([
                dcc.Graph(id="station_map", style={"width":"60%","display":"inline-block"}),
                dcc.Graph(id="top_routes", style={"width":"38%","display":"inline-block"})
            ]),
            html.Div(id="footer", style={"height":"60px"})
        ], style={"width":"79%","display":"inline-block","padding":"20px","boxSizing":"border-box"})
    ])
])

@app.callback(
    Output("kpi_row","children"),
    Output("trips_by_weekday","figure"),
    Output("trips_by_month","figure"),
    Output("age_distribution","figure"),
    Output("gender_pie","figure"),
    Output("station_map","figure"),
    Output("top_routes","figure"),
    [
        Input("date_range","start_date"),
        Input("date_range","end_date"),
        Input("user_type","value"),
        Input("gender","value"),
        Input("age_group","value")
    ]
)
def update(start_date, end_date, user_type, gender, age_group):
    dff = df.copy()
    if start_date:
        dff = dff[dff["start_time"] >= pd.to_datetime(start_date)]
    if end_date:
        dff = dff[dff["start_time"] <= pd.to_datetime(end_date) + pd.Timedelta(days=1)]
    if user_type:
        if isinstance(user_type, list):
            dff = dff[dff["user_type"].isin(user_type)]
        else:
            dff = dff[dff["user_type"]==user_type]
    if gender:
        if isinstance(gender, list):
            dff = dff[dff["member_gender"].isin(gender)]
        else:
            dff = dff[dff["member_gender"]==gender]
    if age_group:
        dff = dff[dff["age_group"].isin(age_group)]
    # KPIs
    total_trips = len(dff)
    avg_dur = dff["trip_duration_min"].mean() if total_trips>0 else 0
    active_users = dff["trip_id"].nunique()
    popular_station = dff["start_station_name"].mode().iloc[0] if not dff.empty else "N/A"
    kpis = kpi_cards(total_trips, avg_dur, active_users, popular_station)
    # Charts
    trips_wd = dff.groupby("day_of_week").size().reindex(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]).fillna(0)
    fig_weekday = px.line(x=trips_wd.index, y=trips_wd.values, markers=True, title="Trips per day of week")
    month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    if "month" in dff.columns:
        trips_month = dff.groupby("month").size().reindex(month_order).fillna(0)
    else:
        trips_month = dff.groupby(dff["start_time"].dt.strftime("%b")).size().reindex(month_order).fillna(0)
    fig_month = px.bar(x=trips_month.index, y=trips_month.values, title="Trips by month")
    fig_age = px.histogram(dff, x="age", nbins=10, title="Age distribution")
    gender_counts = dff["member_gender"].value_counts().reset_index()
    if gender_counts.empty:
        fig_gender = px.pie(names=["N/A"], values=[1], title="Gender")
    else:
        fig_gender = px.pie(gender_counts, names="index", values="member_gender", title="Gender split")
    # Map
    if not dff.empty and "start_station_latitude" in dff.columns:
        fig_map = px.scatter_mapbox(
            dff.groupby(["start_station_name","start_station_latitude","start_station_longitude"]).size().reset_index(name="trips"),
            lat="start_station_latitude", lon="start_station_longitude", size="trips",
            hover_name="start_station_name", zoom=11, title="Stations (bubble by trips)"
        )
        fig_map.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":30,"l":0,"b":0})
    else:
        fig_map = px.scatter(title="Stations")
    # Top routes (start-end pairs)
    if {"start_station_name","trip_id"}.issubset(dff.columns):
        routes = dff.groupby("start_station_name").size().nlargest(10).reset_index(name="trips")
        fig_routes = px.bar(routes, x="trips", y="start_station_name", orientation="h", title="Top Start Stations")
    else:
        fig_routes = px.bar(title="Top Start Stations")
    return kpis, fig_weekday, fig_month, fig_age, fig_gender, fig_map, fig_routes

if __name__ == "__main__":
    app.run(debug=True)
