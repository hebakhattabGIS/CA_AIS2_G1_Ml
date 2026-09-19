import pandas as pd
import pydeck as pdk
import streamlit as st


# ============================================================
# LOAD TRIP DATA
# ============================================================

@st.cache_data
def load_trip_flows(_connection):
    """
    Load trip data and join each trip to its start and end
    station coordinates.

    Returns one row per trip.
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
            AND s_start.station_id <> s_end.station_id
    """

    return _connection.query(query)


# ============================================================
# CREATE STATION DATA
# ============================================================

def create_station_data(df):
    """
    Create one record per station from the trip data.
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


# ============================================================
# AGGREGATE OD FLOWS
# ============================================================

def aggregate_od_flows(df):
    """
    Aggregate trips into Origin-Destination station pairs.

    One row = one unique station-to-station flow.
    """

    if df.empty:
        return pd.DataFrame()

    od = (
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

    return od


# ============================================================
# SELECT TOP N FLOWS
# ============================================================

def select_top_flows(od_df, top_n):
    """
    Return the strongest OD flows based on trip count.
    """

    if od_df.empty:
        return od_df

    return (
        od_df
        .sort_values(
            "trip_count",
            ascending=False
        )
        .head(top_n)
        .copy()
    )


# ============================================================
# SELECTED STATION FLOWS
# ============================================================

def get_station_flows(
    od_df,
    station_id,
    direction="All",
    top_n=10
):
    """
    Return the strongest flows associated with a selected station.

    direction:
        All
        Outbound
        Inbound
    """

    if od_df.empty or station_id is None:
        return od_df

    if direction == "Outbound":

        result = od_df[
            od_df["start_station_id"] == station_id
        ].copy()

    elif direction == "Inbound":

        result = od_df[
            od_df["end_station_id"] == station_id
        ].copy()

    else:

        result = od_df[
            (od_df["start_station_id"] == station_id)
            |
            (od_df["end_station_id"] == station_id)
        ].copy()

    return (
        result
        .sort_values(
            "trip_count",
            ascending=False
        )
        .head(top_n)
        .copy()
    )


# ============================================================
# PREPARE FLOW COLORS
# ============================================================

def prepare_flow_colors(
    flow_df,
    color_by,
    opacity
):
    """
    Create RGBA colors for the ArcLayer.
    """

    df = flow_df.copy()

    if df.empty:
        return df

    if color_by == "Average duration":

        min_value = df["avg_duration"].min()
        max_value = df["avg_duration"].max()

        if max_value == min_value:

            normalized = pd.Series(
                0.5,
                index=df.index
            )

        else:

            normalized = (
                (df["avg_duration"] - min_value)
                /
                (max_value - min_value)
            )

        def duration_color(value):

            # Short = purple
            # Long = red

            return [
                int(255 * value),
                int(80 * (1 - value)),
                int(180 * (1 - value)),
                opacity
            ]

        df["color"] = normalized.apply(
            duration_color
        )

    else:

        # Trip count color
        min_value = df["trip_count"].min()
        max_value = df["trip_count"].max()

        if max_value == min_value:

            normalized = pd.Series(
                0.5,
                index=df.index
            )

        else:

            normalized = (
                (df["trip_count"] - min_value)
                /
                (max_value - min_value)
            )

        def volume_color(value):

            return [
                int(255 * value),
                int(100 * (1 - value)),
                int(255 * (1 - value)),
                opacity
            ]

        df["color"] = normalized.apply(
            volume_color
        )

    return df


# ============================================================
# PREPARE LINE WIDTHS
# ============================================================

def prepare_line_widths(
    flow_df,
    min_width=2,
    max_width=12
):
    """
    Scale line width according to trip count.

    Square-root scaling prevents the largest flow from
    completely dominating the map.
    """

    df = flow_df.copy()

    if df.empty:
        return df

    max_trips = df["trip_count"].max()

    if max_trips <= 0:

        df["line_width"] = min_width

        return df

    df["line_width"] = (
        min_width
        +
        (
            (
                df["trip_count"]
                /
                max_trips
            ) ** 0.5
        )
        *
        (
            max_width - min_width
        )
    )

    return df


# ============================================================
# CREATE ARC MAP
# ============================================================

def create_arc_map(
    flow_df,
    stations,
    show_flows=True,
    show_stations=True,
    color_by="Average duration",
    opacity=160
):
    """
    Create an interactive ArcLayer map.
    """

    layers = []

    # --------------------------------------------------------
    # FLOW LAYER
    # --------------------------------------------------------

    if show_flows and not flow_df.empty:

        flow_df = prepare_flow_colors(
            flow_df,
            color_by=color_by,
            opacity=opacity
        )

        flow_df = prepare_line_widths(
            flow_df
        )

        arc_layer = pdk.Layer(
            "ArcLayer",

            data=flow_df,

            get_source_position=[
                "start_longitude",
                "start_latitude"
            ],

            get_target_position=[
                "end_longitude",
                "end_latitude"
            ],

            get_source_color="color",
            get_target_color="color",

            get_width="line_width",

            pickable=True,

            auto_highlight=True
        )

        layers.append(arc_layer)

    # --------------------------------------------------------
    # STATION LAYER
    # --------------------------------------------------------

    if show_stations and not stations.empty:

        station_layer = pdk.Layer(
            "ScatterplotLayer",

            data=stations,

            get_position=[
                "longitude",
                "latitude"
            ],

            get_radius=70,

            get_fill_color=[
                80,
                80,
                80,
                220
            ],

            get_line_color=[
                255,
                255,
                255,
                255
            ],

            line_width_min_pixels=1,

            pickable=True,

            auto_highlight=True
        )

        layers.append(station_layer)

    # --------------------------------------------------------
    # MAP CENTER
    # --------------------------------------------------------

    if not stations.empty:

        center_lat = stations["latitude"].mean()
        center_lon = stations["longitude"].mean()

    elif not flow_df.empty:

        center_lat = (
            flow_df["start_latitude"].mean()
            +
            flow_df["end_latitude"].mean()
        ) / 2

        center_lon = (
            flow_df["start_longitude"].mean()
            +
            flow_df["end_longitude"].mean()
        ) / 2

    else:

        center_lat = 37.77
        center_lon = -122.42

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

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

    tooltip = {

        "html": """

        <b>Origin:</b>
        {start_station_name}
        <br/>

        <b>Destination:</b>
        {end_station_name}
        <br/>

        <b>Trips:</b>
        {trip_count}
        <br/>

        <b>Average duration:</b>
        {avg_duration} min

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
# MAIN DASHBOARD
# ============================================================

def trip_flow_dashboard(connection):

    st.subheader(
        "Trip Flow Analysis"
    )

    # ========================================================
    # LOAD DATA
    # ========================================================

    trips = load_trip_flows(
        connection
    )

    if trips.empty:

        st.warning(
            "No trip data available."
        )

        return

    stations = create_station_data(
        trips
    )

    # ========================================================
    # FILTERS
    # ========================================================

    st.markdown(
        "### Analysis Controls"
    )

    col1, col2, col3 = st.columns(3)

    # --------------------------------------------------------
    # VIEW MODE
    # --------------------------------------------------------

    with col1:

        view_mode = st.selectbox(
            "Flow analysis",
            [
                "Top OD corridors",
                "Selected station"
            ]
        )

    # --------------------------------------------------------
    # COLOR
    # --------------------------------------------------------

    with col2:

        color_by = st.selectbox(
            "Color flows by",
            [
                "Average duration",
                "Trip volume"
            ]
        )

    # --------------------------------------------------------
    # USER TYPE
    # --------------------------------------------------------

    with col3:

        user_type = st.selectbox(
            "User type",
            [
                "All",
                "Subscriber",
                "Customer"
            ]
        )

    # ========================================================
    # DURATION FILTER
    # ========================================================

    min_duration = float(
        trips["duration_minute"].min()
    )

    max_duration = float(
        trips["duration_minute"].max()
    )

    selected_duration = st.slider(
        "Trip duration range (minutes)",

        min_value=min_duration,

        max_value=max_duration,

        value=(
            min_duration,
            max_duration
        )
    )

    # ========================================================
    # FILTER TRIPS
    # ========================================================

    filtered_trips = trips.copy()

    # User type
    if user_type != "All":

        filtered_trips = filtered_trips[
            filtered_trips["user_type"]
            == user_type
        ]

    # Duration
    filtered_trips = filtered_trips[
        (
            filtered_trips["duration_minute"]
            >= selected_duration[0]
        )
        &
        (
            filtered_trips["duration_minute"]
            <= selected_duration[1]
        )
    ]

    # ========================================================
    # AGGREGATE
    # ========================================================

    od_flows = aggregate_od_flows(
        filtered_trips
    )

    # ========================================================
    # TOP N / SELECTED STATION
    # ========================================================

    if view_mode == "Top OD corridors":

        top_n = st.selectbox(
            "Number of strongest corridors",
            [
                5,
                10,
                20,
                25,
                50,
                100
            ],
            index=3
        )

        displayed_flows = select_top_flows(
            od_flows,
            top_n
        )

        analysis_description = (
            f"Showing the {top_n} strongest "
            "origin-destination station flows."
        )

    else:

        # ----------------------------------------------------
        # STATION SELECTION
        # ----------------------------------------------------

        station_options = (
            stations[
                [
                    "station_id",
                    "station_name"
                ]
            ]
            .drop_duplicates()
            .sort_values("station_name")
        )

        station_labels = {
            row["station_id"]:
            f'{row["station_name"]} '
            f'(ID: {row["station_id"]})'
            for _, row
            in station_options.iterrows()
        }

        selected_station = st.selectbox(
            "Select station",

            station_options[
                "station_id"
            ].tolist(),

            format_func=lambda x:
                station_labels[x]
        )

        direction = st.radio(
            "Flow direction",
            [
                "All",
                "Outbound",
                "Inbound"
            ],
            horizontal=True
        )

        top_n = st.selectbox(
            "Number of strongest connections",
            [
                5,
                10,
                20,
                25,
                50
            ],
            index=1
        )

        displayed_flows = get_station_flows(
            od_flows,
            station_id=selected_station,
            direction=direction,
            top_n=top_n
        )

        selected_station_name = (
            station_labels[
                selected_station
            ]
        )

        analysis_description = (
            f"Showing the {top_n} strongest "
            f"{direction.lower()} connections "
            f"for {selected_station_name}."
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    st.info(
        analysis_description
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Trips in analysis",
            f"{len(filtered_trips):,}"
        )

    with col2:

        st.metric(
            "OD flows shown",
            f"{len(displayed_flows):,}"
        )

    with col3:

        if not displayed_flows.empty:

            total_flow_trips = (
                displayed_flows[
                    "trip_count"
                ].sum()
            )

        else:

            total_flow_trips = 0

        st.metric(
            "Trips represented",
            f"{total_flow_trips:,}"
        )

    with col4:

        if not displayed_flows.empty:

            avg_duration = (
                displayed_flows[
                    "avg_duration"
                ].mean()
            )

            st.metric(
                "Avg. duration",
                f"{avg_duration:.1f} min"
            )

        else:

            st.metric(
                "Avg. duration",
                "—"
            )

    # ========================================================
    # MAP LAYERS
    # ========================================================

    st.markdown(
        "### Map Layers"
    )

    layer1, layer2 = st.columns(2)

    with layer1:

        show_flows = st.checkbox(
            "Show flow corridors",
            value=True
        )

    with layer2:

        show_stations = st.checkbox(
            "Show stations",
            value=True
        )

    # ========================================================
    # VISUAL SETTINGS
    # ========================================================

    opacity = st.slider(
        "Flow opacity",
        min_value=40,
        max_value=220,
        value=160
    )

    # ========================================================
    # MAP
    # ========================================================

    if displayed_flows.empty:

        st.warning(
            "No flows match the selected filters."
        )

    else:

        create_arc_map(
            displayed_flows,
            stations,

            show_flows=show_flows,

            show_stations=show_stations,

            color_by=color_by,

            opacity=opacity
        )

    # ========================================================
    # LEGEND
    # ========================================================

    st.markdown(
        "### Legend"
    )

    if color_by == "Average duration":

        st.markdown(
            """
            **Flow color — average trip duration**

            🟣 Shorter average duration  
            🔴 Longer average duration

            **Flow width — trip volume**

            Thin line → fewer trips  
            Thick line → more trips

            **Stations**

            ● Station
            """
        )

    else:

        st.markdown(
            """
            **Flow color — trip volume**

            🟣 Lower trip volume  
            🔴 Higher trip volume

            **Flow width**

            Thin line → fewer trips  
            Thick line → more trips

            **Stations**

            ● Station
            """
        )