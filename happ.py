"""
Station Onboarding System - ONE-STEP GPS REGISTRATION
Capture GPS + Station Info → Direct to Database
"""

import streamlit as st
import pandas as pd
import sqlite3
import uuid
from datetime import datetime
import base64
import json
import hashlib
import secrets
from streamlit.components.v1 import html

# Page config
st.set_page_config(
    page_title="Station GPS Registration",
    page_icon="⛽",
    layout="wide"
)

# Initialize session state
if 'station_saved' not in st.session_state:
    st.session_state.station_saved = False
if 'station_id' not in st.session_state:
    st.session_state.station_id = None
if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'login_attempted' not in st.session_state:
    st.session_state.login_attempted = False
if 'gps_captured' not in st.session_state:
    st.session_state.gps_captured = False

# Database initialization
def init_db():
    conn = sqlite3.connect('stations_gps.db')
    c = conn.cursor()
    
    # Stations table
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
    
    # Admin users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            salt TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'admin',
            created_at TEXT
        )
    ''')
    
    # Create default admin if not exists
    c.execute("SELECT COUNT(*) FROM admin_users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        salt = secrets.token_hex(16)
        password = "admin123"  # Default password - should be changed
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        
        c.execute('''
            INSERT INTO admin_users (username, password_hash, salt, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', password_hash, salt, 'Administrator', 'admin', datetime.now().isoformat()))
        
        conn.commit()
        print("Default admin created: admin/admin123")
    
    conn.commit()
    return conn

conn = init_db()

# Password hashing functions
def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt

def verify_password(password, stored_hash, salt):
    return hashlib.sha256((password + salt).encode()).hexdigest() == stored_hash

# Admin user management
def authenticate_user(username, password):
    try:
        c = conn.cursor()
        c.execute('''
            SELECT username, password_hash, salt, full_name, role 
            FROM admin_users 
            WHERE username = ?
        ''', (username,))
        
        result = c.fetchone()
        if result:
            stored_hash = result[1]
            salt = result[2]
            
            if verify_password(password, stored_hash, salt):
                return {
                    'username': result[0],
                    'full_name': result[3],
                    'role': result[4]
                }
        return None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None

# Station functions
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

# Login/Logout functions
def show_login_form():
    """Display login form"""
    st.markdown("### 🔐 Admin Login")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
                st.session_state.login_attempted = True
                return False
            
            user = authenticate_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user['username']
                st.session_state.admin_mode = True
                st.session_state.login_attempted = False
                st.success(f"Welcome, {user['full_name']}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
                st.session_state.login_attempted = True
                return False
    return False

def logout():
    """Logout user"""
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.admin_mode = False
    st.session_state.login_attempted = False
    st.rerun()

# Main app
st.title("⛽ Fuel Station GPS Registration")
st.markdown("---")

# Sidebar for login/logout
with st.sidebar:
    if st.session_state.logged_in:
        # User is logged in - show admin options
        st.markdown(f"### 👤 {st.session_state.username}")
        
        if st.button("📊 View Submissions", use_container_width=True):
            st.session_state.admin_mode = True
            st.rerun()
        
        if st.button("🔒 Logout", use_container_width=True):
            logout()
        
        st.markdown("---")
        st.caption(f"Logged in: {st.session_state.username}")
    else:
        # Not logged in - show login form
        show_login_form()

# Main content area
if st.session_state.admin_mode and st.session_state.logged_in:
    # ADMIN DASHBOARD
    st.header("📊 Admin Dashboard")
    
    # Quick stats
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
        
        # Stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Stations", len(df))
        with col2:
            pending = len(df[df['Status'] == 'pending'])
            st.metric("Pending", pending)
        with col3:
            approved = len(df[df['Status'] == 'approved'])
            st.metric("Approved", approved)
        with col4:
            latest = df['Time'].iloc[0] if len(df) > 0 else "None"
            st.metric("Latest", latest)
        
        st.markdown("---")
        
        # Display all stations
        st.subheader(f"All Station Submissions ({len(df)})")
        
        st.dataframe(
            df[['ID', 'Name', 'Owner', 'Phone', 'Coordinates', 'Accuracy', 'Time', 'Status']],
            use_container_width=True,
            hide_index=True
        )
        
        # Export option
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("📥 Export to CSV", use_container_width=True):
                csv = df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="stations.csv">Download CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
    
    else:
        st.info("No station submissions yet.")
    
    # Back to registration button
    if st.button("← Back to Registration", use_container_width=True):
        st.session_state.admin_mode = False
        st.rerun()

elif st.session_state.admin_mode and not st.session_state.logged_in:
    # Redirect to login
    st.warning("⚠️ Please login to access admin dashboard")
    show_login_form()

else:
    # REGISTRATION FLOW (Public access)
    if st.session_state.station_saved:
        # COMPLETION SCREEN
        st.balloons()
        st.success(f"""
        ## ✅ Station Submitted Successfully!
        
        **Station ID:** {st.session_state.station_id}
        
        Your station has been registered and is pending review.
        Our team will contact you for verification.
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Register Another Station", type="primary", use_container_width=True):
                st.session_state.station_saved = False
                st.session_state.station_id = None
                st.rerun()
        with col2:
            if st.button("🏠 Return Home", use_container_width=True):
                st.session_state.station_saved = False
                st.session_state.station_id = None
                st.rerun()
    
    else:
        # ONE-STEP REGISTRATION FORM
        st.header("📍 Register New Station (One Step)")
        
        # Create the combined form
        with st.form("one_step_registration", clear_on_submit=True):
            st.markdown("### Step 1: Station Information")
            
            col1, col2 = st.columns(2)
            with col1:
                station_name = st.text_input("Station Name *", 
                                           placeholder="e.g., Mega Fuel Station",
                                           help="Enter the official name of your fuel station")
                owner_name = st.text_input("Owner Name *", 
                                         placeholder="Full name",
                                         help="Enter the full name of the station owner")
            with col2:
                phone = st.text_input("Phone Number *", 
                                    placeholder="08012345678",
                                    help="Enter a valid phone number for contact")
            
            st.markdown("---")
            st.markdown("### Step 2: GPS Location")
            
            # GPS capture button that triggers form submission
            st.markdown("""
            <div style="background: #f0f9ff; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p><strong>📱 GPS Capture Instructions:</strong></p>
                <ul>
                    <li>Fill all station information above first</li>
                    <li>Click the GPS button below</li>
                    <li>Allow location access when prompted</li>
                    <li>The form will submit automatically with GPS data</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # Hidden fields for GPS data
            latitude_field = st.empty()
            longitude_field = st.empty()
            accuracy_field = st.empty()
            
            # GPS JavaScript that submits the form
            gps_html = '''
            <div style="text-align: center; margin: 20px 0;">
                <button onclick="captureGPSAndSubmit()" style="
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
                    📍 CAPTURE GPS & SUBMIT REGISTRATION
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
                        Click button to capture location and submit registration
                    </div>
                </div>
            </div>
            
            <script>
            function captureGPSAndSubmit() {
                const gpsStatus = document.getElementById('gps-status');
                const button = document.querySelector('button[onclick="captureGPSAndSubmit()"]');
                
                // First validate form fields
                const stationName = document.querySelector('input[placeholder*="Station Name"]');
                const ownerName = document.querySelector('input[placeholder*="Full name"]');
                const phone = document.querySelector('input[placeholder*="08012345678"]');
                
                if (!stationName || !stationName.value || 
                    !ownerName || !ownerName.value || 
                    !phone || !phone.value) {
                    gpsStatus.innerHTML = `
                        <div style="color: #dc2626; font-weight: bold;">
                            ❌ Please fill all station information first
                        </div>
                        <p style="color: #6b7280;">Fill the form above before capturing GPS</p>
                    `;
                    return;
                }
                
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
                                    ✅ GPS CAPTURED! SUBMITTING...
                                </div>
                                <div style="background: #f0f9ff; padding: 15px; border-radius: 5px; margin-top: 10px;">
                                    <div style="font-family: monospace;">
                                        <strong>Latitude:</strong> ${lat.toFixed(6)}<br>
                                        <strong>Longitude:</strong> ${lon.toFixed(6)}<br>
                                        <strong>Accuracy:</strong> ±${acc.toFixed(1)}m
                                    </div>
                                </div>
                            `;
                            
                            button.innerHTML = '✅ SUBMITTING TO DATABASE...';
                            button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                            
                            // Find the form and fill GPS fields
                            const latitudeInputs = document.querySelectorAll('input[type="number"]');
                            const longitudeInputs = document.querySelectorAll('input[type="number"]');
                            
                            // Create hidden inputs for GPS data
                            const form = document.querySelector('form');
                            
                            // Create hidden inputs
                            const latInput = document.createElement('input');
                            latInput.type = 'hidden';
                            latInput.name = 'latitude';
                            latInput.value = lat;
                            
                            const lonInput = document.createElement('input');
                            lonInput.type = 'hidden';
                            lonInput.name = 'longitude';
                            lonInput.value = lon;
                            
                            const accInput = document.createElement('input');
                            accInput.type = 'hidden';
                            accInput.name = 'accuracy';
                            accInput.value = acc;
                            
                            form.appendChild(latInput);
                            form.appendChild(lonInput);
                            form.appendChild(accInput);
                            
                            // Submit the form
                            setTimeout(() => {
                                form.querySelector('button[type="submit"]').click();
                            }, 1000);
                            
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
            </script>
            '''
            
            # Display GPS component
            st.components.v1.html(gps_html, height=300)
            
            # Hidden GPS fields that will be populated by JavaScript
            latitude = latitude_field.number_input("Latitude", value=0.0, format="%.6f", key="lat_hidden")
            longitude = longitude_field.number_input("Longitude", value=0.0, format="%.6f", key="lon_hidden")
            accuracy = accuracy_field.number_input("Accuracy", value=0.0, format="%.1f", key="acc_hidden")
            
            # Check if form was submitted with GPS data
            submitted = st.form_submit_button(
                "✅ READY FOR GPS CAPTURE",
                type="secondary",
                use_container_width=True,
                disabled=True  # Disabled because GPS button handles submission
            )
            
            # Check if GPS data was provided in form submission
            form_data = st.session_state.get('form_data', {})
            
            if form_data.get('latitude') and form_data.get('longitude'):
                # Create GPS data object
                gps_data = {
                    'latitude': form_data['latitude'],
                    'longitude': form_data['longitude'],
                    'accuracy': form_data.get('accuracy', 0)
                }
                
                # Validate all fields are filled
                if station_name and owner_name and phone:
                    # Save to database
                    station_id = save_station_to_db(
                        station_name,
                        owner_name,
                        phone,
                        gps_data
                    )
                    
                    if station_id:
                        st.session_state.station_saved = True
                        st.session_state.station_id = station_id
                        st.session_state.form_data = {}  # Clear form data
                        st.rerun()
                    else:
                        st.error("Failed to save to database. Please try again.")
                else:
                    st.error("Please fill all station information fields!")
            
            # Clear form data after processing
            if 'form_data' in st.session_state:
                st.session_state.form_data = {}

# Footer
st.markdown("---")
st.caption("""
Station GPS Registration System • One-Step Registration • 
[Login Required for Admin Access] • © 2024
""")

# JavaScript to handle form submission
js_code = '''
<script>
// Listen for form submissions
document.addEventListener('submit', function(event) {
    // Only process our registration form
    if (event.target.matches('form')) {
        // Get GPS data from localStorage
        const gpsData = localStorage.getItem('last_gps_capture');
        if (gpsData) {
            const data = JSON.parse(gpsData);
            
            // Create hidden inputs for GPS data
            const latInput = document.createElement('input');
            latInput.type = 'hidden';
            latInput.name = 'latitude';
            latInput.value = data.latitude;
            
            const lonInput = document.createElement('input');
            lonInput.type = 'hidden';
            lonInput.name = 'longitude';
            lonInput.value = data.longitude;
            
            const accInput = document.createElement('input');
            accInput.type = 'hidden';
            accInput.name = 'accuracy';
            accInput.value = data.accuracy;
            
            event.target.appendChild(latInput);
            event.target.appendChild(lonInput);
            event.target.appendChild(accInput);
            
            // Clear localStorage
            localStorage.removeItem('last_gps_capture');
        }
    }
});
</script>
'''

st.components.v1.html(js_code, height=0)
