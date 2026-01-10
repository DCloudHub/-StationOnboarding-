"""
Station Onboarding System - AUTO-SAVE GPS
GPS automatically saves → Admin can view immediately
"""

import streamlit as st
import pandas as pd
import sqlite3
import uuid
from datetime import datetime
import base64

# Page config
st.set_page_config(
    page_title="Station GPS Registration",
    page_icon="⛽",
    layout="wide"
)

# Initialize session state
if 'gps_data' not in st.session_state:
    st.session_state.gps_data = None
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'station_saved' not in st.session_state:
    st.session_state.station_saved = False
if 'station_id' not in st.session_state:
    st.session_state.station_id = None
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
            status TEXT DEFAULT 'pending',
            timestamp TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

def save_station_to_db(station_name, owner_name, phone, gps_data):
    """Save station with GPS to database"""
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
        st.error(f"Database error: {e}")
        return None

def get_all_stations():
    """Get all stations for admin view"""
    try:
        c = conn.cursor()
        c.execute('''
            SELECT station_id, station_name, owner_name, phone, 
                   latitude, longitude, accuracy, timestamp, status
            FROM stations 
            ORDER BY timestamp DESC
        ''')
        return c.fetchall()
    except Exception as e:
        st.error(f"Fetch error: {e}")
        return []

# Clean title
st.title("⛽ Fuel Station GPS Registration")
st.markdown("---")

# Admin Panel - Always accessible
with st.sidebar:
    st.markdown("### 📊 Admin Panel")
    
    if st.button("View All Submissions", use_container_width=True):
        st.session_state.admin_mode = True
        st.rerun()
    
    if st.session_state.admin_mode:
        st.success("✅ Admin View Active")
        if st.button("← Back to Registration", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()

# MAIN APP
if st.session_state.admin_mode:
    # ADMIN VIEW - Shows all submissions immediately
    st.header("📊 All Station Submissions")
    
    # Refresh button
    if st.button("🔄 Refresh Data", key="refresh_admin"):
        st.rerun()
    
    stations = get_all_stations()
    
    if stations:
        df = pd.DataFrame(stations, columns=[
            'ID', 'Name', 'Owner', 'Phone', 'Latitude', 'Longitude', 'Accuracy', 'Time', 'Status'
        ])
        
        # Format
        df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%Y-%m-%d %H:%M')
        df['Coordinates'] = df.apply(
            lambda row: f"{row['Latitude']:.6f}, {row['Longitude']:.6f}", 
            axis=1
        )
        
        # Show all data
        st.dataframe(
            df[['ID', 'Name', 'Owner', 'Phone', 'Coordinates', 'Accuracy', 'Time', 'Status']],
            use_container_width=True,
            hide_index=True
        )
        
        # Statistics
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Submissions", len(df))
        with col2:
            pending = len(df[df['Status'] == 'pending'])
            st.metric("Pending", pending)
        with col3:
            latest = df['Time'].iloc[0] if len(df) > 0 else "None"
            st.metric("Latest", latest)
        
        # Export
        if st.button("📥 Export to CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="stations.csv">Download CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    else:
        st.info("No submissions yet. Stations will appear here once GPS is captured.")
    
    if st.button("← Back to Registration"):
        st.session_state.admin_mode = False
        st.rerun()

else:
    # REGISTRATION FLOW
    if st.session_state.station_saved:
        # SHOW COMPLETION SCREEN
        st.balloons()
        st.success(f"""
        ## ✅ Station Submitted Successfully!
        
        **Station ID:** {st.session_state.station_id}
        
        Your station has been saved to the database.
        GPS coordinates are now available in the admin view.
        """)
        
        # Show in admin button
        if st.button("📊 View in Admin Dashboard", type="primary", use_container_width=True):
            st.session_state.admin_mode = True
            st.session_state.station_saved = False
            st.session_state.station_id = None
            st.rerun()
        
        # Register another
        if st.button("➕ Register Another Station", use_container_width=True):
            st.session_state.station_saved = False
            st.session_state.station_id = None
            st.session_state.gps_data = None
            st.session_state.current_step = 1
            st.rerun()
    
    else:
        # REGISTRATION FORM
        st.header("📍 Register New Station")
        
        # Direct GPS capture that saves immediately
        st.markdown("""
        <div style="background: #f0f9ff; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: #1e40af; margin-top: 0;">📱 Step 1: Capture GPS Location</h3>
            <p><strong>Instructions:</strong></p>
            <ol>
                <li>Click the GPS button below</li>
                <li>Allow location access</li>
                <li>Coordinates will be captured automatically</li>
                <li>Then fill station details</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # GPS Component with AUTO-SAVE
        gps_html = """
        <div style="text-align: center; margin: 20px 0;">
            <button onclick="captureAndSaveGPS()" style="
                background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%);
                color: white;
                border: none;
                padding: 20px 40px;
                border-radius: 10px;
                font-size: 1.2rem;
                font-weight: bold;
                cursor: pointer;
                width: 100%;
                max-width: 500px;
                margin: 0 auto;
                display: block;
            ">
                📍 CAPTURE GPS LOCATION
            </button>
            
            <div id="gps-status" style="
                margin: 20px auto;
                padding: 20px;
                background: white;
                border-radius: 8px;
                border: 2px solid #e5e7eb;
                max-width: 500px;
                min-height: 100px;
            ">
                <div style="color: #6b7280; text-align: center;">
                    Click button to capture station location
                </div>
            </div>
            
            <div id="save-status" style="display: none; margin-top: 20px;">
                <!-- Save status will appear here -->
            </div>
        </div>
        
        <script>
        function captureAndSaveGPS() {
            const gpsStatus = document.getElementById('gps-status');
            const button = document.querySelector('button[onclick="captureAndSaveGPS()"]');
            const saveStatus = document.getElementById('save-status');
            
            button.innerHTML = '⏳ GETTING LOCATION...';
            button.disabled = true;
            
            gpsStatus.innerHTML = `
                <div style="color: #f59e0b; font-weight: bold;">
                    ⏳ REQUESTING LOCATION...
                </div>
                <p style="color: #6b7280;">Please allow location access</p>
            `;
            
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        const acc = position.coords.accuracy;
                        
                        // Show captured coordinates
                        gpsStatus.innerHTML = `
                            <div style="color: #059669; font-weight: bold;">
                                ✅ GPS CAPTURED!
                            </div>
                            <div style="background: #f0f9ff; padding: 15px; border-radius: 5px; margin-top: 10px;">
                                <div style="font-family: monospace;">
                                    <strong>Latitude:</strong> ${lat.toFixed(6)}<br>
                                    <strong>Longitude:</strong> ${lon.toFixed(6)}<br>
                                    <strong>Accuracy:</strong> ±${acc.toFixed(1)}m
                                </div>
                            </div>
                            <div style="color: #059669; margin-top: 10px;">
                                ✓ Ready for station details
                            </div>
                        `;
                        
                        button.innerHTML = '✅ LOCATION CAPTURED';
                        button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                        
                        // Store coordinates for the form
                        localStorage.setItem('captured_latitude', lat);
                        localStorage.setItem('captured_longitude', lon);
                        localStorage.setItem('captured_accuracy', acc);
                        
                        // Show form ready message
                        saveStatus.style.display = 'block';
                        saveStatus.innerHTML = `
                            <div style="background: #d1fae5; padding: 15px; border-radius: 8px; text-align: center;">
                                <p style="color: #065f46; font-weight: bold; margin: 0;">
                                    ✅ GPS coordinates saved! Fill the form below.
                                </p>
                            </div>
                        `;
                        
                        // Signal to Streamlit that GPS is ready
                        const event = new Event('gpsReadyForForm');
                        document.dispatchEvent(event);
                        
                    },
                    function(error) {
                        let errorMsg = "Failed to get location";
                        if (error.code === 1) errorMsg = "Permission denied";
                        if (error.code === 2) errorMsg = "Location unavailable";
                        if (error.code === 3) errorMsg = "Request timeout";
                        
                        gpsStatus.innerHTML = `
                            <div style="color: #dc2626; font-weight: bold;">
                                ❌ ${errorMsg}
                            </div>
                            <p style="color: #6b7280;">Please try again</p>
                        `;
                        
                        button.innerHTML = '📍 TRY AGAIN';
                        button.disabled = false;
                    },
                    { enableHighAccuracy: true, timeout: 15000 }
                );
            } else {
                gpsStatus.innerHTML = '<div style="color: #dc2626;">GPS not supported</div>';
                button.disabled = false;
            }
        }
        
        // Check if we already have GPS
        if (localStorage.getItem('captured_latitude')) {
            const button = document.querySelector('button[onclick="captureAndSaveGPS()"]');
            const gpsStatus = document.getElementById('gps-status');
            const saveStatus = document.getElementById('save-status');
            
            const lat = localStorage.getItem('captured_latitude');
            const lon = localStorage.getItem('captured_longitude');
            
            button.innerHTML = '✅ LOCATION ALREADY CAPTURED';
            button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
            button.disabled = true;
            
            gpsStatus.innerHTML = `
                <div style="color: #059669; font-weight: bold;">
                    ✅ GPS ALREADY CAPTURED
                </div>
                <div style="background: #f0f9ff; padding: 15px; border-radius: 5px; margin-top: 10px;">
                    <div style="font-family: monospace;">
                        <strong>Latitude:</strong> ${parseFloat(lat).toFixed(6)}<br>
                        <strong>Longitude:</strong> ${parseFloat(lon).toFixed(6)}
                    </div>
                </div>
            `;
            
            saveStatus.style.display = 'block';
            saveStatus.innerHTML = `
                <div style="background: #d1fae5; padding: 15px; border-radius: 8px; text-align: center; margin-top: 20px;">
                    <p style="color: #065f46; font-weight: bold; margin: 0;">
                        ✅ GPS coordinates ready! Fill the form below.
                    </p>
                </div>
            `;
        }
        </script>
        """
        
        # Display GPS component
        st.components.v1.html(gps_html, height=300)
        
        # Station Details Form
        st.markdown("---")
        st.markdown("### 📝 Step 2: Enter Station Details")
        
        with st.form("station_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                station_name = st.text_input("Station Name *", 
                                           placeholder="e.g., Mega Fuel Station")
                owner_name = st.text_input("Owner Name *", 
                                         placeholder="Full name")
            with col2:
                phone = st.text_input("Phone Number *", 
                                    placeholder="08012345678")
            
            # Submit button
            submitted = st.form_submit_button("✅ SUBMIT STATION TO DATABASE", 
                                            type="primary", 
                                            use_container_width=True)
            
            if submitted:
                # Check if GPS was captured
                if st.session_state.gps_data:
                    # Save to database
                    station_id = save_station_to_db(
                        station_name,
                        owner_name,
                        phone,
                        st.session_state.gps_data
                    )
                    
                    if station_id:
                        st.session_state.station_saved = True
                        st.session_state.station_id = station_id
                        
                        # Clear localStorage
                        st.markdown("""
                        <script>
                        localStorage.removeItem('captured_latitude');
                        localStorage.removeItem('captured_longitude');
                        localStorage.removeItem('captured_accuracy');
                        </script>
                        """, unsafe_allow_html=True)
                        
                        st.rerun()
                    else:
                        st.error("Failed to save to database")
                else:
                    st.error("Please capture GPS location first!")
        
        # Manual GPS set for testing
        with st.expander("🛠️ Developer: Set Test GPS"):
            col_test1, col_test2, col_test3 = st.columns(3)
            with col_test1:
                if st.button("Set Lagos GPS"):
                    st.session_state.gps_data = {
                        'latitude': 6.524379,
                        'longitude': 3.379206,
                        'accuracy': 25.5
                    }
                    st.success("Test GPS set!")
                    st.rerun()
            with col_test2:
                if st.button("Set Abuja GPS"):
                    st.session_state.gps_data = {
                        'latitude': 9.076478,
                        'longitude': 7.398574,
                        'accuracy': 30.2
                    }
                    st.success("Test GPS set!")
                    st.rerun()
            with col_test3:
                if st.button("Clear GPS"):
                    st.session_state.gps_data = None
                    st.success("GPS cleared!")
                    st.rerun()

# Footer
st.markdown("---")
st.caption("Station GPS Registration • Auto-save to database • Admin view accessible anytime")
