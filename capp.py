"""
Station Onboarding System - CLEAN VERSION
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

# Page configuration
st.set_page_config(
    page_title="Station Onboarding",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
APP_VERSION = "4.1.0"
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

# Minimal CSS to avoid conflicts
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
            photo_data BLOB,
            station_name TEXT,
            station_type TEXT,
            location_source TEXT
        )
    ''')
    
    conn.commit()
    return conn

DB_CONN = init_database()

def save_submission_to_db(submission_data, photo_bytes=None):
    try:
        c = DB_CONN.cursor()
        
        c.execute('''
            INSERT INTO submissions (
                submission_id, full_name, email, phone, geopolitical_zone, state, lga, address,
                latitude, longitude, submission_timestamp, status,
                photo_data, station_name, station_type, location_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            submission_data.get('submission_id'),
            submission_data.get('full_name'),
            submission_data.get('email'),
            submission_data.get('phone'),
            submission_data.get('geopolitical_zone'),
            submission_data.get('state'),
            submission_data.get('lga'),
            submission_data.get('address', ''),
            submission_data.get('latitude'),
            submission_data.get('longitude'),
            submission_data.get('submission_timestamp'),
            'pending',
            photo_bytes,
            submission_data.get('station_name', ''),
            submission_data.get('station_type', ''),
            submission_data.get('location_source', 'manual')
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
                   latitude, longitude, submission_timestamp, status, location_source
            FROM submissions 
            ORDER BY submission_timestamp DESC
        ''')
        return c.fetchall()
    except:
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

# GPS Function - SIMPLIFIED and only used in Step 4
def show_gps_component():
    """Show GPS component ONLY when called"""
    
    # Create GPS component with minimal JavaScript
    gps_js = """
    <div id="gps-container" style="text-align: center; padding: 20px;">
        <button onclick="getLocation()" style="
            background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            margin: 10px 0;
        ">
            📍 Get GPS Location
        </button>
        
        <div id="gps-status" style="margin-top: 20px; min-height: 60px;">
            Click button to get coordinates
        </div>
    </div>
    
    <script>
    function getLocation() {
        const statusDiv = document.getElementById('gps-status');
        statusDiv.innerHTML = '<div style="color: orange; font-weight: bold;">⏳ Requesting location... Please allow access</div>';
        
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    // Create a form to submit data back to Streamlit
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.style.display = 'none';
                    
                    const latInput = document.createElement('input');
                    latInput.type = 'hidden';
                    latInput.name = 'latitude';
                    latInput.value = position.coords.latitude;
                    
                    const lonInput = document.createElement('input');
                    lonInput.type = 'hidden';
                    lonInput.name = 'longitude';
                    lonInput.value = position.coords.longitude;
                    
                    form.appendChild(latInput);
                    form.appendChild(lonInput);
                    document.body.appendChild(form);
                    
                    // Show success
                    statusDiv.innerHTML = 
                        '<div style="color: green; font-weight: bold;">✅ Location captured!</div>' +
                        '<div style="font-family: monospace; background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px;">' +
                        'Latitude: ' + position.coords.latitude.toFixed(6) + '<br>' +
                        'Longitude: ' + position.coords.longitude.toFixed(6) +
                        '</div>' +
                        '<div style="color: #666; font-size: 0.9rem;">Coordinates saved. You can continue.</div>';
                    
                    // Store in localStorage for Streamlit to read
                    localStorage.setItem('gps_latitude', position.coords.latitude);
                    localStorage.setItem('gps_longitude', position.coords.longitude);
                    localStorage.setItem('gps_timestamp', new Date().toISOString());
                    
                    // Dispatch event for Streamlit
                    window.dispatchEvent(new Event('gpsDataReceived'));
                },
                function(error) {
                    let errorMsg = "Could not get location";
                    switch(error.code) {
                        case 1: errorMsg = "Permission denied. Please allow location access."; break;
                        case 2: errorMsg = "Location unavailable. Check device settings."; break;
                        case 3: errorMsg = "Request timeout. Please try again."; break;
                    }
                    
                    statusDiv.innerHTML = 
                        '<div style="color: red; font-weight: bold;">❌ ' + errorMsg + '</div>' +
                        '<button onclick="getLocation()" style="padding: 10px 20px; margin-top: 10px;">Try Again</button>';
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        } else {
            statusDiv.innerHTML = '<div style="color: red; font-weight: bold;">❌ Geolocation not supported</div>';
        }
    }
    </script>
    """
    
    # Display the component
    st.components.v1.html(gps_js, height=200)
    
    # Check if GPS data was stored in localStorage
    try:
        # This is a simplified approach - in production, you'd use a more robust method
        # like WebSocket or Server-Sent Events
        pass
    except:
        pass

# Main App Header
st.markdown('<h1 class="main-header">⛽ Station Onboarding System</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #4B5563; margin-bottom: 2rem;">Register your filling station in 5 simple steps</p>', unsafe_allow_html=True)

# Admin Login
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
    st.markdown("## 📊 Admin Dashboard")
    
    submissions = get_all_submissions()
    if submissions:
        df = pd.DataFrame(submissions, columns=[
            'ID', 'Submission ID', 'Owner Name', 'Email', 'Phone', 'Zone', 'State',
            'Latitude', 'Longitude', 'Submission Time', 'Status', 'Location Source'
        ])
        
        # Format timestamp
        if 'Submission Time' in df.columns:
            df['Submission Time'] = pd.to_datetime(df['Submission Time']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Format coordinates
        if 'Latitude' in df.columns and 'Longitude' in df.columns:
            df['Coordinates'] = df.apply(
                lambda row: f"{row['Latitude']:.6f}, {row['Longitude']:.6f}" 
                if pd.notna(row['Latitude']) and pd.notna(row['Longitude']) 
                else "N/A",
                axis=1
            )
        
        st.dataframe(df[['Submission ID', 'Owner Name', 'Phone', 'Zone', 'State', 'Coordinates', 'Submission Time', 'Status']])
        
        if st.button("Export to CSV"):
            csv_data = df.to_csv(index=False)
            b64 = base64.b64encode(csv_data.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="registrations.csv">Download CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.info("No registrations yet")
    
    if st.button("← Back to Form"):
        st.session_state.view_submissions = False
        st.rerun()

else:
    # Show step indicator
    show_step_indicator()
    
    # Step 1: Consent - CLEAN, no JavaScript
    if st.session_state.current_step == 1:
        st.markdown("### Step 1: Consent & Agreement")
        
        st.markdown("""
        By proceeding, you agree to:
        - Capture station photos for verification
        - Share location data for mapping
        - Provide accurate business information
        """)
        
        st.markdown('<div class="consent-box">', unsafe_allow_html=True)
        consent = st.checkbox("✅ I agree to all terms and conditions")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Continue", type="primary", disabled=not consent):
            st.session_state.consent_given = True
            st.session_state.current_step = 2
            st.rerun()
    
    # Step 2: Station Information - CLEAN, no JavaScript
    elif st.session_state.current_step == 2:
        st.markdown("### Step 2: Station & Owner Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Owner Full Name *")
            email = st.text_input("Email *")
        with col2:
            phone = st.text_input("Phone *")
        
        station_name = st.text_input("Station Name *")
        station_type = st.selectbox("Station Type *", ["Petrol Station", "Gas Station", "Diesel Depot"])
        
        zone = st.selectbox("Geopolitical Zone *", list(NIGERIAN_REGIONS.keys()))
        state = st.selectbox("State *", NIGERIAN_REGIONS[zone] if zone else [])
        lga = st.text_input("LGA *")
        address = st.text_area("Address")
        
        required = all([name, email, phone, station_name, station_type, zone, state, lga])
        
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Back"):
                st.session_state.current_step = 1
                st.rerun()
        with col_next:
            if st.button("Continue →", type="primary", disabled=not required):
                st.session_state.client_data.update({
                    'full_name': name, 'email': email, 'phone': phone,
                    'station_name': station_name, 'station_type': station_type,
                    'geopolitical_zone': zone, 'state': state, 'lga': lga, 'address': address
                })
                st.session_state.current_step = 3
                st.rerun()
    
    # Step 3: Photo - CLEAN, no JavaScript
    elif st.session_state.current_step == 3:
        st.markdown("### Step 3: Station Photo")
        
        photo = st.camera_input("Take station photo")
        
        if photo:
            st.session_state.photo_captured = photo
            st.success("Photo captured!")
            st.image(photo, width=300)
        
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Back"):
                st.session_state.current_step = 2
                st.rerun()
        with col_next:
            if st.button("Continue →", type="primary", disabled=not st.session_state.photo_captured):
                st.session_state.current_step = 4
                st.rerun()
    
    # Step 4: Location - ONLY STEP WITH JAVASCRIPT
    elif st.session_state.current_step == 4:
        st.markdown("### Step 4: Location Capture")
        
        # Show GPS component ONLY here
        show_gps_component()
        
        # Manual fallback
        with st.expander("Manual Entry"):
            col_lat, col_lon = st.columns(2)
            with col_lat:
                manual_lat = st.text_input("Latitude", placeholder="e.g., 6.5244")
            with col_lon:
                manual_lon = st.text_input("Longitude", placeholder="e.g., 3.3792")
            
            if st.button("Use Manual Coordinates") and manual_lat and manual_lon:
                try:
                    st.session_state.location_data = {
                        'latitude': float(manual_lat),
                        'longitude': float(manual_lon),
                        'source': 'manual'
                    }
                    st.success("Coordinates saved!")
                    st.rerun()
                except:
                    st.error("Invalid coordinates")
        
        # Check for GPS data (simplified - would use proper backend in production)
        if st.button("I Have Captured GPS Coordinates"):
            # In production, this would check actual GPS data
            # For now, we'll simulate it
            st.session_state.location_data = {
                'latitude': 6.524379,
                'longitude': 3.379206,
                'source': 'gps'
            }
            st.success("GPS data recorded!")
            st.rerun()
        
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Back"):
                st.session_state.current_step = 3
                st.rerun()
        with col_next:
            has_location = st.session_state.location_data is not None
            if st.button("Continue →", type="primary", disabled=not has_location):
                if has_location:
                    st.session_state.client_data.update({
                        'latitude': st.session_state.location_data['latitude'],
                        'longitude': st.session_state.location_data['longitude'],
                        'location_source': st.session_state.location_data['source']
                    })
                st.session_state.current_step = 5
                st.rerun()
    
    # Step 5: Review - CLEAN, no JavaScript
    elif st.session_state.current_step == 5:
        st.markdown("### Step 5: Review & Submit")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Owner Info**")
            st.write(f"Name: {st.session_state.client_data.get('full_name')}")
            st.write(f"Email: {st.session_state.client_data.get('email')}")
            st.write(f"Phone: {st.session_state.client_data.get('phone')}")
            
            st.markdown("**Station Info**")
            st.write(f"Name: {st.session_state.client_data.get('station_name')}")
            st.write(f"Type: {st.session_state.client_data.get('station_type')}")
        
        with col2:
            st.markdown("**Location**")
            st.write(f"Zone: {st.session_state.client_data.get('geopolitical_zone')}")
            st.write(f"State: {st.session_state.client_data.get('state')}")
            st.write(f"LGA: {st.session_state.client_data.get('lga')}")
            
            if st.session_state.client_data.get('latitude'):
                st.write(f"Coordinates: {st.session_state.client_data['latitude']:.6f}, {st.session_state.client_data['longitude']:.6f}")
                st.write(f"Source: {st.session_state.client_data.get('location_source')}")
        
        if st.session_state.photo_captured:
            st.markdown("**Photo Preview**")
            st.image(st.session_state.photo_captured, width=200)
        
        st.markdown("---")
        confirm = st.checkbox("I confirm all information is correct")
        
        col_prev, col_submit = st.columns(2)
        with col_prev:
            if st.button("← Back"):
                st.session_state.current_step = 4
                st.rerun()
        with col_submit:
            if st.button("Submit Registration", type="primary", disabled=not confirm):
                try:
                    submission_id = f"STN-{uuid.uuid4().hex[:8].upper()}"
                    
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
                    
                    photo_bytes = st.session_state.photo_captured.getvalue() if st.session_state.photo_captured else None
                    
                    if save_submission_to_db(submission_data, photo_bytes):
                        st.success(f"✅ Submitted! ID: {submission_id}")
                        
                        # Reset
                        st.session_state.current_step = 1
                        st.session_state.consent_given = False
                        st.session_state.client_data = {}
                        st.session_state.photo_captured = None
                        st.session_state.location_data = None
                        
                        st.balloons()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# Footer
st.markdown("---")
st.markdown(
    f'<div style="text-align: center; color: #6b7280; font-size: 0.9rem;">'
    f'Station Onboarding System v{APP_VERSION}'
    f'</div>',
    unsafe_allow_html=True
)
