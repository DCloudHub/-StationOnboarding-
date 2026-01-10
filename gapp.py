"""
Station Onboarding System - CLEAN VERSION
GPS → Database → Admin View (No Step HTML Display)
"""

import streamlit as st
import pandas as pd
import sqlite3
import uuid
from datetime import datetime
import base64

# Page config
st.set_page_config(
    page_title="Station Onboarding",
    page_icon="⛽",
    layout="wide"
)

# Initialize session state
if 'gps_data' not in st.session_state:
    st.session_state.gps_data = None
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}
if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False

# Database
def init_db():
    conn = sqlite3.connect('stations_gps.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT UNIQUE,
            station_name TEXT,
            owner_name TEXT,
            phone TEXT,
            latitude REAL,
            longitude REAL,
            accuracy REAL,
            timestamp TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

def save_station(station_name, owner_name, phone, gps_data):
    try:
        c = conn.cursor()
        station_id = f"STN-{uuid.uuid4().hex[:6].upper()}"
        
        c.execute('''
            INSERT INTO stations 
            (station_id, station_name, owner_name, phone, latitude, longitude, accuracy, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            station_id,
            station_name,
            owner_name,
            phone,
            gps_data['latitude'],
            gps_data['longitude'],
            gps_data.get('accuracy', 0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        return station_id
    except Exception as e:
        return None

def get_all_stations():
    try:
        c = conn.cursor()
        c.execute('''
            SELECT station_id, station_name, owner_name, phone, 
                   latitude, longitude, accuracy, timestamp
            FROM stations 
            ORDER BY timestamp DESC
        ''')
        return c.fetchall()
    except:
        return []

# SIMPLE TITLE - NO COMPLEX HTML
st.title("⛽ Station Registration System")
st.write("Register your fuel station with GPS location")

# Admin Login in Sidebar
with st.sidebar:
    st.markdown("### Admin Access")
    
    if not st.session_state.admin_mode:
        if st.button("Login as Admin", use_container_width=True):
            st.session_state.admin_mode = True
            st.rerun()
    else:
        st.success("Admin Mode Active")
        if st.button("Back to Registration", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()

# MAIN CONTENT
if st.session_state.admin_mode:
    # ADMIN VIEW
    st.header("📊 Station Registrations")
    
    stations = get_all_stations()
    
    if stations:
        df = pd.DataFrame(stations, columns=[
            'ID', 'Name', 'Owner', 'Phone', 'Latitude', 'Longitude', 'Accuracy', 'Time'
        ])
        
        # Format coordinates
        df['Coordinates'] = df.apply(
            lambda row: f"{row['Latitude']:.6f}, {row['Longitude']:.6f}", 
            axis=1
        )
        
        # Format time
        df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Show table
        st.dataframe(
            df[['ID', 'Name', 'Owner', 'Phone', 'Coordinates', 'Accuracy', 'Time']],
            use_container_width=True,
            hide_index=True
        )
        
        # Export
        if st.button("Export to CSV"):
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="stations.csv">Download CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    else:
        st.info("No stations registered yet")
    
    if st.button("← Back to Main"):
        st.session_state.admin_mode = False
        st.rerun()

else:
    # SIMPLE STEP INDICATOR - Using Streamlit Native Components
    steps = ["Location", "Details", "Complete"]
    current = st.session_state.current_step
    
    # Create a simple progress indicator
    progress = current / len(steps)
    st.progress(progress)
    
    # Show current step as header
    if current == 1:
        st.header("Step 1: Capture Location")
    elif current == 2:
        st.header("Step 2: Station Details")
    elif current == 3:
        st.header("Step 3: Registration Complete")
    
    st.markdown("---")
    
    # STEP 1: GPS CAPTURE
    if st.session_state.current_step == 1:
        st.markdown("### Capture Station GPS Coordinates")
        
        # Test mode
        with st.expander("Test Mode (Add Sample Data)"):
            if st.button("Add Sample GPS Coordinates"):
                st.session_state.gps_data = {
                    'latitude': 6.524379,
                    'longitude': 3.379206,
                    'accuracy': 25.5,
                    'source': 'test'
                }
                st.success("Test coordinates added!")
                st.rerun()
        
        # GPS Instructions
        st.info("Click the button below to capture GPS coordinates. Allow location access when prompted.")
        
        # GPS Button
        gps_html = """
        <div style="text-align: center; margin: 30px 0;">
            <button onclick="getGPS()" style="
                background: #1E3A8A;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 1.1rem;
                font-weight: bold;
                cursor: pointer;
            ">
                📍 Get GPS Location
            </button>
            
            <div id="status" style="margin-top: 20px; padding: 15px; min-height: 60px;">
                Click button to start
            </div>
        </div>
        
        <script>
        function getGPS() {
            const status = document.getElementById('status');
            status.innerHTML = '<p style="color: orange;">Requesting location... Please allow access</p>';
            
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(pos) {
                        status.innerHTML = 
                            '<p style="color: green; font-weight: bold;">✅ Location captured!</p>' +
                            '<p>Latitude: ' + pos.coords.latitude.toFixed(6) + '</p>' +
                            '<p>Longitude: ' + pos.coords.longitude.toFixed(6) + '</p>';
                        
                        // Store for Streamlit
                        localStorage.setItem('gps_lat', pos.coords.latitude);
                        localStorage.setItem('gps_lon', pos.coords.longitude);
                    },
                    function(err) {
                        status.innerHTML = '<p style="color: red;">Failed to get location. Please try again.</p>';
                    }
                );
            } else {
                status.innerHTML = '<p style="color: red;">GPS not supported</p>';
            }
        }
        </script>
        """
        
        st.components.v1.html(gps_html, height=200)
        
        # Manual entry
        with st.expander("Manual Entry"):
            col1, col2 = st.columns(2)
            with col1:
                lat = st.text_input("Latitude", key="man_lat")
            with col2:
                lon = st.text_input("Longitude", key="man_lon")
            
            if st.button("Use Manual Entry") and lat and lon:
                try:
                    st.session_state.gps_data = {
                        'latitude': float(lat),
                        'longitude': float(lon),
                        'accuracy': 50.0,
                        'source': 'manual'
                    }
                    st.success("Coordinates set!")
                    st.rerun()
                except:
                    st.error("Invalid coordinates")
        
        # Navigation
        col1, col2 = st.columns(2)
        with col2:
            if st.session_state.gps_data:
                st.success(f"GPS Ready: {st.session_state.gps_data['latitude']:.6f}, {st.session_state.gps_data['longitude']:.6f}")
                if st.button("Next →", type="primary", use_container_width=True):
                    st.session_state.current_step = 2
                    st.rerun()
            else:
                st.warning("Capture GPS to continue")
    
    # STEP 2: STATION DETAILS
    elif st.session_state.current_step == 2:
        # Show current GPS
        if st.session_state.gps_data:
            st.info(f"📍 Coordinates: {st.session_state.gps_data['latitude']:.6f}, {st.session_state.gps_data['longitude']:.6f}")
        
        # Station form
        with st.form("station_form"):
            col1, col2 = st.columns(2)
            with col1:
                station_name = st.text_input("Station Name *")
                owner_name = st.text_input("Owner Name *")
            with col2:
                phone = st.text_input("Phone Number *")
            
            address = st.text_area("Address")
            
            col_back, col_submit = st.columns(2)
            with col_back:
                if st.form_submit_button("← Back", use_container_width=True):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col_submit:
                if st.form_submit_button("Submit Registration", type="primary", use_container_width=True):
                    if not all([station_name, owner_name, phone]):
                        st.error("Please fill all required fields")
                    elif not st.session_state.gps_data:
                        st.error("GPS data missing")
                    else:
                        # Save to database
                        station_id = save_station(
                            station_name,
                            owner_name,
                            phone,
                            st.session_state.gps_data
                        )
                        
                        if station_id:
                            st.session_state.form_data = {
                                'station_id': station_id,
                                'station_name': station_name,
                                'owner_name': owner_name
                            }
                            st.session_state.current_step = 3
                            st.rerun()
    
    # STEP 3: COMPLETE
    elif st.session_state.current_step == 3:
        st.success("✅ Registration Complete!")
        
        st.markdown(f"""
        **Station ID:** {st.session_state.form_data.get('station_id')}
        
        **Station Name:** {st.session_state.form_data.get('station_name')}
        
        **Owner:** {st.session_state.form_data.get('owner_name')}
        
        **GPS Coordinates:** {st.session_state.gps_data['latitude']:.6f}, {st.session_state.gps_data['longitude']:.6f}
        """)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("View in Admin", use_container_width=True):
                st.session_state.admin_mode = True
                st.session_state.current_step = 1
                st.session_state.gps_data = None
                st.rerun()
        
        with col2:
            if st.button("Register Another", use_container_width=True):
                st.session_state.current_step = 1
                st.session_state.gps_data = None
                st.session_state.form_data = {}
                st.rerun()
        
        with col3:
            st.info("Saved to database")

# Simple footer
st.markdown("---")
st.caption("Station Registration System")
