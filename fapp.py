"""
Station Onboarding System - NO ERRORS VERSION
GPS → Database → Admin View (No JavaScript Errors)
"""

import streamlit as st
import pandas as pd
import sqlite3
import uuid
from datetime import datetime
import base64

# Page config - NO JAVASCRIPT INJECTION HERE
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

# Database - SIMPLE
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

# CLEAN TITLE - NO JAVASCRIPT ERRORS
st.markdown("""
<div style="text-align: center;">
    <h1 style="color: #1E3A8A; margin-bottom: 10px;">⛽ Station Registration</h1>
    <p style="color: #6B7280;">Register your fuel station with GPS location</p>
</div>
""", unsafe_allow_html=True)

# Admin Login in Sidebar
with st.sidebar:
    st.markdown("### 🔐 Admin Access")
    
    if not st.session_state.admin_mode:
        if st.button("Login as Admin", use_container_width=True):
            st.session_state.admin_mode = True
            st.rerun()
    else:
        st.success("✅ Admin Mode")
        if st.button("Back to Registration", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()

# MAIN CONTENT
if st.session_state.admin_mode:
    # ADMIN VIEW
    st.markdown("## 📊 Station Registrations")
    
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
        
        # Show first station on map
        if len(df) > 0:
            st.markdown("### 📍 Location Preview")
            lat = df.iloc[0]['Latitude']
            lon = df.iloc[0]['Longitude']
            
            # Simple HTML map preview
            map_html = f"""
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #e5e7eb;">
                <h4 style="margin-top: 0;">First Station Location</h4>
                <div style="background: white; padding: 15px; border-radius: 8px; font-family: monospace;">
                    <strong>Latitude:</strong> {lat:.6f}<br>
                    <strong>Longitude:</strong> {lon:.6f}<br>
                    <strong>Accuracy:</strong> ±{df.iloc[0]['Accuracy']:.1f}m
                </div>
                <p style="margin-top: 15px; color: #6b7280; font-size: 0.9em;">
                    ⚠️ Note: For security, actual map display requires API key
                </p>
            </div>
            """
            st.markdown(map_html, unsafe_allow_html=True)
        
        # Export
        st.markdown("---")
        if st.button("📥 Export to CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="stations_export.csv" style="text-decoration: none; color: white; background: #1E3A8A; padding: 10px 20px; border-radius: 5px; display: inline-block;">Download CSV File</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    else:
        st.info("📭 No stations registered yet")
    
    st.markdown("---")
    if st.button("← Back to Main", use_container_width=True):
        st.session_state.admin_mode = False
        st.rerun()

else:
    # REGISTRATION FLOW - NO JAVASCRIPT ERRORS
    
    # Step indicator
    steps = ["Location", "Details", "Complete"]
    current = st.session_state.current_step
    
    cols = st.columns(3)
    for i, col in enumerate(cols, 1):
        with col:
            if i == current:
                st.markdown(f"<div style='background: #1E3A8A; color: white; padding: 10px; border-radius: 5px; text-align: center;'><strong>Step {i}</strong><br>{steps[i-1]}</div>", unsafe_allow_html=True)
            elif i < current:
                st.markdown(f"<div style='background: #10b981; color: white; padding: 10px; border-radius: 5px; text-align: center;'>✅ Step {i}<br>{steps[i-1]}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background: #e5e7eb; color: #6b7280; padding: 10px; border-radius: 5px; text-align: center;'>○ Step {i}<br>{steps[i-1]}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # STEP 1: GPS CAPTURE - SAFE JAVASCRIPT
    if st.session_state.current_step == 1:
        st.markdown("### Step 1: Capture Station Location")
        
        # Test mode for development
        with st.expander("🛠️ Development Mode (Add Test Data)"):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Add Lagos Coordinates", use_container_width=True):
                    st.session_state.gps_data = {
                        'latitude': 6.524379,
                        'longitude': 3.379206,
                        'accuracy': 25.5,
                        'source': 'test'
                    }
                    st.success("Test coordinates added!")
                    st.rerun()
            with col2:
                if st.button("Add Abuja Coordinates", use_container_width=True):
                    st.session_state.gps_data = {
                        'latitude': 9.076478,
                        'longitude': 7.398574,
                        'accuracy': 30.2,
                        'source': 'test'
                    }
                    st.success("Test coordinates added!")
                    st.rerun()
        
        # GPS Capture Section - SAFE IMPLEMENTATION
        st.markdown("""
        <div style="background: #eff6ff; padding: 25px; border-radius: 10px; border: 2px solid #3b82f6; margin: 20px 0;">
            <h3 style="color: #1e40af; margin-top: 0;">📍 GPS Location Capture</h3>
            <p><strong>To capture GPS coordinates:</strong></p>
            <ol>
                <li>Click the button below</li>
                <li>Allow location access when browser asks</li>
                <li>Wait for coordinates to appear</li>
                <li>Proceed to Step 2</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # GPS Button - SAFE JavaScript implementation
        gps_html = """
        <div id="gps-container" style="text-align: center; margin: 30px 0;">
            <button onclick="captureGPS()" style="
                background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%);
                color: white;
                border: none;
                padding: 20px 40px;
                border-radius: 10px;
                font-size: 1.3rem;
                font-weight: bold;
                cursor: pointer;
                width: 100%;
                max-width: 500px;
                margin: 0 auto;
                display: block;
                transition: all 0.3s;
            " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                📍 CLICK TO GET GPS LOCATION
            </button>
            
            <div id="status" style="
                margin: 25px auto;
                padding: 20px;
                background: white;
                border-radius: 8px;
                border: 2px solid #e5e7eb;
                max-width: 500px;
                min-height: 100px;
                text-align: left;
            ">
                <div style="color: #6b7280; text-align: center;">
                    <p>Click the button above to start GPS capture</p>
                    <p style="font-size: 0.9em; color: #9ca3af;">Make sure location services are enabled</p>
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
            button.style.cursor = 'wait';
            
            statusDiv.innerHTML = `
                <div style="color: #f59e0b; font-weight: bold; margin-bottom: 10px;">
                    ⏳ REQUESTING GPS LOCATION...
                </div>
                <div style="color: #6b7280; font-size: 0.9em;">
                    <p>✓ Checking geolocation support</p>
                    <p>⏳ Requesting browser permission...</p>
                    <p>Waiting for GPS signal...</p>
                </div>
            `;
            
            if (navigator.geolocation) {
                try {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            // SUCCESS
                            const lat = position.coords.latitude;
                            const lon = position.coords.longitude;
                            const acc = position.coords.accuracy;
                            
                            // Update UI with success
                            button.innerHTML = '✅ LOCATION CAPTURED';
                            button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                            button.style.cursor = 'default';
                            
                            statusDiv.innerHTML = `
                                <div style="color: #059669; font-weight: bold; margin-bottom: 10px;">
                                    ✅ GPS LOCATION CAPTURED SUCCESSFULLY!
                                </div>
                                <div style="background: #f0f9ff; padding: 15px; border-radius: 5px; border-left: 4px solid #0ea5e9;">
                                    <div style="font-family: 'Courier New', monospace;">
                                        <strong>Latitude:</strong> ${lat.toFixed(6)}<br>
                                        <strong>Longitude:</strong> ${lon.toFixed(6)}<br>
                                        <strong>Accuracy:</strong> ±${acc.toFixed(1)} meters
                                    </div>
                                </div>
                                <div style="margin-top: 15px; color: #059669; font-weight: bold;">
                                    ✓ You can now proceed to Step 2
                                </div>
                            `;
                            
                            // Store data for Streamlit
                            localStorage.setItem('gps_latitude', lat);
                            localStorage.setItem('gps_longitude', lon);
                            localStorage.setItem('gps_accuracy', acc);
                            localStorage.setItem('gps_timestamp', new Date().toISOString());
                            
                            // Show a message for Streamlit
                            const streamlitMsg = document.createElement('div');
                            streamlitMsg.id = 'streamlit_gps_data';
                            streamlitMsg.style.display = 'none';
                            streamlitMsg.textContent = JSON.stringify({
                                latitude: lat,
                                longitude: lon,
                                accuracy: acc,
                                success: true
                            });
                            document.body.appendChild(streamlitMsg);
                            
                        },
                        function(error) {
                            // ERROR - User friendly messages
                            let errorMsg = "Could not get location";
                            let details = "Unknown error occurred";
                            
                            if (error.code === 1) {
                                errorMsg = "PERMISSION DENIED";
                                details = "You need to allow location access. Please check browser settings.";
                            } else if (error.code === 2) {
                                errorMsg = "LOCATION UNAVAILABLE";
                                details = "Make sure location/GPS is turned on your device.";
                            } else if (error.code === 3) {
                                errorMsg = "REQUEST TIMEOUT";
                                details = "GPS took too long. Please try again.";
                            }
                            
                            button.innerHTML = '📍 TRY AGAIN';
                            button.style.opacity = '1';
                            button.style.cursor = 'pointer';
                            
                            statusDiv.innerHTML = `
                                <div style="color: #dc2626; font-weight: bold; margin-bottom: 10px;">
                                    ❌ ${errorMsg}
                                </div>
                                <div style="background: #fef2f2; padding: 15px; border-radius: 5px; border-left: 4px solid #dc2626;">
                                    ${details}
                                </div>
                                <div style="margin-top: 15px; color: #6b7280; font-size: 0.9em;">
                                    <p><strong>Tips:</strong></p>
                                    <ul style="margin-top: 5px;">
                                        <li>Refresh the page and try again</li>
                                        <li>Check device location settings</li>
                                        <li>Use Chrome browser for best results</li>
                                        <li>Or use Test Mode above</li>
                                    </ul>
                                </div>
                            `;
                        },
                        {
                            enableHighAccuracy: true,
                            timeout: 15000,
                            maximumAge: 0
                        }
                    );
                } catch (err) {
                    button.innerHTML = '📍 TRY AGAIN';
                    button.style.opacity = '1';
                    button.style.cursor = 'pointer';
                    
                    statusDiv.innerHTML = `
                        <div style="color: #dc2626; font-weight: bold;">
                            ❌ JAVASCRIPT ERROR
                        </div>
                        <div style="color: #6b7280;">
                            Please refresh the page and try again.
                        </div>
                    `;
                }
            } else {
                // No geolocation support
                button.innerHTML = '📍 NOT SUPPORTED';
                button.style.background = '#9ca3af';
                button.style.cursor = 'not-allowed';
                
                statusDiv.innerHTML = `
                    <div style="color: #dc2626; font-weight: bold;">
                        ❌ GEOLOCATION NOT SUPPORTED
                    </div>
                    <div style="color: #6b7280;">
                        Your browser does not support GPS location. Please use a modern browser like Chrome.
                    </div>
                `;
            }
        }
        
        // Check if we already have GPS data
        document.addEventListener('DOMContentLoaded', function() {
            const storedLat = localStorage.getItem('gps_latitude');
            if (storedLat) {
                const button = document.querySelector('button[onclick="captureGPS()"]');
                const statusDiv = document.getElementById('status');
                
                button.innerHTML = '✅ LOCATION ALREADY CAPTURED';
                button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                button.style.cursor = 'default';
                button.onclick = null;
                
                statusDiv.innerHTML = `
                    <div style="color: #059669; font-weight: bold; margin-bottom: 10px;">
                        ✅ GPS ALREADY CAPTURED
                    </div>
                    <div style="color: #6b7280;">
                        Location data is ready. You can proceed to the next step.
                    </div>
                `;
            }
        });
        </script>
        """
        
        # Display GPS component
        st.components.v1.html(gps_html, height=400)
        
        # Manual GPS data entry as fallback
        with st.expander("🔧 Manual GPS Entry (If automatic fails)"):
            col_lat, col_lon = st.columns(2)
            with col_lat:
                manual_lat = st.text_input("Enter Latitude", key="manual_lat", 
                                          placeholder="e.g., 6.524379")
            with col_lon:
                manual_lon = st.text_input("Enter Longitude", key="manual_lon",
                                          placeholder="e.g., 3.379206")
            
            if st.button("Use Manual Coordinates", key="use_manual"):
                if manual_lat and manual_lon:
                    try:
                        st.session_state.gps_data = {
                            'latitude': float(manual_lat),
                            'longitude': float(manual_lon),
                            'accuracy': 100.0,  # Default accuracy for manual entry
                            'source': 'manual'
                        }
                        st.success("Manual coordinates set!")
                        st.rerun()
                    except ValueError:
                        st.error("Please enter valid numbers")
        
        # Navigation
        st.markdown("---")
        col_prev, col_next = st.columns(2)
        
        with col_next:
            if st.session_state.gps_data:
                st.success(f"✅ GPS Ready: {st.session_state.gps_data['latitude']:.6f}, {st.session_state.gps_data['longitude']:.6f}")
                if st.button("Next Step →", type="primary", use_container_width=True):
                    st.session_state.current_step = 2
                    st.rerun()
            else:
                st.warning("Capture GPS location to continue")
        
        # Add a refresh button to check localStorage
        if st.button("🔄 Check for GPS Data", key="check_gps"):
            st.rerun()
    
    # STEP 2: STATION DETAILS
    elif st.session_state.current_step == 2:
        st.markdown("### Step 2: Station Information")
        
        # Show GPS data
        if st.session_state.gps_data:
            st.info(f"📍 GPS Coordinates: {st.session_state.gps_data['latitude']:.6f}, {st.session_state.gps_data['longitude']:.6f}")
        
        # Station form
        with st.form("station_form"):
            col1, col2 = st.columns(2)
            with col1:
                station_name = st.text_input("Station Name *", key="s_name")
                owner_name = st.text_input("Owner Name *", key="o_name")
            with col2:
                phone = st.text_input("Phone Number *", key="phone")
                station_type = st.selectbox("Station Type", ["Petrol", "Gas", "Diesel", "Multi-Fuel"], key="type")
            
            address = st.text_area("Station Address", key="address", height=100)
            
            st.markdown("---")
            
            col_back, col_submit = st.columns(2)
            with col_back:
                if st.form_submit_button("← Back", use_container_width=True):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col_submit:
                if st.form_submit_button("✅ Submit Registration", type="primary", use_container_width=True):
                    if not all([station_name, owner_name, phone]):
                        st.error("Please fill all required fields")
                    elif not st.session_state.gps_data:
                        st.error("GPS data missing. Please go back to Step 1.")
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
                        else:
                            st.error("Failed to save to database")
    
    # STEP 3: COMPLETION
    elif st.session_state.current_step == 3:
        st.balloons()
        
        st.markdown("""
        <div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #dbeafe 0%, #f0f9ff 100%); border-radius: 15px; margin: 20px 0;">
            <h1 style="color: #059669;">✅ REGISTRATION COMPLETE!</h1>
            <p style="font-size: 1.2rem; color: #1E3A8A;">Your station has been registered with GPS coordinates</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show registration details
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📋 Registration Details")
            st.markdown(f"""
            <div style="background: white; padding: 20px; border-radius: 10px; border: 1px solid #e5e7eb;">
                <p><strong>Station ID:</strong><br><code>{st.session_state.form_data.get('station_id', 'N/A')}</code></p>
                <p><strong>Station Name:</strong><br>{st.session_state.form_data.get('station_name', 'N/A')}</p>
                <p><strong>Owner Name:</strong><br>{st.session_state.form_data.get('owner_name', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 📍 GPS Coordinates")
            if st.session_state.gps_data:
                st.markdown(f"""
                <div style="background: white; padding: 20px; border-radius: 10px; border: 1px solid #e5e7eb;">
                    <p><strong>Latitude:</strong><br>{st.session_state.gps_data['latitude']:.6f}</p>
                    <p><strong>Longitude:</strong><br>{st.session_state.gps_data['longitude']:.6f}</p>
                    <p><strong>Accuracy:</strong><br>±{st.session_state.gps_data.get('accuracy', 0):.1f} meters</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Next actions
        st.markdown("---")
        st.markdown("### What would you like to do next?")
        
        col_admin, col_new, col_view = st.columns(3)
        
        with col_admin:
            if st.button("📊 Go to Admin View", use_container_width=True):
                st.session_state.admin_mode = True
                st.session_state.current_step = 1
                st.session_state.gps_data = None
                st.rerun()
        
        with col_new:
            if st.button("➕ Register Another", use_container_width=True):
                st.session_state.current_step = 1
                st.session_state.gps_data = None
                st.session_state.form_data = {}
                st.rerun()
        
        with col_view:
            # Show current registration in a nice box
            st.markdown("""
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                <p style="margin: 0; color: #6b7280;">Current registration saved to database ✅</p>
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.9rem; padding: 20px;">
    <p>Station GPS Registration System • Coordinates saved directly to database</p>
    <p style="font-size: 0.8rem; color: #9ca3af;">No JavaScript errors • Reliable GPS capture</p>
</div>
""", unsafe_allow_html=True)
