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
import json
from streamlit.components.v1 import html

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

# JavaScript to pass GPS data to Streamlit
def gps_capture_component():
    """Component that captures GPS and sends to Streamlit"""
    html_code = '''
    <div style="text-align: center; margin: 20px 0;">
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
        
        <div id="streamlit-status" style="display: none;"></div>
    </div>
    
    <script>
    function captureGPS() {
        const gpsStatus = document.getElementById('gps-status');
        const button = document.querySelector('button[onclick="captureGPS()"]');
        
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
                    
                    // Send data to Streamlit
                    const data = {
                        latitude: lat,
                        longitude: lon,
                        accuracy: acc
                    };
                    
                    // Store in sessionStorage for persistence
                    sessionStorage.setItem('gps_coordinates', JSON.stringify(data));
                    
                    // Send to Streamlit
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        value: JSON.stringify(data)
                    }, '*');
                    
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
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
            );
        } else {
            gpsStatus.innerHTML = '<div style="color: #dc2626;">GPS not supported</div>';
            button.disabled = false;
        }
    }
    
    // Check if we already have GPS from previous session
    const savedGPS = sessionStorage.getItem('gps_coordinates');
    if (savedGPS) {
        const data = JSON.parse(savedGPS);
        const gpsStatus = document.getElementById('gps-status');
        const button = document.querySelector('button[onclick="captureGPS()"]');
        
        gpsStatus.innerHTML = `
            <div style="color: #059669; font-weight: bold;">
                ✅ GPS ALREADY CAPTURED
            </div>
            <div style="background: #f0f9ff; padding: 15px; border-radius: 5px; margin-top: 10px;">
                <div style="font-family: monospace;">
                    <strong>Latitude:</strong> ${data.latitude.toFixed(6)}<br>
                    <strong>Longitude:</strong> ${data.longitude.toFixed(6)}<br>
                    <strong>Accuracy:</strong> ±${data.accuracy.toFixed(1)}m
                </div>
            </div>
        `;
        
        button.innerHTML = '✅ LOCATION CAPTURED';
        button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
        
        // Resend to Streamlit to update session state
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: JSON.stringify(data)
        }, '*');
    }
    </script>
    '''
    
    return html_code

# Main app
st.title("⛽ Fuel Station GPS Registration")
st.markdown("---")

# Admin Panel
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

if st.session_state.admin_mode:
    # ADMIN VIEW
    st.header("📊 All Station Submissions")
    
    if st.button("🔄 Refresh Data", key="refresh_admin"):
        st.rerun()
    
    stations = get_all_stations()
    
    if stations:
        df = pd.DataFrame(stations, columns=[
            'ID', 'Name', 'Owner', 'Phone', 'Latitude', 'Longitude', 'Accuracy', 'Time', 'Status'
        ])
        
        df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%Y-%m-%d %H:%M')
        df['Coordinates'] = df.apply(
            lambda row: f"{row['Latitude']:.6f}, {row['Longitude']:.6f}", 
            axis=1
        )
        
        st.dataframe(
            df[['ID', 'Name', 'Owner', 'Phone', 'Coordinates', 'Accuracy', 'Time', 'Status']],
            use_container_width=True,
            hide_index=True
        )
        
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
        
        if st.button("📥 Export to CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="stations.csv">Download CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    else:
        st.info("No submissions yet.")
    
    if st.button("← Back to Registration"):
        st.session_state.admin_mode = False
        st.rerun()

else:
    # REGISTRATION FLOW
    if st.session_state.station_saved:
        # COMPLETION SCREEN
        st.balloons()
        st.success(f"""
        ## ✅ Station Submitted Successfully!
        
        **Station ID:** {st.session_state.station_id}
        
        Your station has been saved to the database.
        GPS coordinates are now available in the admin view.
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 View in Admin Dashboard", type="primary", use_container_width=True):
                st.session_state.admin_mode = True
                st.session_state.station_saved = False
                st.session_state.station_id = None
                st.rerun()
        with col2:
            if st.button("➕ Register Another Station", use_container_width=True):
                st.session_state.station_saved = False
                st.session_state.station_id = None
                st.session_state.gps_data = None
                # Clear browser storage
                clear_js = """
                <script>
                sessionStorage.removeItem('gps_coordinates');
                </script>
                """
                st.components.v1.html(clear_js, height=0)
                st.rerun()
    
    else:
        # REGISTRATION FORM
        st.header("📍 Register New Station")
        
        # GPS Capture Component
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
        
        # Display GPS component
        gps_html = gps_capture_component()
        
        # Create a container for GPS component
        gps_container = st.container()
        with gps_container:
            gps_result = html(gps_html, height=300)
            
            # Listen for GPS data from JavaScript
            if st.experimental_get_query_params().get('gps_data'):
                try:
                    gps_data_json = st.experimental_get_query_params()['gps_data'][0]
                    st.session_state.gps_data = json.loads(gps_data_json)
                    st.success("GPS coordinates captured!")
                except:
                    pass
        
        # Check if we have GPS data via message passing
        if 'gps_data' not in st.session_state or not st.session_state.gps_data:
            # Try to get from URL params (alternative method)
            try:
                # This will be updated by the JavaScript
                pass
            except:
                pass
        
        # Show current GPS status
        if st.session_state.gps_data:
            st.info(f"""
            **✅ GPS Coordinates Captured:**
            - Latitude: {st.session_state.gps_data['latitude']:.6f}
            - Longitude: {st.session_state.gps_data['longitude']:.6f}
            - Accuracy: ±{st.session_state.gps_data.get('accuracy', 0):.1f}m
            """)
        
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
            
            # Validation check
            gps_ready = st.session_state.gps_data is not None
            form_filled = all([station_name, owner_name, phone])
            
            # Show status
            if not gps_ready:
                st.warning("⚠️ Please capture GPS location first!")
            elif not form_filled:
                st.warning("⚠️ Please fill all required fields")
            
            # Submit button
            submitted = st.form_submit_button(
                "✅ SUBMIT STATION TO DATABASE" if gps_ready else "⛔ GPS REQUIRED FIRST",
                type="primary" if gps_ready else "secondary",
                use_container_width=True,
                disabled=not gps_ready
            )
            
            if submitted and gps_ready and form_filled:
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
                    
                    # Clear session storage
                    clear_js = """
                    <script>
                    sessionStorage.removeItem('gps_coordinates');
                    </script>
                    """
                    st.components.v1.html(clear_js, height=0)
                    
                    st.rerun()
                else:
                    st.error("Failed to save to database")
            elif submitted and not gps_ready:
                st.error("Please capture GPS location first!")
        
        # Developer tools for testing
        with st.expander("🛠️ Developer Tools"):
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Set Test Lagos GPS"):
                    st.session_state.gps_data = {
                        'latitude': 6.524379,
                        'longitude': 3.379206,
                        'accuracy': 25.5
                    }
                    st.success("Test GPS set! Form is now enabled.")
                    st.rerun()
            with col2:
                if st.button("Set Test Abuja GPS"):
                    st.session_state.gps_data = {
                        'latitude': 9.076478,
                        'longitude': 7.398574,
                        'accuracy': 30.2
                    }
                    st.success("Test GPS set! Form is now enabled.")
                    st.rerun()
            with col3:
                if st.button("Clear GPS Data"):
                    st.session_state.gps_data = None
                    clear_js = """
                    <script>
                    sessionStorage.removeItem('gps_coordinates');
                    </script>
                    """
                    st.components.v1.html(clear_js, height=0)
                    st.success("GPS data cleared!")
                    st.rerun()
            
            # Show current session state
            st.write("Current GPS data:", st.session_state.gps_data)

# Footer
st.markdown("---")
st.caption("Station GPS Registration • Auto-save to database • Admin view accessible anytime")

# JavaScript to handle message passing (this needs to run after the page loads)
message_handler = """
<script>
// Listen for messages from the iframe
window.addEventListener('message', function(event) {
    // Check if the message is from our component
    if (event.data && event.data.type === 'streamlit:setComponentValue') {
        // Send to Streamlit via URL parameter
        const url = new URL(window.location);
        url.searchParams.set('gps_data', event.data.value);
        window.history.pushState({}, '', url);
        
        // Trigger a rerun
        setTimeout(() => {
            window.location.reload();
        }, 100);
    }
});
</script>
"""

# Add the message handler
st.components.v1.html(message_handler, height=0)
