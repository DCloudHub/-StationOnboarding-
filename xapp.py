"""
Station Onboarding System - NO EXTERNAL DEPENDENCIES VERSION
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
APP_VERSION = "3.1.0"
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

# Nigerian Cities with Coordinates (for manual selection)
NIGERIAN_CITIES = {
    "Abuja (FCT)": {"lat": 9.0765, "lon": 7.3986},
    "Lagos": {"lat": 6.5244, "lon": 3.3792},
    "Kano": {"lat": 12.0022, "lon": 8.5922},
    "Ibadan": {"lat": 7.3775, "lon": 3.9470},
    "Port Harcourt": {"lat": 4.8156, "lon": 7.0498},
    "Benin City": {"lat": 6.3350, "lon": 5.6037},
    "Maiduguri": {"lat": 11.8469, "lon": 13.1571},
    "Zaria": {"lat": 11.1111, "lon": 7.7222},
    "Aba": {"lat": 5.1167, "lon": 7.3667},
    "Jos": {"lat": 9.8965, "lon": 8.8583},
    "Ilorin": {"lat": 8.5000, "lon": 4.5500},
    "Oyo": {"lat": 7.8500, "lon": 3.9333},
    "Enugu": {"lat": 6.4500, "lon": 7.5000},
    "Abeokuta": {"lat": 7.1500, "lon": 3.3500},
    "Onitsha": {"lat": 6.1667, "lon": 6.7833},
    "Warri": {"lat": 5.5167, "lon": 5.7500},
    "Sokoto": {"lat": 13.0667, "lon": 5.2333},
    "Calabar": {"lat": 4.9500, "lon": 8.3250},
    "Katsina": {"lat": 12.9889, "lon": 7.6008},
    "Akure": {"lat": 7.2500, "lon": 5.2000}
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
if 'use_manual_entry' not in st.session_state:
    st.session_state.use_manual_entry = False

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
    .big-button {
        padding: 20px 40px !important;
        font-size: 1.2rem !important;
        border-radius: 10px !important;
        margin: 20px 0 !important;
        width: 100% !important;
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
    .coordinate-input {
        font-family: 'Courier New', monospace;
        font-size: 1.1rem;
    }
    .method-card {
        border: 2px solid #e5e7eb;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .method-card:hover {
        border-color: #1E3A8A;
        background-color: #f0f9ff;
    }
    .method-card.selected {
        border-color: #1E3A8A;
        background-color: #dbeafe;
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

# SIMPLE GPS FUNCTION USING JavaScript Component
def get_gps_with_javascript():
    """GPS function using embedded JavaScript"""
    
    st.markdown("""
    <div class="gps-instructions">
    <h3>📍 Automatic GPS Location Capture</h3>
    <p><strong>Instructions:</strong></p>
    <ol>
        <li>Make sure location services are <strong>ENABLED</strong> on your device</li>
        <li>Click the button below</li>
        <li>When browser asks for permission, click <strong>ALLOW</strong></li>
        <li>Wait 5-10 seconds for coordinates to appear</li>
    </ol>
    <p><strong>If it doesn't work:</strong></p>
    <ul>
        <li>Refresh the page and try again</li>
        <li>Use Google Chrome browser (works best)</li>
        <li>Go outside for better GPS signal</li>
        <li>Or use the manual entry method below</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Create columns for button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📍 CLICK HERE TO GET GPS COORDINATES", 
                    key="get_gps_main", 
                    type="primary", 
                    use_container_width=True,
                    help="This will request your location from the browser"):
            st.session_state.gps_triggered = True
            st.rerun()
    
    # Show GPS component if triggered
    if st.session_state.get('gps_triggered'):
        st.markdown("""
        <div class="gps-waiting">
        <h3>🔄 Requesting Location...</h3>
        <p><strong>Please check your browser for a location permission request!</strong></p>
        <p>If you don't see a popup, check your browser's address bar for a location icon.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # JavaScript GPS component
        gps_html = """
        <script>
        function getLocation() {
            if (navigator.geolocation) {
                var options = {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                };
                
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        // Success - send data back to Streamlit
                        const data = {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            accuracy: position.coords.accuracy,
                            timestamp: new Date().toISOString(),
                            success: true
                        };
                        
                        // Create a hidden element with the data
                        const elem = document.createElement('div');
                        elem.id = 'gpsDataResult';
                        elem.innerText = JSON.stringify(data);
                        elem.style.display = 'none';
                        document.body.appendChild(elem);
                        
                        // Trigger Streamlit to read the data
                        window.dispatchEvent(new Event('gpsDataReady'));
                        
                        // Show success message
                        document.getElementById('status').innerHTML = 
                            '<div style="color: green; font-weight: bold;">✅ GPS Location Captured!</div>' +
                            '<div>Latitude: ' + position.coords.latitude.toFixed(6) + '</div>' +
                            '<div>Longitude: ' + position.coords.longitude.toFixed(6) + '</div>';
                    },
                    function(error) {
                        // Error handling
                        let errorMessage = "Unknown error";
                        switch(error.code) {
                            case 1: errorMessage = "Permission denied. Please allow location access."; break;
                            case 2: errorMessage = "Position unavailable. Check your location settings."; break;
                            case 3: errorMessage = "Request timeout. Please try again."; break;
                        }
                        
                        document.getElementById('status').innerHTML = 
                            '<div style="color: red; font-weight: bold;">❌ ' + errorMessage + '</div>' +
                            '<div><button onclick="getLocation()" style="padding: 10px 20px; margin-top: 10px;">Try Again</button></div>';
                    },
                    options
                );
            } else {
                document.getElementById('status').innerHTML = 
                    '<div style="color: red; font-weight: bold;">❌ Geolocation not supported by this browser.</div>';
            }
        }
        
        // Auto-start when page loads
        window.onload = function() {
            getLocation();
        };
        </script>
        
        <div id="status" style="padding: 20px; text-align: center;">
            <div style="color: orange; font-weight: bold;">⏳ Requesting GPS coordinates...</div>
        </div>
        """
        
        # Display the JavaScript component
        st.components.v1.html(gps_html, height=200)
        
        # Check for GPS data in URL params (alternative method)
        st.markdown("---")
        st.markdown("### 📱 Alternative: Get Coordinates from Your Phone")
        st.markdown("""
        1. **On your smartphone**, open Google Maps
        2. Find your station location
        3. **Long press** on the exact spot
        4. Copy the coordinates (they look like: `6.5244, 3.3792`)
        5. **Paste them here:**
        """)
        
        phone_coords = st.text_input("Paste coordinates from your phone", 
                                    placeholder="e.g., 6.5244, 3.3792",
                                    key="phone_coords_input")
        
        if phone_coords:
            try:
                # Parse the coordinates
                coords = phone_coords.strip().split(',')
                if len(coords) == 2:
                    lat = float(coords[0].strip())
                    lon = float(coords[1].strip())
                    
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        st.session_state.location_data = {
                            'latitude': lat,
                            'longitude': lon,
                            'timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                            'source': 'phone_gps',
                            'success': True
                        }
                        
                        st.markdown(f"""
                        <div class="gps-success">
                        <h3>✅ Coordinates Saved!</h3>
                        <div class="gps-coordinates">
                        Latitude: {lat:.6f}<br>
                        Longitude: {lon:.6f}
                        </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("Invalid coordinate range. Latitude must be -90 to 90, Longitude -180 to 180")
                else:
                    st.error("Please enter coordinates in the format: latitude, longitude")
            except ValueError:
                st.error("Please enter valid numbers for coordinates")

# Manual coordinate entry (as fallback)
def get_manual_coordinates():
    """Manual coordinate entry with city selection"""
    st.markdown("""
    <div class="gps-instructions">
    <h3>🗺️ Manual Coordinate Entry</h3>
    <p>Enter the coordinates manually or select from common Nigerian cities:</p>
    </div>
    """, unsafe_allow_html=True)
    
    # City selection
    col1, col2 = st.columns(2)
    
    with col1:
        selected_city = st.selectbox(
            "Select a city for approximate coordinates:",
            ["-- Select a city --"] + list(NIGERIAN_CITIES.keys()),
            key="city_selector"
        )
        
        if selected_city and selected_city != "-- Select a city --":
            city_data = NIGERIAN_CITIES[selected_city]
            # Update the manual inputs with city coordinates
            st.session_state.manual_lat = str(city_data['lat'])
            st.session_state.manual_lon = str(city_data['lon'])
            st.success(f"Coordinates for {selected_city} loaded")
    
    with col2:
        # Show map of selected city
        if selected_city and selected_city != "-- Select a city --":
            city_data = NIGERIAN_CITIES[selected_city]
            # Simple map display using HTML
            map_html = f"""
            <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">
                <p style="margin: 0; font-weight: bold;">{selected_city}</p>
                <p style="margin: 5px 0;">Latitude: {city_data['lat']:.4f}</p>
                <p style="margin: 5px 0;">Longitude: {city_data['lon']:.4f}</p>
            </div>
            """
            st.markdown(map_html, unsafe_allow_html=True)
    
    # Manual coordinate input
    st.markdown("### Enter Exact Coordinates")
    
    col_lat, col_lon = st.columns(2)
    
    with col_lat:
        manual_lat = st.text_input(
            "Latitude *",
            value=st.session_state.get('manual_lat', ''),
            placeholder="e.g., 6.5244",
            help="Between -90 and 90 (Nigeria is between 4-14)",
            key="manual_lat_input"
        )
    
    with col_lon:
        manual_lon = st.text_input(
            "Longitude *",
            value=st.session_state.get('manual_lon', ''),
            placeholder="e.g., 3.3792",
            help="Between -180 and 180 (Nigeria is between 3-15)",
            key="manual_lon_input"
        )
    
    # Coordinate validation and save
    if manual_lat and manual_lon:
        try:
            lat = float(manual_lat)
            lon = float(manual_lon)
            
            # Validate ranges for Nigeria (approximate)
            if not (4 <= lat <= 14):
                st.warning("⚠️ Latitude seems outside typical Nigeria range (4-14)")
            if not (3 <= lon <= 15):
                st.warning("⚠️ Longitude seems outside typical Nigeria range (3-15)")
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                # Show preview
                st.markdown(f"""
                <div style="background-color: #f0f9ff; padding: 15px; border-radius: 8px; margin: 10px 0;">
                    <h4>📍 Coordinate Preview:</h4>
                    <div class="gps-coordinates">
                    Latitude: {lat:.6f}<br>
                    Longitude: {lon:.6f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Save button
                if st.button("✅ Save These Coordinates", type="primary", use_container_width=True):
                    st.session_state.location_data = {
                        'latitude': lat,
                        'longitude': lon,
                        'timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                        'source': 'manual',
                        'success': True
                    }
                    st.success("Coordinates saved successfully!")
                    st.rerun()
            else:
                st.error("Invalid coordinate range. Latitude must be -90 to 90, Longitude -180 to 180")
        except ValueError:
            st.error("Please enter valid numbers for coordinates")

# Address-only method
def get_address_only():
    """Address entry without coordinates"""
    st.markdown("""
    <div class="gps-instructions">
    <h3>📝 Address Entry Only</h3>
    <p>If you can't get GPS coordinates, you can enter the full address instead.</p>
    </div>
    """, unsafe_allow_html=True)
    
    address = st.text_area(
        "Enter complete station address:",
        height=150,
        placeholder="Example:\nMega Fuel Station\nNo. 25 Airport Road\nOpposite Central Market\nIkeja, Lagos State\nNigeria",
        help="Please provide as much detail as possible",
        key="address_input_full"
    )
    
    if address:
        st.session_state.client_data['address'] = address
        st.session_state.client_data['location_source'] = 'manual_address'
        st.success("✅ Address saved successfully!")

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
            - You consent to share your station's location
            - Location data will be used for official registration
            
            ### 3. Business Information Consent
            - You consent to provide business owner information
            - This information will be used for official purposes
            
            ### 4. Data Protection
            - Your data will be handled securely
            - Used only for registration purposes
            """)
        
        st.markdown('<div class="consent-box">', unsafe_allow_html=True)
        consent_all = st.checkbox(
            "✅ **I consent to ALL of the above terms and conditions**",
            help="Check this box to give your consent"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Continue to Step 2", type="primary", use_container_width=True):
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
            name = st.text_input("Full Name *", placeholder="Enter owner's full name")
            email = st.text_input("Email Address *", placeholder="owner@station.com")
        with col2:
            phone = st.text_input("Phone Number *", placeholder="08012345678")
        
        # Station Details
        st.markdown("#### ⛽ Station Details")
        station_name = st.text_input("Station Name *", placeholder="e.g., Mega Fuel Station")
        station_type = st.selectbox("Station Type *", 
                                  ["Petrol Station", "Gas Station", "Diesel Depot", "Multi-Fuel Station"])
        
        # Location Information
        st.markdown('<div class="location-group">', unsafe_allow_html=True)
        st.markdown("#### 📍 Station Location")
        
        zone = st.selectbox("Geopolitical Zone *", 
                          list(NIGERIAN_REGIONS.keys()), 
                          index=None,
                          placeholder="Select zone")
        
        state_options = NIGERIAN_REGIONS[zone] if zone else []
        state = st.selectbox("State *", 
                           state_options, 
                           disabled=not zone,
                           placeholder="Select state" if zone else "Select zone first")
        
        lga = st.text_input("Local Government Area (LGA) *", 
                          placeholder="e.g., Ikeja, Surulere")
        st.markdown('</div>', unsafe_allow_html=True)
        
        address = st.text_area("Detailed Station Address", 
                             placeholder="Enter complete station address with landmarks",
                             height=100)
        
        # Validation
        required_fields = all([name, email, phone, station_name, station_type, zone, state, lga])
        
        # Navigation
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Back to Consent", use_container_width=True):
                st.session_state.current_step = 1
                st.rerun()
        
        with col_next:
            if st.button("Continue to Photo →", type="primary", disabled=not required_fields, use_container_width=True):
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
        
        # Navigation
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Back to Information", use_container_width=True):
                st.session_state.current_step = 2
                st.rerun()
        
        with col_next:
            photo_ready = st.session_state.photo_captured is not None
            if st.button("Continue to Location →", type="primary", disabled=not photo_ready, use_container_width=True):
                st.session_state.current_step = 4
                st.rerun()
        
        if not photo_ready:
            st.warning("⚠️ Please capture a station photo to continue")
    
    # Step 4: Location Capture - MULTIPLE METHODS
    elif st.session_state.current_step == 4:
        st.markdown("### Step 4: Location Capture")
        
        # Show current location if already captured
        if st.session_state.location_data:
            st.markdown('<div class="gps-success">', unsafe_allow_html=True)
            st.success("✅ Location already captured!")
            lat = st.session_state.location_data['latitude']
            lon = st.session_state.location_data['longitude']
            st.markdown(f"""
            <div class="gps-coordinates">
            Latitude: {lat:.6f}<br>
            Longitude: {lon:.6f}
            </div>
            """, unsafe_allow_html=True)
            st.write(f"**Source:** {st.session_state.location_data.get('source', 'Unknown').replace('_', ' ').title()}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Method Selection
        st.markdown("### Choose Your Location Method:")
        
        method = st.radio(
            "Select how you want to provide location:",
            ["📍 Automatic GPS (Recommended)", 
             "🗺️ Manual Coordinate Entry", 
             "📝 Address Only (No Coordinates)"],
            index=0,
            key="location_method"
        )
        
        st.markdown("---")
        
        # Display selected method
        if "Automatic GPS" in method:
            get_gps_with_javascript()
        elif "Manual Coordinate" in method:
            get_manual_coordinates()
        elif "Address Only" in method:
            get_address_only()
        
        # Navigation
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Back to Photo", use_container_width=True):
                st.session_state.current_step = 3
                st.rerun()
        
        with col_next:
            # Check if we have location data
            has_gps = st.session_state.location_data is not None
            has_address = st.session_state.client_data.get('address') is not None
            
            location_ready = has_gps or has_address
            
            if st.button("Continue to Review →", type="primary", disabled=not location_ready, use_container_width=True):
                # Save location data
                if has_gps:
                    st.session_state.client_data['location_source'] = st.session_state.location_data['source']
                    st.session_state.client_data['latitude'] = st.session_state.location_data['latitude']
                    st.session_state.client_data['longitude'] = st.session_state.location_data['longitude']
                elif has_address:
                    st.session_state.client_data['location_source'] = 'manual_address'
                
                st.session_state.current_step = 5
                st.rerun()
        
        if not location_ready:
            st.warning("⚠️ Please provide location using one of the methods above")
    
    # Step 5: Review and Submit
    elif st.session_state.current_step == 5:
        st.markdown("### Step 5: Review & Submit")
        
        # Display summary
        st.markdown("#### 📋 Registration Summary")
        
        # Create two columns for better layout
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
                st.markdown(f"""
                **Coordinates:**
                <div class="gps-coordinates" style="font-size: 1rem; padding: 10px;">
                {lat:.6f}, {lon:.6f}
                </div>
                """, unsafe_allow_html=True)
                st.write(f"**Source:** {st.session_state.client_data.get('location_source', 'unknown').replace('_', ' ').title()}")
            elif st.session_state.client_data.get('address'):
                st.write(f"**Address:** {st.session_state.client_data['address']}")
        
        # Photo preview
        if st.session_state.photo_captured:
            st.markdown("**📸 Station Photo:**")
            st.image(st.session_state.photo_captured, width=300)
        
        # Final submission
        st.markdown("---")
        st.markdown("### ✅ Ready to Submit")
        
        agree_final = st.checkbox("**I confirm all information is correct and complete**")
        
        col_prev, col_submit = st.columns(2)
        with col_prev:
            if st.button("← Back to Location", use_container_width=True):
                st.session_state.current_step = 4
                st.rerun()
        
        with col_submit:
            if st.button("Submit Registration", type="primary", disabled=not agree_final, use_container_width=True):
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
                        st.success(f"""
                        ## ✅ Registration Successful!
                        
                        **Your Submission ID:** `{submission_id}`
                        
                        Please save this ID for future reference.
                        """)
                        
                        # Reset all session state
                        keys_to_keep = ['admin_authenticated', 'view_submissions']
                        for key in list(st.session_state.keys()):
                            if key not in keys_to_keep:
                                del st.session_state[key]
                        
                        # Add a button to start new registration
                        if st.button("Start New Registration", type="primary", use_container_width=True):
                            st.rerun()
                        
                        st.balloons()
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
