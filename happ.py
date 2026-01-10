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
import hashlib
import secrets

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
        password = "admin123"
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        
        c.execute('''
            INSERT INTO admin_users (username, password_hash, salt, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', password_hash, salt, 'Administrator', 'admin', datetime.now().isoformat()))
        
        conn.commit()
    
    conn.commit()
    return conn

conn = init_db()

# Password hashing functions
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
def save_station_to_db(station_name, owner_name, phone, latitude, longitude, accuracy):
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
            latitude,
            longitude,
            accuracy,
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
        
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
                return False
            
            user = authenticate_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user['username']
                st.session_state.admin_mode = True
                st.success(f"Welcome, {user['full_name']}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
                return False
    return False

def logout():
    """Logout user"""
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.admin_mode = False
    st.rerun()

# Main app
st.title("⛽ Fuel Station GPS Registration")
st.markdown("---")

# Sidebar for login/logout
with st.sidebar:
    if st.session_state.logged_in:
        st.markdown(f"### 👤 {st.session_state.username}")
        
        if st.button("📊 View Submissions", use_container_width=True):
            st.session_state.admin_mode = True
            st.rerun()
        
        if st.button("🔒 Logout", use_container_width=True):
            logout()
        
        st.markdown("---")
        st.caption(f"Logged in: {st.session_state.username}")
    else:
        show_login_form()

# Main content area
if st.session_state.admin_mode and st.session_state.logged_in:
    # ADMIN DASHBOARD
    st.header("📊 Admin Dashboard")
    
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
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Stations", len(df))
        with col2:
            pending = len(df[df['Status'] == 'pending'])
            st.metric("Pending", pending)
        with col3:
            latest = df['Time'].iloc[0] if len(df) > 0 else "None"
            st.metric("Latest", latest)
        
        st.markdown("---")
        
        # Display all stations
        st.dataframe(
            df[['ID', 'Name', 'Owner', 'Phone', 'Coordinates', 'Accuracy', 'Time', 'Status']],
            use_container_width=True,
            hide_index=True
        )
        
        # Export option
        if st.button("📥 Export to CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="stations.csv">Download CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    else:
        st.info("No station submissions yet.")
    
    if st.button("← Back to Registration", use_container_width=True):
        st.session_state.admin_mode = False
        st.rerun()

elif st.session_state.admin_mode and not st.session_state.logged_in:
    st.warning("⚠️ Please login to access admin dashboard")
    show_login_form()

else:
    # ONE-STEP REGISTRATION
    if st.session_state.station_saved:
        st.balloons()
        st.success(f"""
        ## ✅ Station Submitted Successfully!
        
        **Station ID:** {st.session_state.station_id}
        
        Your station has been registered and is pending review.
        Our team will contact you for verification.
        """)
        
        if st.button("➕ Register Another Station", type="primary", use_container_width=True):
            st.session_state.station_saved = False
            st.session_state.station_id = None
            st.rerun()
    
    else:
        st.header("📍 Register New Station")
        
        # Create form columns
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
        
        # Hidden fields for GPS data
        st.markdown("---")
        st.markdown("### 📱 GPS Location Capture")
        
        # Check if all required fields are filled
        all_fields_filled = all([station_name, owner_name, phone])
        
        if not all_fields_filled:
            st.warning("⚠️ Please fill all station information above before capturing GPS")
        
        # GPS capture component
        gps_html = f'''
        <div style="text-align: center; margin: 20px 0;">
            <button onclick="captureGPS()" style="
                background: {'linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%)' if all_fields_filled else 'linear-gradient(135deg, #6b7280 0%, #9ca3af 100%)'};
                color: white;
                border: none;
                padding: 20px 40px;
                border-radius: 10px;
                font-size: 1.2rem;
                font-weight: bold;
                cursor: {'pointer' if all_fields_filled else 'not-allowed'};
                width: 100%;
                max-width: 500px;
                margin: 0 auto;
                display: block;
                opacity: {'1' if all_fields_filled else '0.6'};
            "
                {'disabled' if not all_fields_filled else ''}
            >
                {'📍 CAPTURE GPS & SUBMIT REGISTRATION' if all_fields_filled else '⛔ FILL FORM FIRST'}
            </button>
            
            <div id="gps-status" style="
                margin: 20px auto;
                padding: 20px;
                background: white;
                border-radius: 8px;
                border: 2px solid #e5e7eb;
                max-width: 500px;
                min-height: 120px;
            ">
                <div style="color: #6b7280; text-align: center;">
                    {f'✓ All fields filled! Click button to capture GPS and submit' if all_fields_filled else 'Fill all station information above first'}
                </div>
            </div>
            
            <!-- Hidden form that will be submitted with GPS data -->
            <form id="gps-form" style="display: none;">
                <input type="hidden" name="station_name" value="{station_name or ''}">
                <input type="hidden" name="owner_name" value="{owner_name or ''}">
                <input type="hidden" name="phone" value="{phone or ''}">
                <input type="hidden" name="latitude" id="latitude-input">
                <input type="hidden" name="longitude" id="longitude-input">
                <input type="hidden" name="accuracy" id="accuracy-input">
                <button type="submit" id="submit-btn"></button>
            </form>
            
            <div id="form-status" style="display: none;"></div>
        </div>
        
        <script>
        function captureGPS() {{
            // Check if form is filled (client-side validation)
            const stationName = "{station_name or ''}";
            const ownerName = "{owner_name or ''}";
            const phone = "{phone or ''}";
            
            if (!stationName || !ownerName || !phone) {{
                document.getElementById('gps-status').innerHTML = `
                    <div style="color: #dc2626; font-weight: bold;">
                        ❌ Please fill all station information first
                    </div>
                    <p style="color: #6b7280;">Fill the form above before capturing GPS</p>
                `;
                return;
            }}
            
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
            
            if (navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition(
                    function(position) {{
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
                                    <strong>Latitude:</strong> ${{lat.toFixed(6)}}<br>
                                    <strong>Longitude:</strong> ${{lon.toFixed(6)}}<br>
                                    <strong>Accuracy:</strong> ±${{acc.toFixed(1)}}m
                                </div>
                            </div>
                        `;
                        
                        button.innerHTML = '✅ SUBMITTING...';
                        button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                        
                        // Fill the hidden form
                        document.getElementById('latitude-input').value = lat;
                        document.getElementById('longitude-input').value = lon;
                        document.getElementById('accuracy-input').value = acc;
                        
                        // Submit the form
                        setTimeout(() => {{
                            document.getElementById('submit-btn').click();
                        }}, 1500);
                        
                    }},
                    function(error) {{
                        let errorMsg = "Failed to get location";
                        if (error.code === 1) errorMsg = "Permission denied";
                        if (error.code === 2) errorMsg = "Location unavailable";
                        if (error.code === 3) errorMsg = "Request timeout";
                        
                        gpsStatus.innerHTML = `
                            <div style="color: #dc2626; font-weight: bold;">
                                ❌ ${{errorMsg}}
                            </div>
                            <p style="color: #6b7280;">Please try again</p>
                        `;
                        
                        button.innerHTML = '📍 TRY AGAIN';
                        button.disabled = false;
                    }},
                    {{ enableHighAccuracy: true, timeout: 15000 }}
                );
            }} else {{
                gpsStatus.innerHTML = '<div style="color: #dc2626;">GPS not supported</div>';
                button.disabled = false;
            }}
        }}
        
        // Handle form submission
        document.getElementById('gps-form').addEventListener('submit', function(e) {{
            e.preventDefault();
            
            // Create FormData from the form
            const formData = new FormData(this);
            
            // Send data to Streamlit via fetch
            fetch(window.location.href, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/x-www-form-urlencoded',
                }},
                body: new URLSearchParams(formData)
            }}).then(response => {{
                // Show success message
                document.getElementById('gps-status').innerHTML = `
                    <div style="color: #059669; font-weight: bold; text-align: center;">
                        ✅ Registration Complete!
                    </div>
                    <div style="background: #d1fae5; padding: 15px; border-radius: 5px; margin-top: 10px;">
                        <p style="color: #065f46; text-align: center;">
                            Station has been registered successfully.<br>
                            Page will refresh shortly...
                        </p>
                    </div>
                `;
                
                // Refresh page after delay
                setTimeout(() => {{
                    window.location.reload();
                }}, 3000);
            }}).catch(error => {{
                document.getElementById('gps-status').innerHTML = `
                    <div style="color: #dc2626; font-weight: bold;">
                        ❌ Submission Failed
                    </div>
                    <p style="color: #6b7280;">Please try again or contact support</p>
                `;
            }});
        }});
        </script>
        '''
        
        # Display the GPS component
        st.components.v1.html(gps_html, height=350)
        
        # Check for form submission
        if st.request is not None and st.request.method == "POST":
            try:
                # Get form data from POST request
                form_data = st.request.body.decode('utf-8')
                params = dict(pair.split('=') for pair in form_data.split('&') if '=' in pair)
                
                # Decode URL encoded values
                station_name_val = params.get('station_name', '').replace('+', ' ')
                owner_name_val = params.get('owner_name', '').replace('+', ' ')
                phone_val = params.get('phone', '')
                latitude_val = float(params.get('latitude', 0))
                longitude_val = float(params.get('longitude', 0))
                accuracy_val = float(params.get('accuracy', 0))
                
                # Save to database
                if station_name_val and owner_name_val and phone_val:
                    station_id = save_station_to_db(
                        station_name_val,
                        owner_name_val,
                        phone_val,
                        latitude_val,
                        longitude_val,
                        accuracy_val
                    )
                    
                    if station_id:
                        st.session_state.station_saved = True
                        st.session_state.station_id = station_id
                        st.rerun()
                    else:
                        st.error("Failed to save to database")
                else:
                    st.error("Missing required information")
                    
            except Exception as e:
                st.error(f"Error processing form: {e}")

# Footer
st.markdown("---")
st.caption("Station GPS Registration System • One-Step Registration • © 2024")

# Add CSS for better appearance
st.markdown("""
<style>
.stButton > button {
    transition: all 0.3s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

div[data-testid="stForm"] {
    background: transparent;
    border: none;
    padding: 0;
}
</style>
""", unsafe_allow_html=True)
