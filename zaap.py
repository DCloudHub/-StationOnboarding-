"""
Station Onboarding System - GPS FIXED VERSION
MIT License - For production use
"""

import streamlit as st
from streamlit_geolocation import streamlit_geolocation
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

# Page configuration
st.set_page_config(
    page_title="Station Onboarding",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
APP_VERSION = "3.0.0"
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

# Initialize session state
if 'consent_given' not in st.session_state:
    st.session_state.consent_given = False
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'client_data' not in st.session_state:
    st.session_state.client_data = {}
if 'selected_zone' not in st.session_state:
    st.session_state.selected_zone = None
if 'selected_state' not in st.session_state:
    st.session_state.selected_state = None
if 'photo_captured' not in st.session_state:
    st.session_state.photo_captured = None
if 'photo_metadata' not in st.session_state:
    st.session_state.photo_metadata = None
if 'location_data' not in st.session_state:
    st.session_state.location_data = None
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'view_submissions' not in st.session_state:
    st.session_state.view_submissions = False
if 'gps_triggered' not in st.session_state:
    st.session_state.gps_triggered = False

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .step-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 2rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
    }
    .step-item {
        text-align: center;
        flex: 1;
        padding: 10px;
        position: relative;
    }
    .step-item.active {
        background-color: #1E3A8A;
        color: white;
        border-radius: 5px;
    }
    .step-number {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 5px;
        display: inline-block;
        width: 30px;
        height: 30px;
        line-height: 30px;
        border-radius: 50%;
        background-color: #e5e7eb;
        color: #6b7280;
    }
    .step-item.active .step-number {
        background-color: white;
        color: #1E3A8A;
    }
    .step-label {
        font-size: 0.9rem;
        margin-top: 5px;
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
    .station-icon {
        font-size: 3rem;
        text-align: center;
        margin-bottom: 1rem;
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
    .big-button {
        padding: 20px 40px !important;
        font-size: 1.2rem !important;
        border-radius: 10px !important;
        margin: 20px 0 !important;
    }
    .gps-coordinates {
        font-family: monospace;
        font-size: 1.1rem;
        background-color: #1f2937;
        color: #10b981;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Database setup
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
            location_source TEXT DEFAULT 'manual'
        )
    ''')
    
    conn.commit()
    return conn

DB_CONN = init_database()

def save_submission_to_db(submission_data, photo_bytes=None, photo_metadata=None):
    try:
        c = DB_CONN.cursor()
        
        submission_data_with_meta = submission_data.copy()
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
        
        c.execute('''
            INSERT INTO submissions (
                submission_id, full_name, email, phone, geopolitical_zone, state, lga, address,
                latitude, longitude, submission_timestamp, status,
                photo_timestamp, photo_latitude, photo_longitude, photo_data,
                station_name, station_type, location_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
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
            'pending',
            submission_data_with_meta.get('photo_timestamp'),
            submission_data_with_meta.get('photo_latitude'),
            submission_data_with_meta.get('photo_longitude'),
            photo_bytes,
            submission_data_with_meta.get('station_name', ''),
            submission_data_with_meta.get('station_type', ''),
            submission_data_with_meta.get('location_source', 'manual')
        ))
        
        DB_CONN.commit()
        return True
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return False

def get_all_submissions():
    try:
        c = DB_CONN.cursor()
        c.execute('''
            SELECT id, submission_id, full_name, email, phone, geopolitical_zone, state,
                   photo_timestamp, photo_latitude, photo_longitude, submission_timestamp, status,
                   location_source
            FROM submissions 
            ORDER BY submission_timestamp DESC
        ''')
        return c.fetchall()
    except:
        return []

# Step indicator function
def show_step_indicator_simple():
    steps = ["Consent", "Information", "Station Photo", "Location", "Review"]
    
    cols = st.columns(5)
    for i, (col, step_name) in enumerate(zip(cols, steps), 1):
        with col:
            is_active = i == st.session_state.current_step
            bg_color = "#1E3A8A" if is_active else "#e5e7eb"
            text_color = "white" if is_active else "#6b7280"
            
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; border-radius: 5px; 
                        background-color: {bg_color}; color: {text_color}; font-weight: bold;">
                <div style="font-size: 1.2rem;">{i}</div>
                <div style="font-size: 0.9rem;">{step_name}</div>
            </div>
            """, unsafe_allow_html=True)

# SIMPLE GPS FUNCTION USING streamlit-geolocation
def get_gps_simple():
    """Simple reliable GPS function"""
    st.markdown('<div class="gps-instructions">', unsafe_allow_html=True)
    st.markdown("### 📍 How to Get GPS Coordinates:")
    st.markdown("""
    1. **Make sure location is ON** on your device
    2. Click the button below
    3. **Allow location access** when browser asks
    4. Wait 5-10 seconds for coordinates
    5. If it fails, try:
       - Refresh the page
       - Use a different browser (Chrome works best)
       - Go outside for better signal
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Create a button to trigger GPS
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📍 GET MY LOCATION NOW", key="get_gps_main", type="primary", use_container_width=True):
            st.session_state.gps_triggered = True
            st.rerun()
    
    # If GPS was triggered, show the component
    if st.session_state.get('gps_triggered'):
        st.markdown('<div class="gps-waiting">', unsafe_allow_html=True)
        st.info("🔄 Requesting your location... Please allow location access when prompted by your browser.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Use streamlit-geolocation package
        location = streamlit_geolocation()
        
        if location:
            if 'latitude' in location and location['latitude']:
                st.session_state.location_data = {
                    'latitude': location['latitude'],
                    'longitude': location['longitude'],
                    'timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                    'source': 'gps'
                }
                
                st.markdown('<div class="gps-success">', unsafe_allow_html=True)
                st.success("✅ Location captured successfully!")
                st.markdown(f"""
                **Coordinates:**
                <div class="gps-coordinates">
                Latitude:  {location['latitude']:.6f}
                Longitude: {location['longitude']:.6f}
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Show on map
                try:
                    import folium
                    from streamlit_folium import folium_static
                    
                    m = folium.Map(location=[location['latitude'], location['longitude']], zoom_start=16)
                    folium.Marker(
                        [location['latitude'], location['longitude']],
                        popup="Your Station Location",
                        tooltip="Click for details",
                        icon=folium.Icon(color="green", icon="gas-pump", prefix="fa")
                    ).add_to(m)
                    
                    folium_static(m, width=700, height=400)
                except:
                    pass  # Map is optional
            else:
                st.markdown('<div class="gps-error">', unsafe_allow_html=True)
                st.error("❌ Could not get location. Please try manual entry or check device settings.")
                st.markdown('</div>', unsafe_allow_html=True)

# Alternative: Manual GPS input
def get_gps_manual():
    """Manual GPS entry as fallback"""
    st.markdown("### 📍 Manual Location Entry")
    
    col1, col2 = st.columns(2)
    with col1:
        manual_lat = st.text_input("Latitude", 
                                  placeholder="e.g., 9.0765 for Lagos",
                                  key="manual_lat")
    with col2:
        manual_lon = st.text_input("Longitude", 
                                  placeholder="e.g., 7.3986 for Abuja",
                                  key="manual_lon")
    
    # Nigerian city coordinates for reference
    st.markdown("#### Common Nigerian City Coordinates:")
    cities = {
        "Lagos": {"lat": 6.5244, "lon": 3.3792},
        "Abuja": {"lat": 9.0765, "lon": 7.3986},
        "Kano": {"lat": 12.0022, "lon": 8.5922},
        "Port Harcourt": {"lat": 4.8156, "lon": 7.0498},
        "Ibadan": {"lat": 7.3775, "lon": 3.9470},
        "Benin City": {"lat": 6.3350, "lon": 5.6037}
    }
    
    selected_city = st.selectbox("Quick select a city:", 
                                ["Select a city..."] + list(cities.keys()))
    
    if selected_city and selected_city != "Select a city...":
        city_data = cities[selected_city]
        manual_lat = str(city_data['lat'])
        manual_lon = str(city_data['lon'])
        st.info(f"Using coordinates for {selected_city}")
    
    if manual_lat and manual_lon:
        try:
            lat = float(manual_lat)
            lon = float(manual_lon)
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                st.session_state.location_data = {
                    'latitude': lat,
                    'longitude': lon,
                    'timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                    'source': 'manual'
                }
                st.success(f"✅ Coordinates set: {lat:.6f}, {lon:.6f}")
            else:
                st.error("Invalid coordinates. Latitude must be between -90 and 90, Longitude between -180 and 180")
        except ValueError:
            st.error("Please enter valid numbers for coordinates")

# Main App Header
st.markdown('<h1 class="main-header">⛽ Station Onboarding System</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #4B5563; margin-bottom: 2rem;">Register your filling station in 5 simple steps</p>', unsafe_allow_html=True)

# Admin Login (same as before)
with st.sidebar:
    if not st.session_state.admin_authenticated:
        st.markdown("### Admin Login")
        admin_user = st.text_input("Username")
        admin_pass = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if admin_user == "admin" and admin_pass == "admin123":
                st.session_state.admin_authenticated = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        st.success("Admin logged in")
        if st.button("📊 View Submissions"):
            st.session_state.view_submissions = True
            st.rerun()
        if st.button("Logout"):
            st.session_state.admin_authenticated = False
            st.session_state.view_submissions = False
            st.rerun()

# Main App Flow
if st.session_state.admin_authenticated and st.session_state.view_submissions:
    st.markdown("## Admin Dashboard - Station Registrations")
    
    submissions = get_all_submissions()
    if submissions:
        df = pd.DataFrame(submissions, columns=[
            'ID', 'Submission ID', 'Owner Name', 'Email', 'Phone', 'Zone', 'State',
            'Photo Time', 'Photo Lat', 'Photo Lon', 'Submission Time', 'Status', 'Location Source'
        ])
        
        if 'Photo Time' in df.columns:
            df['Photo Time'] = pd.to_datetime(df['Photo Time']).dt.strftime('%Y-%m-%d %H:%M')
        if 'Submission Time' in df.columns:
            df['Submission Time'] = pd.to_datetime(df['Submission Time']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(df[['Submission ID', 'Owner Name', 'Phone', 'Zone', 'State', 'Photo Time', 'Status', 'Location Source']])
        
        if st.button("Export to CSV"):
            csv_data = df.to_csv(index=False)
            b64 = base64.b64encode(csv_data.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="station_registrations.csv">📥 Download CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.info("No station registrations yet")
    
    if st.button("← Back to Registration Form"):
        st.session_state.view_submissions = False
        st.rerun()

else:
    # Show step indicator
    show_step_indicator_simple()
    
    # Step 1: Consent
    if st.session_state.current_step == 1:
        st.markdown("### Step 1: Consent & Agreement")
        
        with st.expander("📋 Read Complete Terms & Conditions", expanded=True):
            st.markdown("""
            ## Filling Station Registration Consent
            By checking the consent box below, you agree to ALL of the following:
            
            ### 1. Station Photo Capture Consent
            - You consent to capture photos of your filling station
            - Photos will include location metadata (GPS coordinates)
            - Photos will be timestamped for verification
            
            ### 2. Location Data Consent  
            - You consent to share your station's precise location coordinates
            - Location data will be used for mapping and service planning
            - You allow automatic GPS location capture when requested
            
            ### 3. Business Information Consent
            - You consent to provide business owner information
            - This information will be used for official registration
            - Data will be handled in accordance with regulations
            """)
        
        st.markdown('<div class="consent-box">', unsafe_allow_html=True)
        consent_all = st.checkbox(
            "✅ **I consent to ALL of the above terms and conditions**",
            help="Check this box to give your consent for station registration including GPS location capture"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Continue to Step 2", type="primary"):
            if consent_all:
                st.session_state.consent_given = True
                st.session_state.current_step = 2
                st.rerun()
            else:
                st.error("⚠️ You must give your consent to proceed with station registration")
    
    # Step 2: Station Information (simplified)
    elif st.session_state.current_step == 2:
        st.markdown("### Step 2: Station & Owner Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Owner Full Name *", placeholder="Enter owner's full name")
            email = st.text_input("Email Address *", placeholder="owner@station.com")
        with col2:
            phone = st.text_input("Phone Number *", placeholder="08012345678")
        
        station_name = st.text_input("Station Name *", placeholder="e.g., Mega Fuel Station")
        station_type = st.selectbox("Station Type *", ["Petrol Station", "Gas Station", "Diesel Depot", "Multi-Fuel Station"])
        
        st.markdown('<div class="location-group">', unsafe_allow_html=True)
        st.markdown("#### Station Location")
        
        zone = st.selectbox("Geopolitical Zone *", list(NIGERIAN_REGIONS.keys()), index=None)
        if zone:
            states = NIGERIAN_REGIONS[zone]
            state = st.selectbox("State *", states)
        else:
            state = None
        
        lga = st.text_input("Local Government Area (LGA) *", placeholder="e.g., Ikeja, Surulere")
        st.markdown('</div>', unsafe_allow_html=True)
        
        address = st.text_area("Detailed Station Address", placeholder="Enter complete station address with landmarks")
        
        required_fields = all([name, email, phone, station_name, station_type, zone, state, lga])
        
        col_prev, _, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("← Back"):
                st.session_state.current_step = 1
                st.rerun()
        with col_next:
            if st.button("Continue →", type="primary", disabled=not required_fields):
                st.session_state.client_data.update({
                    'full_name': name, 'email': email, 'phone': phone,
                    'station_name': station_name, 'station_type': station_type,
                    'geopolitical_zone': zone, 'state': state, 'lga': lga, 'address': address
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
        
        col_prev, _, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("← Back"):
                st.session_state.current_step = 2
                st.rerun()
        with col_next:
            photo_ready = st.session_state.photo_captured is not None
            if st.button("Continue →", type="primary", disabled=not photo_ready):
                st.session_state.current_step = 4
                st.rerun()
        
        if not photo_ready:
            st.warning("⚠️ Please capture a station photo to continue")
    
    # Step 4: Location Capture - SIMPLIFIED
    elif st.session_state.current_step == 4:
        st.markdown("### Step 4: Location Capture")
        
        # Show current location if already captured
        if st.session_state.location_data:
            st.markdown('<div class="gps-success">', unsafe_allow_html=True)
            st.success("✅ Location already captured!")
            st.write(f"**Coordinates:** {st.session_state.location_data['latitude']:.6f}, {st.session_state.location_data['longitude']:.6f}")
            st.write(f"**Source:** {st.session_state.location_data.get('source', 'Unknown').title()}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Tab interface for location methods
        tab1, tab2, tab3 = st.tabs(["📍 Automatic GPS", "🗺️ Manual Entry", "📱 QR Code Method"])
        
        with tab1:
            # Method 1: Automatic GPS
            get_gps_simple()
        
        with tab2:
            # Method 2: Manual Entry
            get_gps_manual()
            
            # Also allow manual address
            st.markdown("---")
            manual_address = st.text_area("Or enter full address", 
                                         placeholder="Complete station address with landmarks",
                                         height=100)
            if manual_address:
                st.session_state.client_data['address'] = manual_address
                st.session_state.client_data['location_source'] = 'manual_address'
                st.success("✅ Address saved")
        
        with tab3:
            # Method 3: QR Code to get coordinates from phone
            st.markdown("### 📱 Use Your Phone to Get Coordinates")
            st.markdown("""
            1. **On your phone**, open Google Maps
            2. Search for your station or long-press on the location
            3. Copy the coordinates (they look like: `6.5244, 3.3792`)
            4. **Paste them below:**
            """)
            
            phone_coords = st.text_input("Paste coordinates from your phone", 
                                        placeholder="e.g., 6.5244, 3.3792")
            
            if phone_coords:
                try:
                    lat_str, lon_str = phone_coords.split(',')
                    lat = float(lat_str.strip())
                    lon = float(lon_str.strip())
                    
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        st.session_state.location_data = {
                            'latitude': lat,
                            'longitude': lon,
                            'timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                            'source': 'phone_gps'
                        }
                        st.success(f"✅ Coordinates saved: {lat:.6f}, {lon:.6f}")
                    else:
                        st.error("Invalid coordinates range")
                except:
                    st.error("Invalid format. Please enter as: latitude, longitude")
        
        # Navigation
        col_prev, _, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("← Back to Photo"):
                st.session_state.current_step = 3
                st.rerun()
        
        with col_next:
            # Check if we have any location data
            has_location = (st.session_state.location_data is not None or 
                          st.session_state.client_data.get('address'))
            
            if st.button("Continue to Review →", type="primary", disabled=not has_location):
                # Save location data
                if st.session_state.location_data:
                    st.session_state.client_data['location_source'] = st.session_state.location_data['source']
                    st.session_state.client_data['latitude'] = st.session_state.location_data['latitude']
                    st.session_state.client_data['longitude'] = st.session_state.location_data['longitude']
                elif st.session_state.client_data.get('address'):
                    st.session_state.client_data['location_source'] = 'manual_address'
                
                st.session_state.current_step = 5
                st.rerun()
        
        if not has_location:
            st.warning("⚠️ Please provide location using one of the methods above")
    
    # Step 5: Review and Submit
    elif st.session_state.current_step == 5:
        st.markdown("### Step 5: Review & Submit")
        
        # Display summary
        st.markdown("#### 📋 Registration Summary")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Owner Information**")
            for field in ['full_name', 'email', 'phone']:
                if field in st.session_state.client_data:
                    st.write(f"**{field.replace('_', ' ').title()}:** {st.session_state.client_data[field]}")
        
        with col2:
            st.markdown("**Station Details**")
            for field in ['station_name', 'station_type', 'geopolitical_zone', 'state', 'lga']:
                if field in st.session_state.client_data:
                    st.write(f"**{field.replace('_', ' ').title()}:** {st.session_state.client_data[field]}")
        
        # Location summary
        if st.session_state.client_data.get('latitude'):
            st.markdown("**Location**")
            st.write(f"**Coordinates:** {st.session_state.client_data['latitude']:.6f}, {st.session_state.client_data['longitude']:.6f}")
            st.write(f"**Source:** {st.session_state.client_data.get('location_source', 'unknown').replace('_', ' ').title()}")
        elif st.session_state.client_data.get('address'):
            st.write(f"**Address:** {st.session_state.client_data['address']}")
        
        # Photo preview
        if st.session_state.photo_captured:
            st.markdown("**Station Photo Preview:**")
            st.image(st.session_state.photo_captured, width=300)
        
        # Final submission
        st.markdown("---")
        st.markdown("### ✅ Ready to Submit")
        
        agree_final = st.checkbox("I confirm all information is correct and complete")
        
        col_prev, _, col_submit = st.columns([1, 2, 1])
        with col_prev:
            if st.button("← Back"):
                st.session_state.current_step = 4
                st.rerun()
        
        with col_submit:
            if st.button("Submit Registration", type="primary", disabled=not agree_final):
                try:
                    # Generate submission ID
                    submission_id = f"STN-{uuid.uuid4().hex[:8].upper()}"
                    
                    # Prepare data
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
                        'submission_timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                        'station_name': st.session_state.client_data.get('station_name'),
                        'station_type': st.session_state.client_data.get('station_type'),
                        'location_source': st.session_state.client_data.get('location_source', 'manual')
                    }
                    
                    # Convert photo
                    photo_bytes = None
                    if st.session_state.photo_captured:
                        photo_bytes = st.session_state.photo_captured.getvalue()
                    
                    # Save to database
                    success = save_submission_to_db(submission_data, photo_bytes, st.session_state.photo_metadata)
                    
                    if success:
                        st.success(f"✅ Registration submitted successfully! Your ID: **{submission_id}**")
                        
                        # Reset
                        for key in ['consent_given', 'client_data', 'selected_zone', 'selected_state', 
                                  'photo_captured', 'photo_metadata', 'location_data', 'gps_triggered']:
                            if key in st.session_state:
                                del st.session_state[key]
                        
                        st.session_state.current_step = 1
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Failed to save. Please try again.")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    f'<div style="text-align: center; color: #6b7280; font-size: 0.9rem; margin-top: 2rem;">'
    f'Station Onboarding System v{APP_VERSION} • © 2024 • For Official Use Only'
    f'</div>',
    unsafe_allow_html=True
)
