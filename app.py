import streamlit as st

st.set_page_config(
    page_title="Station Location Tracker",
    page_icon="📍",
    layout="centered"
)

st.title("📍 Station Location Registration")
st.markdown("---")

# Simple form
with st.form("registration"):
    name = st.text_input("Client Name")
    station = st.selectbox("Station", ["Central", "North", "South", "West"])
    
    if st.form_submit_button("Register"):
        if name:
            st.success(f"✅ {name} registered at {station} Station!")
            st.balloons()
        else:
            st.error("Please enter a name")

st.info("Share this app link to collect locations automatically.")
