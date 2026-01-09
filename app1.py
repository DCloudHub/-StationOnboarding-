import streamlit as st
from st_geolocation import geolocate
import pandas as pd
import datetime

st.set_page_config(page_title="Station Location — Auto capture", layout="centered")
st.title("Station Location — Auto capture example")

st.markdown(
    "This page attempts to capture coordinates automatically on load. "
    "A browser permission prompt will appear; allow to capture coordinates. "
    "If you prefer not to auto-capture, set auto=False in geolocate()."
)

# Call the component with auto=True so it triggers getCurrentPosition on mount
coords = geolocate(auto=True)

if coords is None:
    st.info("Waiting for location capture... (or click the component button)")
elif "error" in coords:
    st.error(f"Could not capture location: {coords['error']}")
else:
    lat = coords.get("lat")
    lon = coords.get("lon")
    st.success(f"Captured coordinates: {lat:.6f}, {lon:.6f}")

st.markdown("---")
with st.form("reg"):
    name = st.text_input("Client name")
    station = st.selectbox("Station", ["Central", "North", "South", "West"])
    attach = st.checkbox("Attach captured coordinates", value=True)
    submitted = st.form_submit_button("Register")

if submitted:
    if not name:
        st.error("Enter a client name.")
    else:
        row = {"Name": name, "Station": station, "Timestamp": datetime.datetime.now().isoformat(sep=' ', timespec='seconds')}
        if attach and coords and "lat" in coords:
            row["Latitude"] = coords["lat"]
            row["Longitude"] = coords["lon"]
        st.write("Would save:", row)
        st.success("Registration recorded (example).")
