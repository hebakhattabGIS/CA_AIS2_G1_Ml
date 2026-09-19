import streamlit as st

from app import get_connection

from Visualization.trip_flow_map import (
    trip_flow_dashboard
)


st.title("Ford GoBike — Trip Flow Analysis")

connection = get_connection()

trip_flow_dashboard(connection)