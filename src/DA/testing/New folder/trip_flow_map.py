import pandas as pd
import pydeck as pdk
import streamlit as st


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_trip_flows(_connection):
    """
    Load trip information together with start/end station
    coordinates and user information.
    """

    query = """
        SELECT
            ft.trip_id,
            ft.duration_sec,
            ft.duration_minute,

            du.user_type,

            s_start.station_id AS start_station_id,
            s_start.station_name AS start_station_name,
            s_start.latitude AS start_latitude,
            s_start.longitude AS start_longitude,

            s_end.station_id AS end_station_id,
            s_end.station_name AS end_station_name,
            s_end.latitude AS end_latitude,
            s_end.longitude AS end_longitude

        FROM fact_trips ft

        INNER JOIN dim_station s_start
            ON ft.start_station_id = s_start.station_id

        INNER JOIN dim_station s_end
            ON ft.end_station_id = s_end.station_id

        INNER JOIN dim_user du
            ON ft.user_id = du.user_id

        WHERE
            s_start.latitude IS NOT NULL
            AND s_start.longitude IS NOT NULL
            AND s_end.latitude IS NOT NULL
            AND s_end.longitude IS NOT NULL
    """

    return _connection.query(query)


# ============================================================
# CREATE STATION DATA
# ============================================================

def create_station_data(df):
    """
    Create a unique station dataframe from the trip data.
    """

    start_stations = df[
        [
            "start_station_id",
            "start_station_name",
            "start_latitude",
            "start_longitude"
        ]
    ].copy()

    start_stations.columns = [
        "station_id",
        "station_name",
        "latitude",
        "longitude"
    ]

    end_stations = df[
        [
            "end_station_id",
            "end_station_name",
            "end_latitude",
            "end_longitude"
        ]
    ].copy()

    end_stations.columns = [
        "station_id",
        "station_name",
        "latitude",
        "longitude"
    ]

    stations = pd.concat(
        [start_stations, end_stations],
        ignore_index=True
    )

    stations = stations.drop_duplicates(
        subset=["station_id"]
    )

    return stations

def aggregate_trip_flows(df):
    """
    Aggregate individual trips into station-to-station flows.

    Each unique start/end station pair becomes one line.
    """

    aggregated = (
        df.groupby(
            [
                "start_station_id",
                "start_station_name",
                "start_latitude",
                "start_longitude",
                "end_station_id",
                "end_station_name",
                "end_latitude",
                "end_longitude"
            ],
            as_index=False
        )
        .agg(
            trip_count=("trip_id", "count"),
            avg_duration=("duration_minute", "mean")
        )
    )

    return aggregated

# ============================================================
# APPLY FILTERS
# ============================================================

def filter_trip_data(
    df,
    user_type,
    min_duration,
    max_duration,
    sample_percent
):

    filtered = df.copy()

    # User type filter
    if user_type != "All":
        filtered = filtered[
            filtered["user_type"] == user_type
        ]

    # Duration filter
    filtered = filtered[
        (filtered["duration_minute"] >= min_duration)
        &
        (filtered["duration_minute"] <= max_duration)
    ]

    # Sampling
    if sample_percent < 100 and len(filtered) > 0:

        filtered = filtered.sample(
            frac=sample_percent / 100,
            random_state=42
        )

    return filtered


# ============================================================
# CREATE MAP
# ============================================================

def create_trip_flow_map(
    df,
    stations,
    color_by="Duration",
    show_flows=True,
    show_stations=True,
    show_start_stations=False,
    show_end_stations=False,
    line_opacity=100,
    line_width=2,
    aggregated=False
):

    layers = []

    # --------------------------------------------------------
    # AGGREGATE TRIPS IF REQUESTED
    # --------------------------------------------------------

    if aggregated and not df.empty:
        df = aggregate_trip_flows(df)

    # --------------------------------------------------------
    # FLOW COLORS
    # --------------------------------------------------------

    if color_by == "User type" and not aggregated:

        def get_user_color(user_type):

            if user_type == "Subscriber":
                return [31, 119, 180, line_opacity]

            return [255, 127, 14, line_opacity]

        df["color"] = df["user_type"].apply(
            get_user_color
        )

    else:

        # Duration / average duration color
        duration_column = (
            "avg_duration"
            if aggregated
            else "duration_minute"
        )

        min_duration = df[duration_column].min()
        max_duration = df[duration_column].max()

        if max_duration == min_duration:

            normalized = pd.Series(
                0.5,
                index=df.index
            )

        else:

            normalized = (
                (df[duration_column] - min_duration)
                /
                (max_duration - min_duration)
            )

        df["color"] = normalized.apply(
            lambda x: [
                int(255 * x),
                int(100 * (1 - x)),
                int(255 * (1 - x)),
                line_opacity
            ]
        )

    # --------------------------------------------------------
    # TRIP FLOW LAYER
    # --------------------------------------------------------
    if aggregated:

        max_trips = df["trip_count"].max()

        if max_trips > 0:
            df["line_width"] = (1 + 8 * ( df["trip_count"] / max_trips) ** 0.5)
        else:
            df["line_width"] = 1
    else:
        df["line_width"] = line_width

    if show_flows and not df.empty:

        flow_layer = pdk.Layer(
            "LineLayer",

            data=df,

            get_source_position=[
                "start_longitude",
                "start_latitude"
            ],

            get_target_position=[
                "end_longitude",
                "end_latitude"
            ],

            get_color="color",

            get_width="line_width",

            pickable=True,

            auto_highlight=True
        )

        layers.append(flow_layer)

    # --------------------------------------------------------
    # STATION LAYER
    # --------------------------------------------------------

    if show_stations:

        station_layer = pdk.Layer(
            "ScatterplotLayer",

            data=stations,

            get_position=[
                "longitude",
                "latitude"
            ],

            get_radius=80,

            get_fill_color=[50, 50, 50, 220],

            get_line_color=[255, 255, 255, 255],

            line_width_min_pixels=1,

            pickable=True,

            auto_highlight=True
        )

        layers.append(station_layer)

    # --------------------------------------------------------
    # START STATIONS
    # --------------------------------------------------------

    if show_start_stations and not df.empty:

        start_station_ids = (
            df["start_station_id"]
            .unique()
        )

        start_stations = stations[
            stations["station_id"].isin(
                start_station_ids
            )
        ]

        start_layer = pdk.Layer(
            "ScatterplotLayer",

            data=start_stations,

            get_position=[
                "longitude",
                "latitude"
            ],

            get_radius=130,

            get_fill_color=[0, 150, 0, 220],

            pickable=True,

            auto_highlight=True
        )

        layers.append(start_layer)

    # --------------------------------------------------------
    # END STATIONS
    # --------------------------------------------------------

    if show_end_stations and not df.empty:

        end_station_ids = (
            df["end_station_id"]
            .unique()
        )

        end_stations = stations[
            stations["station_id"].isin(
                end_station_ids
            )
        ]

        end_layer = pdk.Layer(
            "ScatterplotLayer",

            data=end_stations,

            get_position=[
                "longitude",
                "latitude"
            ],

            get_radius=130,

            get_fill_color=[200, 0, 0, 220],

            pickable=True,

            auto_highlight=True
        )

        layers.append(end_layer)

    # --------------------------------------------------------
    # MAP CENTER
    # --------------------------------------------------------

    if not stations.empty:

        center_lat = stations["latitude"].mean()
        center_lon = stations["longitude"].mean()

    else:

        center_lat = 37.77
        center_lon = -122.42

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=12,
        pitch=0,
        bearing=0
    )

    # --------------------------------------------------------
    # TOOLTIP
    # --------------------------------------------------------

    if aggregated:

        tooltip = {

            "html": """
                <b>From:</b> {start_station_name}<br/>
                <b>To:</b> {end_station_name}<br/>
                <b>Trips:</b> {trip_count}<br/>
                <b>Average duration:</b> {avg_duration} min
            """,

            "style": {
                "backgroundColor": "white",
                "color": "black"
            }
        }

    else:

        tooltip = {

            "html": """
                <b>Trip:</b> {trip_id}<br/>
                <b>From:</b> {start_station_name}<br/>
                <b>To:</b> {end_station_name}<br/>
                <b>Duration:</b> {duration_minute} minutes<br/>
                <b>User:</b> {user_type}
            """,

            "style": {
                "backgroundColor": "white",
                "color": "black"
            }
        }

    # --------------------------------------------------------
    # DECK
    # --------------------------------------------------------

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip
    )

    st.pydeck_chart(
        deck,
        use_container_width=True
    )


# ============================================================
# DASHBOARD COMPONENT
# ============================================================

def trip_flow_dashboard(connection):

    st.subheader("Trip Flow Analysis")

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    trips = load_trip_flows(connection)

    if trips.empty:

        st.warning(
            "No trip data available."
        )

        return

    stations = create_station_data(trips)

    # --------------------------------------------------------
    # SIDEBAR / CONTROLS
    # --------------------------------------------------------

    st.markdown("### Map Controls")

    col1, col2, col3 = st.columns(3)
    map_mode = st.radio(
        "Flow display",
        [
            "Individual trips",
            "Aggregated station flows"
        ],
        horizontal=True
    )

    aggregated = (
        map_mode == "Aggregated station flows"
    )

    with col1:

        color_by = st.selectbox(
            "Color trips by",
            [
                "Duration",
                "User type"
            ]
        )

    with col2:

        user_type = st.selectbox(
            "User type",
            [
                "All",
                "Subscriber",
                "Customer"
            ]
        )

    with col3:

        sample_percent = st.selectbox(
            "Trip sample",
            [
                1,
                2,
                5,
                10,
                25,
                50,
                100
            ],
            index=2,
            format_func=lambda x: f"{x}%"
        )

    # --------------------------------------------------------
    # DURATION FILTER
    # --------------------------------------------------------

    duration_min = float(
        trips["duration_minute"].min()
    )

    duration_max = float(
        trips["duration_minute"].max()
    )

    selected_duration = st.slider(
        "Trip duration (minutes)",
        min_value=duration_min,
        max_value=duration_max,
        value=(duration_min, duration_max)
    )

    # --------------------------------------------------------
    # LAYERS
    # --------------------------------------------------------

    st.markdown("### Layers")

    layer1, layer2, layer3, layer4 = st.columns(4)

    with layer1:

        show_flows = st.checkbox(
            "Trip flows",
            value=True
        )

    with layer2:

        show_stations = st.checkbox(
            "Stations",
            value=True
        )

    with layer3:

        show_start_stations = st.checkbox(
            "Start stations",
            value=False
        )

    with layer4:

        show_end_stations = st.checkbox(
            "End stations",
            value=False
        )

    # --------------------------------------------------------
    # LINE SETTINGS
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        line_opacity = st.slider(
            "Flow transparency",
            min_value=20,
            max_value=220,
            value=100
        )

    with col2:

        line_width = st.slider(
            "Flow line width",
            min_value=1,
            max_value=5,
            value=2
        )

    # --------------------------------------------------------
    # FILTER DATA
    # --------------------------------------------------------

    # First filter without sampling
    filtered_trips = filter_trip_data(
        trips,
        user_type=user_type,
        min_duration=selected_duration[0],
        max_duration=selected_duration[1],
        sample_percent=100
    )

    # Only sample when displaying individual trips
    if not aggregated and sample_percent < 100:

        filtered_trips = filtered_trips.sample(
            frac=sample_percent / 100,
            random_state=42
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    st.markdown("### Map Summary")

    m1, m2, m3 = st.columns(3)

    with m1:

        st.metric(
            "Trips displayed",
            f"{len(filtered_trips):,}"
        )

    with m2:

        st.metric(
            "Stations",
            f"{stations['station_id'].nunique():,}"
        )

    with m3:

        if not filtered_trips.empty:

            avg_duration = (
                filtered_trips[
                    "duration_minute"
                ].mean()
            )

            st.metric(
                "Average duration",
                f"{avg_duration:.1f} min"
            )

    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    create_trip_flow_map(
        filtered_trips,
        stations,
        color_by=color_by,
        show_flows=show_flows,
        show_stations=show_stations,
        show_start_stations=show_start_stations,
        show_end_stations=show_end_stations,
        line_opacity=line_opacity,
        line_width=line_width,
        aggregated=aggregated
    )

    # --------------------------------------------------------
    # LEGEND
    # --------------------------------------------------------

    st.markdown("### Legend")

    if aggregated:

        st.markdown(
            """
            **Aggregated station flows**

            **Line width:**  
            Thin → fewer trips  
            Thick → more trips

            **Line color:**  
            Purple → shorter average duration  
            Red → longer average duration

            **Station:**  
            ● Station
            """
        )

    elif color_by == "User type":

        st.markdown(
            """
            **Individual trip flows**

            🔵 Subscriber  
            🟠 Customer

            **Stations**

            ● Station
            """
        )

    else:

        st.markdown(
            """
            **Individual trip flows**

            **Duration:**  
            Purple → shorter trips  
            Red → longer trips

            **Station:**  
            ● Station
            """
        )