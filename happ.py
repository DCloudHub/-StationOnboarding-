"""
Station Onboarding System - AUTO-SAVE GPS with Admin Authentication
GPS automatically saves → Admin can view after login
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
if 'gps_data' not in st.session_state:
    st.session_state.gps_data = None
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
def create_admin_user(username, password, full_name):
    try:
        c = conn.cursor()
        password_hash, salt = hash_password(password)
        
        c.execute('''
            INSERT INTO admin_users (username, password_hash, salt, full_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password_hash, salt, full_name, datetime.now().isoformat()))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error creating user: {e}")
        return False

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

def change_admin_password(username, old_password, new_password):
    try:
        user = authenticate_user(username, old_password)
        if user:
            c = conn.cursor()
            new_hash, new_salt = hash_password(new_password)
            
            c.execute('''
                UPDATE admin_users 
                SET password_hash = ?, salt = ?
                WHERE username = ?
            ''', (new_hash, new_salt, username))
            
            conn.commit()
            return True
        return False
    except Exception as e:
        st.error(f"Password change error: {e}")
        return False

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

def update_station_status(station_id, status):
    """Update station status"""
    try:
        c = conn.cursor()
        c.execute('''
            UPDATE stations 
            SET status = ?
            WHERE station_id = ?
        ''', (status, station_id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Update error: {e}")
        return False

def delete_station(station_id):
    """Delete a station"""
    try:
        c = conn.cursor()
        c.execute('DELETE FROM stations WHERE station_id = ?', (station_id,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        st.error(f"Delete error: {e}")
        return False

# GPS Capture Component with proper communication
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
        
        <div id="streamlit-message" style="display: none;"></div>
    </div>
    
    <script>
    // Function to send data to Streamlit
    function sendToStreamlit(data) {
        const message = document.getElementById('streamlit-message');
        message.textContent = JSON.stringify(data);
        
        // Trigger Streamlit to read the message
        const event = new Event('gpsDataCaptured');
        message.dispatchEvent(event);
    }
    
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
                    
                    // Create GPS data object
                    const gpsData = {
                        latitude: lat,
                        longitude: lon,
                        accuracy: acc
                    };
                    
                    // Store in localStorage
                    localStorage.setItem('gps_coordinates', JSON.stringify(gpsData));
                    
                    // Send to Streamlit
                    sendToStreamlit(gpsData);
                    
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
    
    // Check for previously captured GPS on page load
    window.addEventListener('load', function() {
        const savedGPS = localStorage.getItem('gps_coordinates');
        if (savedGPS) {
            const gpsData = JSON.parse(savedGPS);
            const gpsStatus = document.getElementById('gps-status');
            const button = document.querySelector('button[onclick="captureGPS()"]');
            
            gpsStatus.innerHTML = `
                <div style="color: #059669; font-weight: bold;">
                    ✅ GPS ALREADY CAPTURED
                </div>
                <div style="background: #f0f9ff; padding: 15px; border-radius: 5px; margin-top: 10px;">
                    <div style="font-family: monospace;">
                        <strong>Latitude:</strong> ${gpsData.latitude.toFixed(6)}<br>
                        <strong>Longitude:</strong> ${gpsData.longitude.toFixed(6)}<br>
                        <strong>Accuracy:</strong> ±${gpsData.accuracy.toFixed(1)}m
                    </div>
                </div>
            `;
            
            button.innerHTML = '✅ LOCATION CAPTURED';
            button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
            
            // Send to Streamlit
            sendToStreamlit(gpsData);
        }
    });
    </script>
    '''
    
    return html_code

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
        
        # Change password
        with st.expander("Change Password"):
            with st.form("change_password_form"):
                old_pwd = st.text_input("Current Password", type="password")
                new_pwd = st.text_input("New Password", type="password")
                confirm_pwd = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("Update Password"):
                    if new_pwd != confirm_pwd:
                        st.error("New passwords don't match!")
                    elif len(new_pwd) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        if change_admin_password(st.session_state.username, old_pwd, new_pwd):
                            st.success("Password updated successfully!")
                        else:
                            st.error("Failed to update password. Check current password.")
        
        st.markdown("---")
        st.caption(f"Logged in: {st.session_state.username}")
    else:
        # Not logged in - show login form
        show_login_form()

# Check for GPS data from JavaScript
# Create a container for the GPS component
gps_container = st.empty()

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
        
        # Display all stations in a clean table
        st.subheader(f"All Station Submissions ({len(df)})")
        
        # Use Streamlit's dataframe with editing capability
        edited_df = st.data_editor(
            df[['ID', 'Name', 'Owner', 'Phone', 'Coordinates', 'Time', 'Status']],
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    help="Update station status",
                    options=["pending", "approved", "rejected"],
                    required=True,
                )
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )
        
        # Save changes button
        if st.button("💾 Save All Changes", type="primary", use_container_width=True):
            changes_made = False
            for index, row in edited_df.iterrows():
                original_status = df.iloc[index]['Status']
                if row['Status'] != original_status:
                    if update_station_status(row['ID'], row['Status']):
                        changes_made = True
            
            if changes_made:
                st.success("All changes saved successfully!")
                st.rerun()
            else:
                st.info("No changes to save")
        
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
                st.session_state.gps_data = None
                # Clear browser storage
                clear_js = """
                <script>
                localStorage.removeItem('gps_coordinates');
                </script>
                """
                st.components.v1.html(clear_js, height=0)
                st.rerun()
        with col2:
            if st.button("🏠 Return Home", use_container_width=True):
                st.session_state.station_saved = False
                st.session_state.station_id = None
                st.session_state.gps_data = None
                clear_js = """
                <script>
                localStorage.removeItem('gps_coordinates');
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
        
        # Use a custom HTML component to capture GPS data
        with gps_container:
            gps_result = html(gps_html, height=300)
        
        # Check if GPS data was captured (using a simpler approach)
        # We'll check for GPS data in the URL parameters
        query_params = st.query_params
        
        if 'gps_data' in query_params:
            try:
                gps_json = query_params['gps_data']
                st.session_state.gps_data = json.loads(gps_json)
                # Clear the parameter
                st.query_params.clear()
            except:
                pass
        
        # Also check for GPS data from localStorage via JavaScript
        check_gps_js = """
        <script>
        // Check if GPS data exists in localStorage
        const gpsData = localStorage.getItem('gps_coordinates');
        if (gpsData) {
            // Send to Streamlit via URL parameter
            const url = new URL(window.location);
            url.searchParams.set('gps_data', gpsData);
            window.history.replaceState({}, '', url);
            
            // Trigger a rerun
            setTimeout(() => {
                window.location.reload();
            }, 500);
        }
        </script>
        """
        
        st.components.v1.html(check_gps_js, height=0)
        
        # Show current GPS status
        if st.session_state.gps_data:
            st.info(f"""
            **✅ GPS Coordinates Captured:**
            - Latitude: {st.session_state.gps_data['latitude']:.6f}
            - Longitude: {st.session_state.gps_data['longitude']:.6f}
            - Accuracy: ±{st.session_state.gps_data.get('accuracy', 0):.1f}m
            
            **✓ You can now fill the station details below.**
            """)
        else:
            st.warning("⚠️ Please capture GPS location first before filling station details")
        
        # Station Details Form
        st.markdown("---")
        st.markdown("### 📝 Step 2: Enter Station Details")
        
        with st.form("station_form", clear_on_submit=True):
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
            
            # Validation
            gps_ready = st.session_state.gps_data is not None
            form_filled = all([station_name, owner_name, phone])
            
            # Status indicator
            if gps_ready:
                st.success("✅ GPS location captured - Form is ready!")
            else:
                st.error("❌ GPS location not captured yet")
            
            # Submit button - only enabled when GPS is ready
            submit_disabled = not gps_ready or not form_filled
            
            if submit_disabled and not gps_ready:
                button_label = "⛔ CAPTURE GPS FIRST"
                button_type = "secondary"
            elif submit_disabled:
                button_label = "⚠️ FILL ALL FIELDS"
                button_type = "secondary"
            else:
                button_label = "✅ SUBMIT STATION REGISTRATION"
                button_type = "primary"
            
            submitted = st.form_submit_button(
                button_label,
                type=button_type,
                use_container_width=True,
                disabled=submit_disabled
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
                    
                    # Clear localStorage
                    clear_js = """
                    <script>
                    localStorage.removeItem('gps_coordinates');
                    </script>
                    """
                    st.components.v1.html(clear_js, height=0)
                    
                    st.rerun()
                else:
                    st.error("Failed to save to database. Please try again.")
            elif submitted and not gps_ready:
                st.error("Please capture GPS location first by clicking the 'Capture GPS Location' button!")
        
        # Help section for users
        st.markdown("---")
        with st.expander("ℹ️ Need Help?"):
            st.markdown("""
            **Common Issues:**
            
            1. **GPS not working?**
               - Make sure location services are enabled on your device
               - Use a modern browser (Chrome, Firefox, Edge)
               - Try again in a different location
            
            2. **Form not submitting?**
               - Ensure all fields are filled
               - Make sure GPS location is captured (green checkmark)
               - Check your internet connection
            
            3. **Admin Access?**
               - Login using the sidebar (for authorized personnel only)
               - Contact system administrator for credentials
            
            **Contact Support:** support@stationregistration.com
            """)

# Footer
st.markdown("---")
st.caption("""
Station GPS Registration System • Auto-save GPS coordinates • 
[Login Required for Admin Access] • © 2024
""")

# JavaScript to handle GPS data communication
gps_communication_js = """
<script>
// Function to check for GPS data and update Streamlit
function updateGPSStatus() {
    const gpsData = localStorage.getItem('gps_coordinates');
    if (gpsData) {
        // Update URL to send data to Streamlit
        const url = new URL(window.location);
        if (!url.searchParams.has('gps_data')) {
            url.searchParams.set('gps_data', gpsData);
            window.history.replaceState({}, '', url);
            
            // Show a message that form is ready
            const gpsStatusElement = document.getElementById('gps-status');
            if (gpsStatusElement) {
                gpsStatusElement.innerHTML += `
                    <div style="color: #059669; margin-top: 10px; font-weight: bold;">
                        ✓ Form is now ready below!
                    </div>
                `;
            }
            
            // Small delay then reload to update Streamlit state
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }
}

// Check for GPS data periodically
setInterval(updateGPSStatus, 2000);

// Also check on page load
window.addEventListener('load', updateGPSStatus);
</script>
"""

# Add the communication JavaScript
st.components.v1.html(gps_communication_js, height=0)
