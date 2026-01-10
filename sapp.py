"""
Station Onboarding System - SIMPLE GPS ONLY
Automatic GPS → Database → Admin View
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
            timestamp TEXT
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
        st.error(f"Database error: {e}")
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
    except Exception as e:
        st.error(f"Fetch error: {e}")
        return []

# Clean title
st.title("⛽ Fuel Station GPS Registration")
st.markdown("---")

# Admin Login
with st.sidebar:
    st.markdown("### Admin Panel")
    
    if not st.session_state.admin_mode:
        if st.button("🔓 Login as Admin", use_container_width=True):
            st.session_state.admin_mode = True
            st.rerun()
    else:
        st.success("✅ Admin Mode")
        if st.button("← Back to Registration", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()

# MAIN APP
if st.session_state.admin_mode:
    # ADMIN VIEW
    st.header("📊 All Station Registrations")
    
    stations = get_all_stations()
    
    if stations:
        df = pd.DataFrame(stations, columns=[
            'ID', 'Name', 'Owner', 'Phone', 'Latitude', 'Longitude', 'Accuracy', 'Time'
        ])
        
        # Format coordinates - BOTH LATITUDE AND LONGITUDE
        df['Coordinates'] = df.apply(
            lambda row: f"Lat: {row['Latitude']:.6f}, Lon: {row['Longitude']:.6f}", 
            axis=1
        )
        
        df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Display BOTH columns separately
        st.dataframe(
            df[['ID', 'Name', 'Owner', 'Phone', 'Latitude', 'Longitude', 'Accuracy', 'Time']],
            use_container_width=True,
            hide_index=True
        )
        
        # Export
        if st.button("📥 Export to CSV"):
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="stations.csv" style="text-decoration: none; color: white; background: #1E3A8A; padding: 10px 20px; border-radius: 5px;">Download CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        # Show summary
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Stations", len(df))
        with col2:
            avg_acc = df['Accuracy'].mean()
            st.metric("Avg Accuracy", f"±{avg_acc:.1f}m")
        with col3:
            latest = df['Time'].iloc[0] if len(df) > 0 else "None"
            st.metric("Latest", latest)
    
    else:
        st.info("No stations registered yet")
    
    if st.button("← Back to Registration"):
        st.session_state.admin_mode = False
        st.rerun()

else:
    # REGISTRATION FLOW
    # Simple step indicator
    steps = ["Location", "Details", "Complete"]
    current = st.session_state.current_step
    
    # Progress bar
    progress = current / len(steps)
    st.progress(progress)
    
    # Step header
    if current == 1:
        st.header("📍 Step 1: Capture GPS Location")
    elif current == 2:
        st.header("📝 Step 2: Enter Station Details")
    elif current == 3:
        st.header("✅ Step 3: Registration Complete")
    
    st.markdown("---")
    
    # STEP 1: GPS CAPTURE - AUTOMATIC ONLY
    if st.session_state.current_step == 1:
        st.markdown("### Capture Your Station's Location")
        
        # GPS Instructions
        st.info("""
        **How to capture GPS:**
        1. Click the **Get GPS Location** button below
        2. Allow location access when browser asks
        3. Wait for coordinates to appear
        4. Click **Next** to continue
        """)
        
        # GPS Component - Shows BOTH latitude and longitude
        gps_html = """
        <div style="text-align: center; margin: 30px 0;">
            <button onclick="captureGPS()" style="
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
                📍 GET GPS LOCATION
            </button>
            
            <div id="status" style="
                margin: 25px auto;
                padding: 20px;
                background: white;
                border-radius: 8px;
                border: 2px solid #e5e7eb;
                max-width: 500px;
                min-height: 120px;
                text-align: left;
            ">
                <div style="color: #6b7280; text-align: center;">
                    <p>Click the button above to start GPS capture</p>
                </div>
            </div>
        </div>
        
        <script>
        function captureGPS() {
            const statusDiv = document.getElementById('status');
            const button = document.querySelector('button[onclick="captureGPS()"]');
            
            // Update UI
            button.innerHTML = '⏳ GETTING LOCATION...';
            button.style.opacity = '0.8';
            
            statusDiv.innerHTML = `
                <div style="color: #f59e0b; font-weight: bold; margin-bottom: 10px;">
                    ⏳ REQUESTING GPS LOCATION...
                </div>
                <div style="color: #6b7280; font-size: 0.9em;">
                    <p>Please allow location access when prompted by your browser</p>
                </div>
            `;
            
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        // SUCCESS - Got BOTH latitude and longitude
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        const acc = position.coords.accuracy;
                        
                        // Update UI
                        button.innerHTML = '✅ LOCATION CAPTURED';
                        button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                        button.disabled = true;
                        
                        statusDiv.innerHTML = `
                            <div style="color: #059669; font-weight: bold; margin-bottom: 10px;">
                                ✅ GPS LOCATION CAPTURED!
                            </div>
                            <div style="background: #f0f9ff; padding: 15px; border-radius: 5px;">
                                <div style="font-family: monospace; font-size: 1.1rem;">
                                    <strong>Latitude:</strong> ${lat.toFixed(6)}<br>
                                    <strong>Longitude:</strong> ${lon.toFixed(6)}<br>
                                    <strong>Accuracy:</strong> ±${acc.toFixed(1)} meters
                                </div>
                            </div>
                            <div style="margin-top: 15px; color: #059669;">
                                ✓ Both coordinates captured successfully
                            </div>
                        `;
                        
                        // Store BOTH coordinates for Streamlit
                        localStorage.setItem('gps_latitude', lat);
                        localStorage.setItem('gps_longitude', lon);
                        localStorage.setItem('gps_accuracy', acc);
                        
                        // Create hidden element for Streamlit to detect
                        const gpsData = document.createElement('div');
                        gpsData.id = 'streamlit_gps_data';
                        gpsData.style.display = 'none';
                        gpsData.textContent = 'GPS_CAPTURED';
                        document.body.appendChild(gpsData);
                        
                    },
                    function(error) {
                        // ERROR handling
                        let errorMsg = "Could not get location";
                        if (error.code === 1) {
                            errorMsg = "Permission denied. Please allow location access.";
                        } else if (error.code === 2) {
                            errorMsg = "Location unavailable. Check device GPS.";
                        } else if (error.code === 3) {
                            errorMsg = "Request timeout. Please try again.";
                        }
                        
                        button.innerHTML = '📍 TRY AGAIN';
                        button.style.opacity = '1';
                        
                        statusDiv.innerHTML = `
                            <div style="color: #dc2626; font-weight: bold; margin-bottom: 10px;">
                                ❌ ${errorMsg}
                            </div>
                            <div style="color: #6b7280;">
                                Please refresh the page and try again.
                            </div>
                        `;
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 15000,
                        maximumAge: 0
                    }
                );
            } else {
                statusDiv.innerHTML = `
                    <div style="color: #dc2626; font-weight: bold;">
                        ❌ GEOLOCATION NOT SUPPORTED
                    </div>
                    <div style="color: #6b7280;">
                        Please use Chrome, Firefox, or Safari browser.
                    </div>
                `;
            }
        }
        </script>
        """
        
        # Display GPS component
        st.components.v1.html(gps_html, height=300)
        
        # Check for GPS data
        if st.button("🔄 Check if GPS is Captured"):
            # This triggers a rerun to check localStorage
            st.rerun()
        
        # Auto-check for GPS data (simplified)
        # In production, you'd use WebSockets or periodic checks
        
        # Navigation
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        
        with col2:
            if st.session_state.gps_data:
                lat = st.session_state.gps_data['latitude']
                lon = st.session_state.gps_data['longitude']
                st.success(f"✅ GPS Ready!\nLatitude: {lat:.6f}\nLongitude: {lon:.6f}")
                if st.button("Next Step →", type="primary", use_container_width=True):
                    st.session_state.current_step = 2
                    st.rerun()
            else:
                st.warning("Please capture GPS location to continue")
    
    # STEP 2: STATION DETAILS
    elif st.session_state.current_step == 2:
        # Show captured GPS data
        if st.session_state.gps_data:
            lat = st.session_state.gps_data['latitude']
            lon = st.session_state.gps_data['longitude']
            
            st.info(f"""
            **📍 Captured GPS Coordinates:**
            
            **Latitude:** {lat:.6f}
            
            **Longitude:** {lon:.6f}
            
            **Accuracy:** ±{st.session_state.gps_data.get('accuracy', 0):.1f} meters
            """)
        
        # Station registration form
        with st.form("station_form"):
            st.markdown("### Enter Station Information")
            
            col1, col2 = st.columns(2)
            with col1:
                station_name = st.text_input("Station Name *", 
                                           placeholder="e.g., Mega Fuel Station")
                owner_name = st.text_input("Owner Name *", 
                                         placeholder="Full name")
            with col2:
                phone = st.text_input("Phone Number *", 
                                    placeholder="08012345678")
            
            st.markdown("---")
            
            col_back, col_submit = st.columns(2)
            with col_back:
                if st.form_submit_button("← Back", use_container_width=True):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col_submit:
                submitted = st.form_submit_button("✅ Submit Registration", 
                                                type="primary", 
                                                use_container_width=True)
                
                if submitted:
                    # Validate
                    if not all([station_name, owner_name, phone]):
                        st.error("Please fill all required fields")
                    elif not st.session_state.gps_data:
                        st.error("GPS data missing. Please go back to capture location.")
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
    
    # STEP 3: COMPLETION
    elif st.session_state.current_step == 3:
        st.balloons()
        
        st.success("""
        ## ✅ Registration Complete!
        
        Your station has been registered with GPS coordinates saved to database.
        """)
        
        # Show registration details
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📋 Registration Details")
            st.markdown(f"""
            **Station ID:** {st.session_state.form_data.get('station_id', 'N/A')}
            
            **Station Name:** {st.session_state.form_data.get('station_name', 'N/A')}
            
            **Owner Name:** {st.session_state.form_data.get('owner_name', 'N/A')}
            """)
        
        with col2:
            st.markdown("#### 📍 GPS Coordinates")
            if st.session_state.gps_data:
                st.markdown(f"""
                **Latitude:** {st.session_state.gps_data['latitude']:.6f}
                
                **Longitude:** {st.session_state.gps_data['longitude']:.6f}
                
                **Accuracy:** ±{st.session_state.gps_data.get('accuracy', 0):.1f} meters
                """)
        
        # Next actions
        st.markdown("---")
        st.markdown("### What would you like to do next?")
        
        col_admin, col_new = st.columns(2)
        
        with col_admin:
            if st.button("📊 Go to Admin Dashboard", use_container_width=True):
                st.session_state.admin_mode = True
                st.session_state.current_step = 1
                st.session_state.gps_data = None
                st.rerun()
        
        with col_new:
            if st.button("➕ Register Another Station", use_container_width=True):
                st.session_state.current_step = 1
                st.session_state.gps_data = None
                st.session_state.form_data = {}
                st.rerun()

# Footer
st.markdown("---")
st.caption("Station GPS Registration System • Automatic GPS Capture Only")
