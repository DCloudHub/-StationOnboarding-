"""
Station Onboarding System - FINAL WORKING VERSION
MIT License - For production use
"""

import streamlit as st
import json
import base64
from datetime import datetime
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import io
import sqlite3
import csv
import hashlib
import pytz
import uuid
import re

# Page configuration
st.set_page_config(
    page_title="Station Onboarding",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
APP_VERSION = "4.0.0"
NIGERIA_TZ = pytz.timezone('Africa/Lagos')

# Nigerian Geopolitical Zones and States
NIGERIAN_REGIONS = {
    "North Central": ["Benue", "Kogi", "Kwara", "Nasarawa", "Niger", "Plateau", "FCT"],
    "North East": ["Adamawa", "Bauchi", "Borno", "Gombe", "Taraba", "Yobe"],
    "North West": ["Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Sokoto", "Zamfara"],
    "South East": ["Abia", "Anambra", "Ebonyi", "Enugu", "Imo"],
    "South South": ["Akwa Ibom", "Bayelsa", "Cross River", "Delta", "Edo", "Rivers"],
    "South West": ["Ekiti", "Lagos", "Ogun", "Ondo", "Osun", "Oyo"]
}

# Initialize session state - FIXED: Clear initialization
def init_session_state():
    defaults = {
        'consent_given': False,
        'current_step': 1,
        'client_data': {},
        'selected_zone': None,
        'selected_state': None,
        'photo_captured': None,
        'photo_metadata': None,
        'location_data': None,
        'admin_authenticated': False,
        'view_submissions': False,
        'gps_triggered': False,
        'location_captured': False,
        'gps_data_received': False,
        'submission_complete': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize session state
init_session_state()

# Custom CSS - FIXED: Clean CSS without errors
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .stButton button {
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .stButton button:hover {
        background-color: #1E40AF;
    }
    .consent-box {
        border: 2px solid #e5e7eb;
        border-radius: 10px;
        padding: 2rem;
        background-color: #f9fafb;
        margin: 2rem 0;
    }
    .location-group {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: #f9fafb;
    }
    .gps-success {
        background-color: #d1fae5;
        border: 2px solid #10b981;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .gps-waiting {
        background-color: #fef3c7;
        border: 2px solid #f59e0b;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .gps-error {
        background-color: #fee2e2;
        border: 2px solid #ef4444;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .gps-instructions {
        background-color: #eff6ff;
        border: 2px solid #3b82f6;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .gps-coordinates {
        font-family: 'Courier New', monospace;
        font-size: 1.2rem;
        background-color: #1f2937;
        color: #10b981;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
        text-align: center;
    }
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin-bottom: 2rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 10px;
    }
    .step {
        text-align: center;
        flex: 1;
        padding: 10px;
        font-weight: bold;
    }
    .step.active {
        background-color: #1E3A8A;
        color: white;
        border-radius: 5px;
    }
    .coordinate-display {
        font-family: monospace;
        font-size: 1.1rem;
        background: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Database setup - FIXED: Proper table structure
def init_database():
    conn = sqlite3.connect('submissions.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id TEXT UNIQUE,
            full_name TEXT,
            email TEXT,
            phone TEXT,
            geopolitical_zone TEXT,
            state TEXT,
            lga TEXT,
            address TEXT,
            latitude REAL,
            longitude REAL,
            submission_timestamp TEXT,
            status TEXT DEFAULT 'pending',
            photo_timestamp TEXT,
            photo_latitude REAL,
            photo_longitude REAL,
            photo_data BLOB,
            station_name TEXT,
            station_type TEXT,
            location_source TEXT,
            accuracy REAL
        )
    ''')
    
    conn.commit()
    return conn

DB_CONN = init_database()

def save_submission_to_db(submission_data, photo_bytes=None, photo_metadata=None):
    try:
        c = DB_CONN.cursor()
        
        submission_data_with_meta = submission_data.copy()
        
        # Add photo metadata if available
        if photo_metadata:
            submission_data_with_meta['photo_timestamp'] = photo_metadata.get('timestamp')
            
            photo_lat = photo_metadata.get('latitude')
            if photo_lat is not None:
                try:
                    submission_data_with_meta['photo_latitude'] = float(photo_lat)
                except (ValueError, TypeError):
                    submission_data_with_meta['photo_latitude'] = None
            
            photo_lon = photo_metadata.get('longitude')
            if photo_lon is not None:
                try:
                    submission_data_with_meta['photo_longitude'] = float(photo_lon)
                except (ValueError, TypeError):
                    submission_data_with_meta['photo_longitude'] = None
        
        # Prepare all values
        values = (
            submission_data_with_meta.get('submission_id'),
            submission_data_with_meta.get('full_name'),
            submission_data_with_meta.get('email'),
            submission_data_with_meta.get('phone'),
            submission_data_with_meta.get('geopolitical_zone'),
            submission_data_with_meta.get('state'),
            submission_data_with_meta.get('lga'),
            submission_data_with_meta.get('address', ''),
            submission_data_with_meta.get('latitude'),
            submission_data_with_meta.get('longitude'),
            submission_data_with_meta.get('submission_timestamp'),
            'pending',  # status
            submission_data_with_meta.get('photo_timestamp'),
            submission_data_with_meta.get('photo_latitude'),
            submission_data_with_meta.get('photo_longitude'),
            photo_bytes,
            submission_data_with_meta.get('station_name', ''),
            submission_data_with_meta.get('station_type', ''),
            submission_data_with_meta.get('location_source', 'manual'),
            submission_data_with_meta.get('accuracy')
        )
        
        c.execute('''
            INSERT INTO submissions (
                submission_id, full_name, email, phone, geopolitical_zone, state, lga, address,
                latitude, longitude, submission_timestamp, status,
                photo_timestamp, photo_latitude, photo_longitude, photo_data,
                station_name, station_type, location_source, accuracy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', values)
        
        DB_CONN.commit()
        return True
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return False

def get_all_submissions():
    """Get all submissions including GPS coordinates - FIXED"""
    try:
        c = DB_CONN.cursor()
        c.execute('''
            SELECT id, submission_id, full_name, email, phone, geopolitical_zone, state,
                   latitude, longitude, accuracy, submission_timestamp, status,
                   location_source, photo_latitude, photo_longitude
            FROM submissions 
            ORDER BY submission_timestamp DESC
        ''')
        rows = c.fetchall()
        return rows
    except Exception as e:
        st.error(f"Error fetching submissions: {str(e)}")
        return []

# Step indicator
def show_step_indicator():
    steps = ["Consent", "Information", "Photo", "Location", "Review"]
    
    html = """
    <div class="step-indicator">
    """
    
    for i, step in enumerate(steps, 1):
        is_active = i == st.session_state.current_step
        active_class = "active" if is_active else ""
        html += f"""
        <div class="step {active_class}">
            <div style="font-size: 1.5rem; margin-bottom: 5px;">{i}</div>
            <div style="font-size: 0.9rem;">{step}</div>
        </div>
        """
    
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# GPS Function using JavaScript - FIXED: Proper data handling
def get_gps_coordinates():
    """Get GPS coordinates using JavaScript"""
    
    st.markdown("""
    <div class="gps-instructions">
    <h3>📍 Automatic GPS Location Capture</h3>
    <p><strong>Instructions:</strong></p>
    <ol>
        <li>Click the button below</li>
        <li>Allow location access when browser asks</li>
        <li>Wait for coordinates to appear</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)
    
    # Button to trigger GPS
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📍 GET GPS LOCATION", 
                    key="gps_button",
                    type="primary", 
                    use_container_width=True):
            st.session_state.gps_triggered = True
            st.rerun()
    
    # If GPS was triggered, show the component
    if st.session_state.get('gps_triggered'):
        # Create GPS component
        gps_js = """
        <div id="gps-container">
            <div id="gps-status" style="padding: 20px; text-align: center;">
                <div style="color: orange; font-weight: bold;">⏳ Requesting GPS coordinates...</div>
                <p>Please allow location access when prompted by your browser</p>
            </div>
        </div>
        
        <script>
        function getGPSLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const data = {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            accuracy: position.coords.accuracy,
                            altitude: position.coords.altitude,
                            altitudeAccuracy: position.coords.altitudeAccuracy,
                            heading: position.coords.heading,
                            speed: position.coords.speed,
                            timestamp: new Date().toISOString(),
                            success: true
                        };
                        
                        // Send to Streamlit via query params
                        const params = new URLSearchParams(window.location.search);
                        params.set('gps_lat', data.latitude);
                        params.set('gps_lon', data.longitude);
                        params.set('gps_acc', data.accuracy);
                        params.set('gps_time', data.timestamp);
                        
                        // Update URL without reloading
                        const newUrl = window.location.pathname + '?' + params.toString();
                        window.history.replaceState({}, '', newUrl);
                        
                        // Show success
                        document.getElementById('gps-status').innerHTML = 
                            '<div style="color: green; font-weight: bold;">✅ GPS Location Captured!</div>' +
                            '<div style="font-family: monospace; background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px;">' +
                            'Latitude: ' + data.latitude.toFixed(6) + '<br>' +
                            'Longitude: ' + data.longitude.toFixed(6) + '<br>' +
                            'Accuracy: ±' + data.accuracy.toFixed(1) + ' meters' +
                            '</div>';
                    },
                    function(error) {
                        let errorMsg = "Unknown error";
                        switch(error.code) {
                            case 1: errorMsg = "Permission denied. Please allow location access."; break;
                            case 2: errorMsg = "Position unavailable. Check your location settings."; break;
                            case 3: errorMsg = "Request timeout. Please try again."; break;
                        }
                        
                        document.getElementById('gps-status').innerHTML = 
                            '<div style="color: red; font-weight: bold;">❌ ' + errorMsg + '</div>' +
                            '<button onclick="getGPSLocation()" style="padding: 10px 20px; margin-top: 10px; background: #1E3A8A; color: white; border: none; border-radius: 5px; cursor: pointer;">Try Again</button>';
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 15000,
                        maximumAge: 0
                    }
                );
            } else {
                document.getElementById('gps-status').innerHTML = 
                    '<div style="color: red; font-weight: bold;">❌ Geolocation not supported by this browser.</div>';
            }
        }
        
        // Start GPS when page loads
        window.onload = function() {
            getGPSLocation();
        };
        </script>
        """
        
        # Display JavaScript component
        st.components.v1.html(gps_js, height=200)
        
        # Check query params for GPS data
        query_params = st.query_params
        
        # Try to get GPS data from query params
        gps_lat = query_params.get("gps_lat", [None])[0]
        gps_lon = query_params.get("gps_lon", [None])[0]
        gps_acc = query_params.get("gps_acc", [None])[0]
        
        if gps_lat and gps_lon:
            try:
                latitude = float(gps_lat)
                longitude = float(gps_lon)
                accuracy = float(gps_acc) if gps_acc else None
                
                # Save to session state
                st.session_state.location_data = {
                    'latitude': latitude,
                    'longitude': longitude,
                    'accuracy': accuracy,
                    'timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                    'source': 'gps',
                    'success': True
                }
                
                st.session_state.gps_data_received = True
                
                # Show success message
                st.markdown(f"""
                <div class="gps-success">
                <h3>✅ GPS Coordinates Captured!</h3>
                <div class="gps-coordinates">
                Latitude: {latitude:.6f}<br>
                Longitude: {longitude:.6f}<br>
                Accuracy: ±{accuracy:.1f} meters
                </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Auto-refresh to update state
                st.rerun()
                
            except (ValueError, TypeError) as e:
                st.error(f"Error parsing GPS data: {e}")

# Main App Header - FIXED: No error below header
st.markdown('<h1 class="main-header">⛽ Station Onboarding System</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #4B5563; margin-bottom: 2rem;">Register your filling station in 5 simple steps</p>', unsafe_allow_html=True)

# Admin Login
with st.sidebar:
    if not st.session_state.admin_authenticated:
        st.markdown("### Admin Login")
        admin_user = st.text_input("Username", key="admin_user")
        admin_pass = st.text_input("Password", type="password", key="admin_pass")
        
        if st.button("Login", key="admin_login"):
            if admin_user == "admin" and admin_pass == "admin123":
                st.session_state.admin_authenticated = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        st.success("Admin logged in")
        if st.button("📊 View Submissions", key="view_submissions_btn"):
            st.session_state.view_submissions = True
            st.rerun()
        if st.button("Logout", key="admin_logout"):
            st.session_state.admin_authenticated = False
            st.session_state.view_submissions = False
            st.rerun()

# Main App Flow
if st.session_state.admin_authenticated and st.session_state.view_submissions:
    st.markdown("## 📊 Admin Dashboard - Station Registrations")
    
    # Get submissions with GPS data
    submissions = get_all_submissions()
    
    if submissions:
        # Create DataFrame with ALL columns including GPS
        df = pd.DataFrame(submissions, columns=[
            'ID', 'Submission ID', 'Owner Name', 'Email', 'Phone', 'Zone', 'State',
            'Latitude', 'Longitude', 'Accuracy', 'Submission Time', 'Status',
            'Location Source', 'Photo Lat', 'Photo Lon'
        ])
        
        # Format timestamp
        if 'Submission Time' in df.columns:
            df['Submission Time'] = pd.to_datetime(df['Submission Time']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Format coordinates for display
        if 'Latitude' in df.columns and 'Longitude' in df.columns:
            df['Coordinates'] = df.apply(
                lambda row: f"{row['Latitude']:.6f}, {row['Longitude']:.6f}" 
                if pd.notna(row['Latitude']) and pd.notna(row['Longitude']) 
                else "Not Available",
                axis=1
            )
        
        # Format photo coordinates
        if 'Photo Lat' in df.columns and 'Photo Lon' in df.columns:
            df['Photo Coordinates'] = df.apply(
                lambda row: f"{row['Photo Lat']:.6f}, {row['Photo Lon']:.6f}" 
                if pd.notna(row['Photo Lat']) and pd.notna(row['Photo Lon']) 
                else "Not Available",
                axis=1
            )
        
        # Display the dataframe
        display_cols = ['Submission ID', 'Owner Name', 'Phone', 'Zone', 'State', 
                       'Coordinates', 'Submission Time', 'Status', 'Location Source']
        
        st.dataframe(df[display_cols], use_container_width=True)
        
        # Show detailed view
        with st.expander("📋 View Detailed Data"):
            st.dataframe(df, use_container_width=True)
        
        # Export functionality
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export to CSV", key="export_csv"):
                csv_data = df.to_csv(index=False)
                b64 = base64.b64encode(csv_data.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="station_registrations.csv">Download CSV File</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            if st.button("📊 View Statistics", key="view_stats"):
                st.markdown("### 📈 Registration Statistics")
                
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                
                with col_stats1:
                    st.metric("Total Registrations", len(df))
                
                with col_stats2:
                    gps_count = df[df['Location Source'] == 'gps'].shape[0]
                    st.metric("GPS Captures", gps_count)
                
                with col_stats3:
                    pending_count = df[df['Status'] == 'pending'].shape[0]
                    st.metric("Pending", pending_count)
                
                # Zone distribution
                st.markdown("#### Zone Distribution")
                zone_dist = df['Zone'].value_counts()
                st.bar_chart(zone_dist)
    
    else:
        st.info("No station registrations yet")
    
    if st.button("← Back to Registration Form", key="back_to_form"):
        st.session_state.view_submissions = False
        st.rerun()

else:
    # Show step indicator
    show_step_indicator()
    
    # Step 1: Consent
    if st.session_state.current_step == 1:
        st.markdown("### Step 1: Consent & Agreement")
        
        with st.expander("📋 Read Complete Terms & Conditions", expanded=True):
            st.markdown("""
            ## Filling Station Registration Consent
            By checking the consent box below, you agree to ALL of the following:
            
            ### 1. Station Photo Capture Consent
            - You consent to capture photos of your filling station
            - Photos will be timestamped for verification
            
            ### 2. Location Data Consent  
            - You consent to share your station's precise location coordinates
            - Location data will be used for mapping and service planning
            
            ### 3. Business Information Consent
            - You consent to provide business owner information
            - This information will be used for official registration
            """)
        
        st.markdown('<div class="consent-box">', unsafe_allow_html=True)
        consent_all = st.checkbox(
            "✅ **I consent to ALL of the above terms and conditions**",
            help="Check this box to give your consent",
            key="consent_checkbox"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Continue to Step 2", type="primary", use_container_width=True, key="step1_continue"):
                if consent_all:
                    st.session_state.consent_given = True
                    st.session_state.current_step = 2
                    st.rerun()
                else:
                    st.error("⚠️ You must give your consent to proceed")
    
    # Step 2: Station Information
    elif st.session_state.current_step == 2:
        st.markdown("### Step 2: Station & Owner Information")
        
        # Owner Information
        st.markdown("#### 👤 Owner Information")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", 
                               placeholder="Enter owner's full name",
                               key="owner_name")
            email = st.text_input("Email Address *", 
                                placeholder="owner@station.com",
                                key="owner_email")
        with col2:
            phone = st.text_input("Phone Number *", 
                                placeholder="08012345678",
                                key="owner_phone")
        
        # Station Details
        st.markdown("#### ⛽ Station Details")
        station_name = st.text_input("Station Name *", 
                                   placeholder="e.g., Mega Fuel Station",
                                   key="station_name")
        station_type = st.selectbox("Station Type *", 
                                  ["Petrol Station", "Gas Station", "Diesel Depot", "Multi-Fuel Station"],
                                  key="station_type")
        
        # Location Information
        st.markdown('<div class="location-group">', unsafe_allow_html=True)
        st.markdown("#### 📍 Station Location")
        
        zone = st.selectbox("Geopolitical Zone *", 
                          list(NIGERIAN_REGIONS.keys()), 
                          index=None,
                          placeholder="Select zone",
                          key="geo_zone")
        
        state_options = NIGERIAN_REGIONS[zone] if zone else []
        state = st.selectbox("State *", 
                           state_options, 
                           disabled=not zone,
                           placeholder="Select state" if zone else "Select zone first",
                           key="state_select")
        
        lga = st.text_input("Local Government Area (LGA) *", 
                          placeholder="e.g., Ikeja, Surulere",
                          key="lga_input")
        st.markdown('</div>', unsafe_allow_html=True)
        
        address = st.text_area("Detailed Station Address", 
                             placeholder="Enter complete station address with landmarks",
                             height=100,
                             key="address_input")
        
        # Validation
        required_fields = all([name, email, phone, station_name, station_type, zone, state, lga])
        
        # Navigation
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Back to Consent", use_container_width=True, key="step2_back"):
                st.session_state.current_step = 1
                st.rerun()
        
        with col_next:
            if st.button("Continue to Photo →", type="primary", disabled=not required_fields, 
                        use_container_width=True, key="step2_continue"):
                st.session_state.client_data.update({
                    'full_name': name, 
                    'email': email, 
                    'phone': phone,
                    'station_name': station_name, 
                    'station_type': station_type,
                    'geopolitical_zone': zone, 
                    'state': state, 
                    'lga': lga, 
                    'address': address
                })
                st.session_state.current_step = 3
                st.rerun()
        
        if not required_fields:
            st.warning("⚠️ Please fill all required fields (marked with *)")
    
    # Step 3: Station Photo
    elif st.session_state.current_step == 3:
        st.markdown("### Step 3: Station Photo Capture")
        st.info("📸 Capture a clear photo of your station's front view")
        
        photo = st.camera_input("Take a photo of your station", key="station_photo")
        
        if photo:
            st.session_state.photo_captured = photo
            st.session_state.photo_metadata = {
                'timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                'source': 'camera'
            }
            st.success("✅ Photo captured successfully!")
            st.image(photo, caption="Station Photo Preview", use_column_width=True)
        
        # Navigation
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Back to Information", use_container_width=True, key="step3_back"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col_next:
            photo_ready = st.session_state.photo_captured is not None
            if st.button("Continue to Location →", type="primary", disabled=not photo_ready, 
                        use_container_width=True, key="step3_continue"):
                st.session_state.current_step = 4
                st.rerun()
        
        if not photo_ready:
            st.warning("⚠️ Please capture a station photo to continue")
    
    # Step 4: Location Capture
    elif st.session_state.current_step == 4:
        st.markdown("### Step 4: Location Capture")
        
        # Show current location if already captured
        if st.session_state.location_data and st.session_state.location_data.get('success'):
            st.markdown('<div class="gps-success">', unsafe_allow_html=True)
            st.success("✅ GPS Location Captured!")
            lat = st.session_state.location_data['latitude']
            lon = st.session_state.location_data['longitude']
            acc = st.session_state.location_data.get('accuracy', 0)
            st.markdown(f"""
            <div class="gps-coordinates">
            Latitude: {lat:.6f}<br>
            Longitude: {lon:.6f}<br>
            Accuracy: ±{acc:.1f} meters
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Manual override option
            with st.expander("📝 Manual Override (if GPS is wrong)"):
                col_lat, col_lon = st.columns(2)
                with col_lat:
                    manual_lat = st.text_input("Manual Latitude", 
                                             value=f"{lat:.6f}",
                                             key="manual_lat_override")
                with col_lon:
                    manual_lon = st.text_input("Manual Longitude", 
                                             value=f"{lon:.6f}",
                                             key="manual_lon_override")
                
                if st.button("Update Coordinates", key="update_coords"):
                    try:
                        new_lat = float(manual_lat)
                        new_lon = float(manual_lon)
                        st.session_state.location_data['latitude'] = new_lat
                        st.session_state.location_data['longitude'] = new_lon
                        st.session_state.location_data['source'] = 'manual_override'
                        st.success("Coordinates updated!")
                        st.rerun()
                    except ValueError:
                        st.error("Invalid coordinates")
        else:
            # Show GPS capture
            get_gps_coordinates()
            
            # Manual fallback if GPS fails
            if st.session_state.gps_triggered and not st.session_state.gps_data_received:
                st.markdown('<div class="gps-error">', unsafe_allow_html=True)
                st.error("GPS capture failed. Please try again or use manual entry.")
                st.markdown('</div>', unsafe_allow_html=True)
                
                with st.expander("📝 Manual Coordinate Entry"):
                    col_lat, col_lon = st.columns(2)
                    with col_lat:
                        manual_lat = st.text_input("Latitude", 
                                                 placeholder="e.g., 6.5244",
                                                 key="manual_lat")
                    with col_lon:
                        manual_lon = st.text_input("Longitude", 
                                                 placeholder="e.g., 3.3792",
                                                 key="manual_lon")
                    
                    if st.button("Use Manual Coordinates", key="use_manual"):
                        try:
                            lat = float(manual_lat)
                            lon = float(manual_lon)
                            st.session_state.location_data = {
                                'latitude': lat,
                                'longitude': lon,
                                'timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                                'source': 'manual',
                                'success': True
                            }
                            st.success("Manual coordinates saved!")
                            st.rerun()
                        except ValueError:
                            st.error("Please enter valid coordinates")
        
        # Navigation
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Back to Photo", use_container_width=True, key="step4_back"):
                st.session_state.current_step = 3
                st.rerun()
        
        with col_next:
            # Check if we have location data
            has_location = (st.session_state.location_data is not None and 
                          st.session_state.location_data.get('success'))
            
            if st.button("Continue to Review →", type="primary", disabled=not has_location, 
                        use_container_width=True, key="step4_continue"):
                # Save location data to client_data
                if has_location:
                    st.session_state.client_data['location_source'] = st.session_state.location_data['source']
                    st.session_state.client_data['latitude'] = st.session_state.location_data['latitude']
                    st.session_state.client_data['longitude'] = st.session_state.location_data['longitude']
                    st.session_state.client_data['accuracy'] = st.session_state.location_data.get('accuracy')
                
                st.session_state.current_step = 5
                st.rerun()
        
        if not has_location:
            st.warning("⚠️ Please capture GPS location to continue")
    
    # Step 5: Review and Submit
    elif st.session_state.current_step == 5:
        st.markdown("### Step 5: Review & Submit")
        
        # Display summary
        st.markdown("#### 📋 Registration Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**👤 Owner Information**")
            st.write(f"**Name:** {st.session_state.client_data.get('full_name', 'N/A')}")
            st.write(f"**Email:** {st.session_state.client_data.get('email', 'N/A')}")
            st.write(f"**Phone:** {st.session_state.client_data.get('phone', 'N/A')}")
            
            st.markdown("**⛽ Station Details**")
            st.write(f"**Station Name:** {st.session_state.client_data.get('station_name', 'N/A')}")
            st.write(f"**Station Type:** {st.session_state.client_data.get('station_type', 'N/A')}")
        
        with col2:
            st.markdown("**📍 Location Information**")
            st.write(f"**Zone:** {st.session_state.client_data.get('geopolitical_zone', 'N/A')}")
            st.write(f"**State:** {st.session_state.client_data.get('state', 'N/A')}")
            st.write(f"**LGA:** {st.session_state.client_data.get('lga', 'N/A')}")
            
            if st.session_state.client_data.get('latitude'):
                lat = st.session_state.client_data['latitude']
                lon = st.session_state.client_data['longitude']
                acc = st.session_state.client_data.get('accuracy', 'N/A')
                source = st.session_state.client_data.get('location_source', 'unknown')
                
                st.markdown(f"""
                **GPS Coordinates:**
                <div class="coordinate-display">
                Latitude: {lat:.6f}<br>
                Longitude: {lon:.6f}<br>
                Accuracy: {acc if isinstance(acc, str) else f'±{acc:.1f}m'}<br>
                Source: {source.replace('_', ' ').title()}
                </div>
                """, unsafe_allow_html=True)
            elif st.session_state.client_data.get('address'):
                st.write(f"**Address:** {st.session_state.client_data['address']}")
        
        # Photo preview
        if st.session_state.photo_captured:
            st.markdown("**📸 Station Photo:**")
            st.image(st.session_state.photo_captured, width=300)
        
        # Final submission
        st.markdown("---")
        st.markdown("### ✅ Ready to Submit")
        
        agree_final = st.checkbox("**I confirm all information is correct and complete**", 
                                 key="final_confirmation")
        
        col_prev, col_submit = st.columns(2)
        with col_prev:
            if st.button("← Back to Location", use_container_width=True, key="step5_back"):
                st.session_state.current_step = 4
                st.rerun()
        
        with col_submit:
            if st.button("Submit Registration", type="primary", disabled=not agree_final, 
                        use_container_width=True, key="submit_registration"):
                try:
                    # Generate submission ID
                    submission_id = f"STN-{uuid.uuid4().hex[:8].upper()}"
                    
                    # Prepare complete submission data with GPS
                    submission_data = {
                        'submission_id': submission_id,
                        'full_name': st.session_state.client_data.get('full_name'),
                        'email': st.session_state.client_data.get('email'),
                        'phone': st.session_state.client_data.get('phone'),
                        'geopolitical_zone': st.session_state.client_data.get('geopolitical_zone'),
                        'state': st.session_state.client_data.get('state'),
                        'lga': st.session_state.client_data.get('lga'),
                        'address': st.session_state.client_data.get('address', ''),
                        'latitude': st.session_state.client_data.get('latitude'),
                        'longitude': st.session_state.client_data.get('longitude'),
                        'accuracy': st.session_state.client_data.get('accuracy'),
                        'submission_timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                        'station_name': st.session_state.client_data.get('station_name'),
                        'station_type': st.session_state.client_data.get('station_type'),
                        'location_source': st.session_state.client_data.get('location_source', 'manual')
                    }
                    
                    # Convert photo to bytes
                    photo_bytes = None
                    if st.session_state.photo_captured:
                        photo_bytes = st.session_state.photo_captured.getvalue()
                    
                    # Save to database
                    success = save_submission_to_db(submission_data, photo_bytes, st.session_state.photo_metadata)
                    
                    if success:
                        st.success(f"""
                        ## ✅ Registration Successful!
                        
                        **Your Submission ID:** `{submission_id}`
                        
                        Please save this ID for future reference.
                        """)
                        
                        # Reset session state for new registration
                        keys_to_keep = ['admin_authenticated', 'view_submissions']
                        new_state = {}
                        for key in keys_to_keep:
                            if key in st.session_state:
                                new_state[key] = st.session_state[key]
                        
                        # Clear session state
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        
                        # Restore admin state
                        for key, value in new_state.items():
                            st.session_state[key] = value
                        
                        # Set initial state
                        st.session_state.current_step = 1
                        st.session_state.consent_given = False
                        st.session_state.client_data = {}
                        
                        st.balloons()
                        
                        # Add button to start new registration
                        if st.button("Start New Registration", type="primary", use_container_width=True):
                            st.rerun()
                    else:
                        st.error("❌ Failed to save registration. Please try again.")
                
                except Exception as e:
                    st.error(f"❌ Error during submission: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    f'<div style="text-align: center; color: #6b7280; font-size: 0.9rem; margin-top: 2rem;">'
    f'Station Onboarding System v{APP_VERSION} • © 2024 • For Official Use Only'
    f'</div>',
    unsafe_allow_html=True
)
