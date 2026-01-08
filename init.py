"""
st_geolocation: Python wrapper for the geolocation Streamlit component.

Usage:
    from st_geolocation import geolocate
    coords = geolocate()
    # coords is None if user hasn't clicked the button yet,
    # or a dict like {"lat": 12.34, "lon": 56.78} or {"error": "message"}
"""
import os
from streamlit import components

# During development, set environment variable ST_GEOCOMP_DEV=1
# and run the frontend dev server (see README). The wrapper will use the dev URL.
if os.environ.get("ST_GEOCOMP_DEV"):
    _st_geocomp = components.declare_component(
        "st_geolocation",
        url="http://localhost:3001"  # parcel dev server (see frontend/package.json)
    )
else:
    # Production / built artifact path: this expects frontend build files at:
    # st_geolocation/frontend/build
    here = os.path.dirname(__file__)
    build_dir = os.path.join(here, "frontend", "build")
    _st_geocomp = components.declare_component("st_geolocation", path=build_dir)


def geolocate(key: str = "st_geolocation"):
    """
    Render the geolocation component and return its value.

    Returns:
      - None: when the user hasn't interacted yet
      - dict {"lat": float, "lon": float} when coordinates were successfully captured
      - dict {"error": "<message>"} on failure/denial

    Example:
        coords = geolocate()
        if coords and "lat" in coords:
            lat, lon = coords["lat"], coords["lon"]
    """
    # We simply call the declared component and return its value.
    # The frontend will call Streamlit.setComponentValue(...) with the result.
    value = _st_geocomp(key=key)
    return value
