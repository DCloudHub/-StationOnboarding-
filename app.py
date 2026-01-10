# Location Information Group - ALL TOGETHER
st.markdown('<div class="location-group">', unsafe_allow_html=True)
st.markdown("#### Station Location")

# Use st.columns for horizontal layout
loc_col1, loc_col2, loc_col3 = st.columns(3)

with loc_col1:
    # Zone selection
    zone = st.selectbox(
        "Geopolitical Zone *",
        list(NIGERIAN_REGIONS.keys()),
        index=None,
        placeholder="Select station zone",
        key="zone_select"
    )

with loc_col2:
    # State selection - IMMEDIATELY appears when Zone is selected
    state_options = NIGERIAN_REGIONS[zone] if zone else []
    state = st.selectbox(
        "State *",
        state_options,
        index=None,
        placeholder="Select state" if zone else "Select zone first",
        disabled=not zone,
        key="state_select"
    )

with loc_col3:
    # LGA input - IMMEDIATELY appears when State is selected
    lga = st.text_input(
        "Local Government Area (LGA) *",
        placeholder="Enter station LGA" if state else "Select state first",
        disabled=not state,
        key="lga_input"
    )

st.markdown('</div>', unsafe_allow_html=True)
