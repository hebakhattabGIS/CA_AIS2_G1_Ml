"""
All visual rendering for the Ford GoBike dashboard.

app.py owns the database connection, filters and layout.
This module owns everything that draws: the Plotly charts and the PyDeck maps.
Every function here takes an already-filtered DataFrame and just renders it.

Maps are flat 2D: no extrusion, no pitch. Density is carried by hexagon colour,
flows by straight lines with teal origin / amber destination endpoints.
"""

import plotly.express as px
import pydeck as pdk
import streamlit as st


TOP_N_FLOWS = 15  # max destination lines drawn per selected origin station

# Basemap options offered in the sidebar. "light" is easier to read against the
# teal/amber palette; "dark" makes the hexagon colours pop more.
BASEMAP_STYLES = {
	"Light": "light",
	"Dark": "dark",
}

ORIGIN_COLOR = [15, 118, 110]       # teal
DESTINATION_COLOR = [245, 158, 11]  # amber

# Line colour gradient: light teal (few trips) -> dark teal (many trips),
# same hue family as the origin dot and the hexagon layer.
LINE_COLOR_LIGHT = (178, 223, 219)
LINE_COLOR_DARK = (0, 60, 55)
LINE_WIDTH_PIXELS = "3"  # fixed width - trip count is now carried by colour, not thickness


def _trip_count_to_color(trip_counts, alpha=210):
    """
    Map a Series of trip counts to an RGBA colour per row, interpolating between
    LINE_COLOR_LIGHT (fewest trips) and LINE_COLOR_DARK (most trips) - the same
    "darker = busier" logic as the hexagon density layer.
    """
    counts = trip_counts.astype(float)
    low, high = counts.min(), counts.max()
    if high == low:
        # Only one distinct count in this selection - render everything at full intensity.
        norm = counts * 0 + 1.0
    else:
        norm = (counts - low) / (high - low)

    colors = []
    for n in norm:
        rgb = [
            int(LINE_COLOR_LIGHT[i] + (LINE_COLOR_DARK[i] - LINE_COLOR_LIGHT[i]) * n)
            for i in range(3)
        ]
        colors.append(rgb + [alpha])
    return colors


# ------------------------------------------------------------------
# AREA BOOKMARKS
# ------------------------------------------------------------------
# Each entry filters the data AND positions the camera, so you only ever see
# one region at a time instead of two distant blobs on a zoomed-out map.
#
# [FLAG] You said two areas - I've included the three the Bay Wheels system
# normally covers. Delete whichever one your data doesn't contain, or adjust
# the bounds if your stations fall outside them.
AREA_PRESETS = {
	"San Francisco": {
		"lat_min": 37.70, "lat_max": 37.84,
		"lon_min": -122.53, "lon_max": -122.35,
		"zoom": 12.5,
	},
	"East Bay": {
		"lat_min": 37.74, "lat_max": 37.90,
		"lon_min": -122.34, "lon_max": -122.15,
		"zoom": 12.0,
	},
	"San Jose": {
		"lat_min": 37.26, "lat_max": 37.42,
		"lon_min": -122.00, "lon_max": -121.82,
		"zoom": 12.5,
	},
}


def area_names():
	"""Options for the area selector in app.py."""
	return list(AREA_PRESETS.keys())


def basemap_names():
	"""Options for the basemap selector in app.py."""
	return list(BASEMAP_STYLES.keys())


def filter_to_area(data, area_name):
	"""Keep only trips whose START station falls inside the chosen area."""
	bounds = AREA_PRESETS[area_name]
	return data[
		data["start_lat"].between(bounds["lat_min"], bounds["lat_max"])
		& data["start_lon"].between(bounds["lon_min"], bounds["lon_max"])
	]


def _as_float_positions(data, lon_col, lat_col):
	"""
	Build an explicit [lon, lat] array column instead of relying on pydeck's
	list-of-column-names accessor. Also forces native float (not numpy/Decimal),
	which is what actually caused the runaway lines: PostgreSQL NUMERIC columns
	arrive as Python Decimal, which serializes badly and gets read by deck.gl
	as 0.0 for some rows - sending those points to (0, 0), way off the coast
	of Africa, which is the "line going to a far distance" you saw.
	"""
	lon = data[lon_col].astype(float)
	lat = data[lat_col].astype(float)
	return list(zip(lon, lat))


def _flat_view(latitude, longitude, zoom):
	"""A strictly top-down view. pitch=0 and bearing=0 keep the map 2D."""
	return pdk.ViewState(
		latitude=float(latitude),
		longitude=float(longitude),
		zoom=zoom,
		pitch=0,
		bearing=0,
	)

# ------------------------------------------------------------------
# MAP MODE 1: DENSITY (flat hexagons, colour = volume)
# ------------------------------------------------------------------
def render_density_map(data, area_name, basemap="Light"):
	st.subheader(f"Start station activity - {area_name}")
	st.caption(
		"Trips aggregated into hexagon bins. Colour intensity reflects trip volume - "
		"darker bins are busier."
	)

	bounds = AREA_PRESETS[area_name]

	hex_data = data[["start_lon", "start_lat"]].copy()
	hex_data["position"] = _as_float_positions(hex_data, "start_lon", "start_lat")

	hex_layer = pdk.Layer(
		"HexagonLayer",
		data=hex_data,
		get_position="position",
		radius=300,
		extruded=False,     # flat 2D - no 3D columns
		opacity=0.55,       # lets the basemap streets read through
		coverage=0.95,
		pickable=True,
		auto_highlight=True,
	)

	st.pydeck_chart(
		pdk.Deck(
			layers=[hex_layer],
			initial_view_state=_flat_view(
				data["start_lat"].mean(), data["start_lon"].mean(), bounds["zoom"]
			),
			map_style=BASEMAP_STYLES[basemap],
			tooltip={"text": "{elevationValue} trips in this area"},
		)
	)


# ------------------------------------------------------------------
# MAP MODE 2: FLOWS (straight 2D lines + coloured endpoints)
# ------------------------------------------------------------------
def render_flow_map(data, area_name, basemap="Light"):
	st.subheader(f"Trip flows - {area_name}")

	station_options = sorted(data["start_station"].dropna().unique().tolist())
	if not station_options:
		st.info("No stations in this area match the current filters.")
		return

	selected_station = st.selectbox("Origin station", station_options)

	station_trips = data[data["start_station"] == selected_station]
	flow_counts = (
		station_trips.groupby(
			["end_station", "start_lat", "start_lon", "end_lat", "end_lon"],
			as_index=False,
		)
		.size()
		.rename(columns={"size": "trip_count"})
		.nlargest(TOP_N_FLOWS, "trip_count")
	)

	if flow_counts.empty:
		st.info("No trips leave this station under the current filters.")
		return

	flow_counts["line_color"] = _trip_count_to_color(flow_counts["trip_count"])	
	flow_counts["source_position"] = _as_float_positions(flow_counts, "start_lon", "start_lat")
	flow_counts["target_position"] = _as_float_positions(flow_counts, "end_lon", "end_lat")
    #flow_counts["line_color"] = _trip_count_to_color(flow_counts["trip_count"], 210)

    # Straight lines, fixed width. Trip count is carried by colour intensity
    # (darker teal = more trips), matching the hexagon density layer's logic.
	line_layer = pdk.Layer(
		"LineLayer",
		data=flow_counts,
		get_source_position="source_position",
		get_target_position="target_position",
		get_color="line_color",
		get_width=LINE_WIDTH_PIXELS,
		width_units="pixels",
		width_min_pixels=1,
		width_max_pixels=6,
		pickable=True,
		auto_highlight=True,
	)

	# Amber dots mark destinations.
	destination_layer = pdk.Layer(
		"ScatterplotLayer",
		data=flow_counts,
		get_position="target_position",
		get_fill_color=DESTINATION_COLOR + [200],
		get_radius=60,
		radius_min_pixels=4,
		radius_max_pixels=10,
		pickable=True,
	)

	# One larger teal dot marks the origin.
	origin_row = flow_counts.head(1)
	origin_layer = pdk.Layer(
		"ScatterplotLayer",
		data=origin_row,
		get_position="source_position",
		get_fill_color=ORIGIN_COLOR + [230],
		get_radius=110,
		radius_min_pixels=7,
		radius_max_pixels=16,
	)

	st.pydeck_chart(
		pdk.Deck(
			layers=[line_layer, destination_layer, origin_layer],
			initial_view_state=_flat_view(
				origin_row["start_lat"].iloc[0],
				origin_row["start_lon"].iloc[0],
				AREA_PRESETS[area_name]["zoom"],
			),
			map_style=BASEMAP_STYLES[basemap],
			tooltip={"text": "{end_station}: {trip_count} trips"},
		)
	)

	st.caption(
		f"Top {len(flow_counts)} destinations from {selected_station}. "
		"The large teal dot is the origin, amber dots are destinations, and line "
		"thickness reflects relative trip volume."
	)

	with st.expander("See underlying numbers"):
		st.dataframe(
			flow_counts[["end_station", "trip_count"]].reset_index(drop=True),
			use_container_width=True,
		)