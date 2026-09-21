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

	for column, values, prefix in (
		("u.user_type", user_types, "user_type"),
		("u.age_group", age_groups, "age_group"),
		("u.gender", genders, "gender"),
	):
		if not values:
			# Empty selection means "exclude everything", not "no filter".
			return "WHERE 1 = 0", {}
		names = []
		for index, value in enumerate(values):
			name = f"{prefix}_{index}"
			names.append(f":{name}")
			params[name] = value
		clauses.append(f"{column}::text IN ({', '.join(names)})")

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
			u.gender::text    AS gender,
			u.age_group::text AS age_group,
			u.user_type::text AS user_type
		FROM fact_trips AS t
		JOIN dim_station AS ss ON ss.station_id = t.start_station_id
		JOIN dim_station AS es ON es.station_id = t.end_station_id
		JOIN dim_user    AS u  ON u.user_id     = t.user_id
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
		data = load_dashboard_data(
			selected_user_types, selected_age_groups, selected_genders
		)
	except Exception as error:
		st.error("Unable to load dashboard data. Check the PostgreSQL connection settings.")
		st.exception(error)
		return

	# KPIs sit above the tabs so they stay visible in both views.
	render_kpis(data)
	st.divider()

	if data.empty:
		st.info("No trips match the selected filters.")
		return

	charts_tab, map_tab = st.tabs(["Charts", "Map"])

	with charts_tab:
		heba_charts.render_charts(data)

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