import pandas as pd
import plotly.express as px
import streamlit as st
import heba_charts

st.set_page_config(page_title="Ford GoBike Analytics", page_icon=":bike:", layout="wide")


@st.cache_resource
def get_connection():
	return st.connection("postgresql", type="sql")


@st.cache_data(ttl=600)
def load_filter_options():
	connection = get_connection()
	user_types = connection.query(
		"SELECT DISTINCT user_type::text AS value FROM dim_user ORDER BY value",
		ttl=600,
	)["value"].tolist()
	age_groups = connection.query(
		"SELECT DISTINCT age_group::text AS value FROM dim_user ORDER BY value",
		ttl=600,
	)["value"].tolist()
	genders = connection.query(
		"SELECT DISTINCT gender::text AS value FROM dim_user ORDER BY value",
		ttl=600,
	)["value"].tolist()
	return user_types, age_groups, genders


def build_filter_clause(user_types, age_groups, genders):
	clauses = []
	params = {}

	if user_types:
		names = []
		for index, value in enumerate(user_types):
			name = f"user_type_{index}"
			names.append(f":{name}")
			params[name] = value
		clauses.append(f"u.user_type::text IN ({', '.join(names)})")

	if age_groups:
		names = []
		for index, value in enumerate(age_groups):
			name = f"age_group_{index}"
			names.append(f":{name}")
			params[name] = value
		clauses.append(f"u.age_group::text IN ({', '.join(names)})")

	if genders:
		names = []
		for index, value in enumerate(genders):
			name = f"gender_{index}"
			names.append(f":{name}")
			params[name] = value
		clauses.append(f"u.gender::text IN ({', '.join(names)})")
	where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
	return where, params


@st.cache_data(ttl=300)
def load_dashboard_data(user_types=(), age_groups=(), genders=()):
	where, params = build_filter_clause(user_types, age_groups, genders)
	query = f"""
		SELECT
			t.trip_id,
			t.duration_minute,
			t.bike_id,
			ss.station_name   AS start_station,
			ss.latitude::float8  AS start_lat,
			ss.longitude::float8 AS start_lon,
			es.station_name   AS end_station,
			es.latitude::float8  AS end_lat,
			es.longitude::float8 AS end_lon,
			u.gender::text AS gender,
			u.age_group::text AS age_group,
			u.user_type::text AS user_type
		FROM fact_trips AS t
		JOIN dim_station AS ss ON ss.station_id = t.start_station_id
		JOIN dim_station AS es ON es.station_id = t.end_station_id
		JOIN dim_user AS u ON u.user_id = t.user_id
		{where}
	"""
	return get_connection().query(query, params=params, ttl=300)


def render_sidebar(user_types, age_groups, genders):
	with st.sidebar:
		st.header("Filters")
		selected_user_types = st.multiselect("User type", user_types, default=user_types)
		selected_age_groups = st.multiselect("Age group", age_groups, default=age_groups)
		selected_genders = st.multiselect("Gender", genders, default=genders)
		
		st.divider()
		st.header("Map")
		selected_area = st.radio(
			"Area",
			heba_charts.area_names(),
			help="The map shows one area at a time so distant regions don't shrink into blobs.",
		)
		map_mode = st.radio(
			"Mode",
			["Station density", "Trip flows"],
			help="Density shows overall volume. Flows show routes from one station at a time.",
		)
		basemap = st.radio(
			"Basemap",
			heba_charts.basemap_names(),
			horizontal=True,
			help="Light is easier to read; dark makes the hexagon colours stand out more.",
		)

	return (
		tuple(selected_user_types),
		tuple(selected_age_groups),
		tuple(selected_genders),
		selected_area,
		map_mode,
		basemap,
	)


def render_kpis(data):
	total_trips = len(data)
	average_duration = data["duration_minute"].mean() if total_trips else 0
	distinct_bikes = data["bike_id"].nunique() if total_trips else 0
	first, second, third = st.columns(3)
	first.metric("Total trips", f"{total_trips:,}")
	second.metric("Average duration", f"{average_duration:.1f} min")
	third.metric("Distinct bikes", f"{distinct_bikes:,}")


def render_charts(data):
	if data.empty:
		st.info("No trips match the selected filters.")
		return

	top_stations = (
		data.groupby("start_station", as_index=False)
		.size()
		.rename(columns={"size": "trip_count"})
		.nlargest(10, "trip_count")
		.sort_values("trip_count")
	)
	station_chart = px.bar(
		top_stations,
		x="trip_count",
		y="start_station",
		orientation="h",
		title="Top 10 start stations",
		labels={"trip_count": "Trips", "start_station": ""},
		color="trip_count",
		color_continuous_scale="Teal",
	)
	station_chart.update_layout(coloraxis_showscale=False, height=430)

	demographic_data = (
		data.groupby(["age_group", "gender"], as_index=False)
		.size()
		.rename(columns={"size": "trip_count"})
	)
	demographic_chart = px.bar(
		demographic_data,
		x="age_group",
		y="trip_count",
		color="gender",
		barmode="group",
		title="Trips by gender and age group",
		labels={"trip_count": "Trips", "age_group": "Age group", "gender": "Gender"},
		color_discrete_sequence=["#0f766e", "#f59e0b"],
	)
	demographic_chart.update_layout(height=430)

	left, right = st.columns(2)
	left.plotly_chart(station_chart, use_container_width=True)
	right.plotly_chart(demographic_chart, use_container_width=True)

	#map_data = (
	#	data.groupby(["start_station", "latitude", "longitude"], as_index=False)
	#	.size()
	#	.rename(columns={"size": "trip_count"})
	#)
	#st.subheader("Start station activity")
	#st.map(map_data, latitude="latitude", longitude="longitude", size="trip_count", zoom=11)


def main():
	st.title("Ford GoBike Analytics")
	st.caption("Trip activity across the selected rider segments")
	try:
		user_types, age_groups, genders = load_filter_options()
		(
			selected_user_types,
			selected_age_groups,
			selected_genders,
			selected_area,
			map_mode,
			basemap,
		) = render_sidebar(user_types, age_groups, genders)
		data = load_dashboard_data(selected_user_types, selected_age_groups, selected_genders)
	except Exception as error:
		st.error("Unable to load dashboard data. Check the PostgreSQL connection settings.")
		st.exception(error)
		return

	render_kpis(data)
	st.divider()

	if data.empty:
		st.info("No trips match the selected filters.")
		return

	charts_tab, map_tab = st.tabs(["Charts", "Map"])

	with charts_tab:
		render_charts(data)

	with map_tab:
		# Maps are scoped to one bookmarked area at a time.
		area_data = heba_charts.filter_to_area(data, selected_area)
		if area_data.empty:
			st.info(f"No trips in {selected_area} match the selected filters.")
		elif map_mode == "Station density":
			heba_charts.render_density_map(area_data, selected_area, basemap)
		else:
			heba_charts.render_flow_map(area_data, selected_area, basemap)


if __name__ == "__main__":
	main()
