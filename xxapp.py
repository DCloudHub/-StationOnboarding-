"""
Station GPS Registration - One Page App
Capture GPS location with timestamp → View in Admin Panel
"""

import streamlit as st
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
import base64
import hashlib
import secrets
from streamlit.components.v1 import html

# Page config
st.set_page_config(
    page_title="Station GPS Tracker",
    page_icon="📍",
    layout="wide"
)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False

# Database initialization
def init_db():
    conn = sqlite3.connect('gps_locations.db')
    c = conn.cursor()
    
    # GPS locations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS gps_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id TEXT UNIQUE,
            station_name TEXT,
            latitude REAL,
            longitude REAL,
            accuracy REAL,
            timestamp TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Admin users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            salt TEXT,
            full_name TEXT,
            created_at TEXT
        )
    ''')
    
    # Create default admin if not exists
    c.execute("SELECT COUNT(*) FROM admin_users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        salt = secrets.token_hex(16)
        password = "admin123"
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        
        c.execute('''
            INSERT INTO admin_users (username, password_hash, salt, full_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', password_hash, salt, 'Administrator', datetime.now().isoformat()))
        
        conn.commit()
        st.sidebar.info("Default login: admin/admin123")
    
    conn.commit()
    return conn

conn = init_db()

# Password functions
def verify_password(password, stored_hash, salt):
    return hashlib.sha256((password + salt).encode()).hexdigest() == stored_hash

def authenticate_user(username, password):
    try:
        c = conn.cursor()
        c.execute('SELECT username, password_hash, salt, full_name FROM admin_users WHERE username = ?', (username,))
        result = c.fetchone()
        
        if result:
            stored_hash = result[1]
            salt = result[2]
            
            if verify_password(password, stored_hash, salt):
                return {
                    'username': result[0],
                    'full_name': result[3]
                }
        return None
    except:
        return None

# GPS functions
def save_gps_location(station_name, latitude, longitude, accuracy):
    try:
        c = conn.cursor()
        location_id = f"LOC-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute('''
            INSERT INTO gps_locations (location_id, station_name, latitude, longitude, accuracy, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (location_id, station_name, latitude, longitude, accuracy, timestamp))
        
        conn.commit()
        return location_id, timestamp
    except Exception as e:
        st.error(f"Error saving GPS: {e}")
        return None, None

def get_all_locations():
    try:
        c = conn.cursor()
        c.execute('''
            SELECT location_id, station_name, latitude, longitude, accuracy, timestamp, status
            FROM gps_locations 
            ORDER BY timestamp DESC
        ''')
        return c.fetchall()
    except:
        return []

def get_locations_count():
    try:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM gps_locations')
        return c.fetchone()[0]
    except:
        return 0

def get_today_locations():
    try:
        c = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('SELECT COUNT(*) FROM gps_locations WHERE date(timestamp) = ?', (today,))
        return c.fetchone()[0]
    except:
        return 0

def delete_location(location_id):
    try:
        c = conn.cursor()
        c.execute('DELETE FROM gps_locations WHERE location_id = ?', (location_id,))
        conn.commit()
        return True
    except:
        return False

# Sidebar - Admin Panel
with st.sidebar:
    st.title("📊 Admin Panel")
    
    if st.session_state.logged_in:
        st.success(f"✅ Logged in as: {st.session_state.username}")
        
        if st.button("👁️ View All Locations", use_container_width=True):
            st.session_state.admin_mode = True
            st.rerun()
            
        if st.button("➕ New GPS Capture", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()
            
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.admin_mode = False
            st.rerun()
            
        st.markdown("---")
        
        # Quick stats
        total_locations = get_locations_count()
        today_locations = get_today_locations()
        
        st.metric("📍 Total Captures", total_locations)
        st.metric("📅 Today's Captures", today_locations)
        
    else:
        st.markdown("### 🔐 Admin Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login", use_container_width=True):
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.username = user['username']
                        st.success(f"Welcome, {user['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.warning("Enter username and password")

# Main content
st.title("📍 GPS Location Capture System")

if st.session_state.admin_mode and st.session_state.logged_in:
    # ADMIN VIEW
    st.header("📋 All GPS Locations")
    
    locations = get_all_locations()
    
    if locations:
        df = pd.DataFrame(locations, columns=[
            'ID', 'Station', 'Latitude', 'Longitude', 'Accuracy', 'Timestamp', 'Status'
        ])
        
        # Display statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(df))
        with col2:
            recent_24h = len(df[pd.to_datetime(df['Timestamp']) > datetime.now() - pd.Timedelta(hours=24)])
            st.metric("Last 24h", recent_24h)
        with col3:
            st.metric("Active", len(df[df['Status'] == 'active']))
        with col4:
            if st.button("🔄 Refresh"):
                st.rerun()
        
        st.markdown("---")
        
        # Display data
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Latitude": st.column_config.NumberColumn(format="%.6f"),
                "Longitude": st.column_config.NumberColumn(format="%.6f"),
                "Accuracy": st.column_config.NumberColumn(format="%.1f"),
                "Timestamp": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss")
            }
        )
        
        # Actions
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            # Export to CSV
            if st.button("📥 Export CSV", use_container_width=True):
                csv = df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="gps_locations.csv">Download CSV File</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            # Delete functionality
            with st.expander("🗑️ Delete Location"):
                location_to_delete = st.selectbox(
                    "Select location to delete",
                    options=df['ID'].tolist(),
                    key="delete_select"
                )
                if st.button("Delete Selected", type="secondary"):
                    if delete_location(location_to_delete):
                        st.success(f"Deleted: {location_to_delete}")
                        st.rerun()
                    else:
                        st.error("Failed to delete")
    
    else:
        st.info("No GPS locations captured yet.")
        if st.button("⬅️ Back to Capture"):
            st.session_state.admin_mode = False
            st.rerun()

else:
    # GPS CAPTURE INTERFACE
    st.markdown("""
    <div style="background: #f0f9ff; padding: 25px; border-radius: 15px; margin-bottom: 30px;">
        <h3 style="color: #1e40af; margin-top: 0;">Capture GPS Location</h3>
        <p>Click the button below to capture your current GPS coordinates with timestamp.</p>
        <p style="color: #6b7280; font-size: 0.9em;">📍 Location accuracy depends on your device and GPS signal.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Station name input
    station_name = st.text_input(
        "📍 Station/Location Name",
        placeholder="Enter location name (e.g., Main Office, Site A, etc.)",
        help="Give a name to identify this location"
    )
    
    # GPS Capture Button
    gps_html = f'''
    <div style="text-align: center; margin: 40px 0;">
        <button onclick="captureGPS()" style="
            background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%);
            color: white;
            border: none;
            padding: 25px 50px;
            border-radius: 12px;
            font-size: 1.3rem;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            max-width: 500px;
            margin: 0 auto;
            display: block;
            box-shadow: 0 4px 20px rgba(30, 64, 175, 0.3);
            transition: all 0.3s ease;
        "
            onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 6px 25px rgba(30, 64, 175, 0.4)';"
            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 20px rgba(30, 64, 175, 0.3)';"
        >
            📍 GET MY LOCATION
        </button>
        
        <div id="gps-status" style="
            margin: 30px auto;
            padding: 25px;
            background: white;
            border-radius: 10px;
            border: 2px solid #e5e7eb;
            max-width: 500px;
            min-height: 150px;
        ">
            <div style="color: #6b7280; text-align: center; padding: 20px;">
                <p style="margin: 0;">Click the button above to capture your GPS location.</p>
                <p style="margin: 10px 0 0 0; font-size: 0.9em;">Location and timestamp will be saved automatically.</p>
            </div>
        </div>
    </div>
    
    <script>
    function captureGPS() {{
        const stationName = "{station_name or ''}";
        if (!stationName) {{
            document.getElementById('gps-status').innerHTML = `
                <div style="color: #dc2626; font-weight: bold; text-align: center;">
                    ❌ Please enter a location name first
                </div>
                <p style="color: #6b7280; text-align: center;">Enter a name above before capturing GPS</p>
            `;
            return;
        }}
        
        const gpsStatus = document.getElementById('gps-status');
        const button = document.querySelector('button[onclick="captureGPS()"]');
        
        button.innerHTML = '⏳ CAPTURING LOCATION...';
        button.disabled = true;
        button.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
        
        gpsStatus.innerHTML = `
            <div style="color: #f59e0b; font-weight: bold; text-align: center;">
                ⏳ REQUESTING LOCATION...
            </div>
            <div style="text-align: center; margin-top: 15px;">
                <p style="color: #6b7280;">Please allow location access in your browser</p>
            </div>
        `;
        
        if (navigator.geolocation) {{
            navigator.geolocation.getCurrentPosition(
                function(position) {{
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    const acc = position.coords.accuracy;
                    const timestamp = new Date().toISOString();
                    
                    // Show captured coordinates
                    gpsStatus.innerHTML = `
                        <div style="color: #059669; font-weight: bold; text-align: center;">
                            ✅ LOCATION CAPTURED!
                        </div>
                        <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin-top: 15px;">
                            <div style="font-family: monospace; font-size: 0.9em;">
                                <strong>📍 Location:</strong> {station_name}<br>
                                <strong>📡 Latitude:</strong> ${{lat.toFixed(6)}}<br>
                                <strong>📡 Longitude:</strong> ${{lon.toFixed(6)}}<br>
                                <strong>🎯 Accuracy:</strong> ±${{acc.toFixed(1)}} meters<br>
                                <strong>🕒 Time:</strong> ${{new Date().toLocaleString()}}
                            </div>
                        </div>
                        <div style="color: #059669; text-align: center; margin-top: 15px; font-weight: bold;">
                            ⬇️ Saving to database...
                        </div>
                    `;
                    
                    button.innerHTML = '✅ SAVING...';
                    button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                    
                    // Prepare data for Streamlit
                    const gpsData = {{
                        station_name: stationName,
                        latitude: lat,
                        longitude: lon,
                        accuracy: acc,
                        timestamp: timestamp
                    }};
                    
                    // Send to Streamlit via URL
                    const url = new URL(window.location);
                    url.searchParams.set('gps_capture', JSON.stringify(gpsData));
                    window.history.replaceState({{}}, '', url);
                    
                    // Show success and reload
                    setTimeout(() => {{
                        gpsStatus.innerHTML = `
                            <div style="color: #059669; font-weight: bold; text-align: center; padding: 20px;">
                                ✅ LOCATION SAVED!
                            </div>
                            <div style="background: #d1fae5; padding: 20px; border-radius: 8px; margin-top: 10px;">
                                <p style="color: #065f46; text-align: center; margin: 0;">
                                    GPS coordinates saved to database.<br>
                                    <span style="font-size: 0.9em;">Page will refresh in 3 seconds...</span>
                                </p>
                            </div>
                        `;
                        
                        button.innerHTML = '📍 LOCATION SAVED';
                        button.disabled = true;
                        
                        // Reload to show updated data
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 3000);
                    }}, 1500);
                    
                }},
                function(error) {{
                    let errorMsg = "Failed to get location";
                    if (error.code === 1) errorMsg = "Permission denied - Please allow location access";
                    if (error.code === 2) errorMsg = "Location unavailable";
                    if (error.code === 3) errorMsg = "Request timeout - Please try again";
                    
                    gpsStatus.innerHTML = `
                        <div style="color: #dc2626; font-weight: bold; text-align: center;">
                            ❌ ${{errorMsg}}
                        </div>
                        <div style="text-align: center; margin-top: 15px;">
                            <p style="color: #6b7280;">Please check your location settings and try again</p>
                        </div>
                    `;
                    
                    button.innerHTML = '📍 TRY AGAIN';
                    button.disabled = false;
                    button.style.background = 'linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%)';
                }},
                {{ 
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }}
            );
        }} else {{
            gpsStatus.innerHTML = `
                <div style="color: #dc2626; font-weight: bold; text-align: center;">
                    ❌ GPS not supported
                </div>
                <p style="color: #6b7280; text-align: center;">Your browser does not support GPS location</p>
            `;
            button.disabled = false;
            button.style.background = 'linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%)';
        }}
    }}
    </script>
    '''
    
    # Display GPS component
    st.components.v1.html(gps_html, height=450)
    
    # Handle GPS data from URL parameters
    query_params = st.query_params
    
    if 'gps_capture' in query_params:
        try:
            import json
            gps_data_json = query_params['gps_capture']
            gps_data = json.loads(gps_data_json)
            
            # Save to database
            location_id, saved_timestamp = save_gps_location(
                gps_data['station_name'],
                gps_data['latitude'],
                gps_data['longitude'],
                gps_data['accuracy']
            )
            
            if location_id:
                # Clear the URL parameter
                st.query_params.clear()
                
                # Show success message
                st.success(f"""
                ✅ **Location Saved Successfully!**
                
                **ID:** {location_id}
                **Station:** {gps_data['station_name']}
                **Coordinates:** {gps_data['latitude']:.6f}, {gps_data['longitude']:.6f}
                **Accuracy:** ±{gps_data['accuracy']:.1f}m
                **Time:** {saved_timestamp}
                """)
                
                # Auto-refresh after 2 seconds
                st.markdown("""
                <script>
                setTimeout(function() {
                    window.location.reload();
                }, 2000);
                </script>
                """, unsafe_allow_html=True)
            else:
                st.error("Failed to save location to database")
                
        except Exception as e:
            st.error(f"Error processing GPS data: {str(e)}")
    
    # Recent captures preview (if logged in)
    if st.session_state.logged_in:
        st.markdown("---")
        st.subheader("📋 Recent Captures")
        
        locations = get_all_locations()
        if locations and len(locations) > 0:
            recent_df = pd.DataFrame(locations[:5], columns=[
                'ID', 'Station', 'Latitude', 'Longitude', 'Accuracy', 'Timestamp', 'Status'
            ])
            
            st.dataframe(
                recent_df[['Station', 'Latitude', 'Longitude', 'Timestamp']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Latitude": st.column_config.NumberColumn(format="%.6f"),
                    "Longitude": st.column_config.NumberColumn(format="%.6f"),
                    "Timestamp": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss")
                }
            )
            
            if len(locations) > 5:
                st.caption(f"Showing 5 of {len(locations)} total locations")

# Footer
st.markdown("---")
st.caption("""
📍 GPS Location Capture System • 
Captures: Latitude, Longitude, Accuracy, and Timestamp • 
Admin login required to view database • © 2024
""")

# Add custom CSS
st.markdown("""
<style>
/* Smooth animations */
@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

button[onclick="captureGPS()"]:hover {
    animation: pulse 0.5s ease-in-out;
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #555;
}
</style>
""", unsafe_allow_html=True)
