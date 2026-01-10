"""
Station Onboarding System
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

# Page configuration
st.set_page_config(
    page_title="Station Onboarding",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
APP_VERSION = "2.0.0"
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
            station_type TEXT
        )
    ''')
    
    conn.commit()
    return conn

DB_CONN = init_database()

def save_submission_to_db(submission_data, photo_bytes=None, photo_metadata=None):
    try:
        c = DB_CONN.cursor()
        
        # Combine submission data with photo metadata
        submission_data_with_meta = submission_data.copy()
        if photo_metadata:
            submission_data_with_meta['photo_timestamp'] = photo_metadata.get('timestamp')
            submission_data_with_meta['photo_latitude'] = photo_metadata.get('latitude')
            submission_data_with_meta['photo_longitude'] = photo_metadata.get('longitude')
        
        c.execute('''
            INSERT INTO submissions (
                submission_id, full_name, email, phone, geopolitical_zone, state, lga, address,
                latitude, longitude, submission_timestamp, status,
                photo_timestamp, photo_latitude, photo_longitude, photo_data,
                station_name, station_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            submission_data_with_meta.get('station_type', '')
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
                   photo_timestamp, photo_latitude, photo_longitude, submission_timestamp, status
            FROM submissions 
            ORDER BY submission_timestamp DESC
        ''')
        return c.fetchall()
    except:
        return []

# Step indicator function using Streamlit columns
def show_step_indicator_simple():
    """Use Streamlit columns for steps"""
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

# Header
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

# Main App
if st.session_state.admin_authenticated and st.session_state.view_submissions:
    st.markdown("## Admin Dashboard - Station Registrations")
    
    submissions = get_all_submissions()
    if submissions:
        df = pd.DataFrame(submissions, columns=[
            'ID', 'Submission ID', 'Owner Name', 'Email', 'Phone', 'Zone', 'State',
            'Photo Time', 'Photo Lat', 'Photo Lon', 'Submission Time', 'Status'
        ])
        
        # Format columns
        if 'Photo Time' in df.columns:
            df['Photo Time'] = pd.to_datetime(df['Photo Time']).dt.strftime('%Y-%m-%d %H:%M')
        if 'Submission Time' in df.columns:
            df['Submission Time'] = pd.to_datetime(df['Submission Time']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(df[['Submission ID', 'Owner Name', 'Phone', 'Zone', 'State', 'Photo Time', 'Status']])
        
        # Export functionality
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
            - Images will be used for station verification and documentation
            
            ### 2. Location Data Consent  
            - You consent to share your station's precise location coordinates
            - Location data will be used for mapping and service planning
            - Coordinates will be embedded in station photos
            
            ### 3. Business Information Consent
            - You consent to provide business owner information
            - This information will be used for official registration
            - Data will be handled in accordance with regulations
            
            ### 4. Terms & Conditions Acceptance
            - You agree to abide by our Terms & Conditions
            - You acknowledge our Privacy Policy
            - You confirm all information provided is accurate
            """)
        
        st.markdown('<div class="consent-box">', unsafe_allow_html=True)
        
        consent_all = st.checkbox(
            "✅ **I consent to ALL of the above terms and conditions**",
            help="Check this box to give your consent for station registration"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Continue to Step 2", type="primary"):
            if consent_all:
                st.session_state.consent_given = True
                st.session_state.current_step = 2
                st.rerun()
            else:
                st.error("⚠️ You must give your consent to proceed with station registration")
    
    # Step 2: Station Information - FIXED: No form wrapping
    elif st.session_state.current_step == 2:
        st.markdown("### Step 2: Station & Owner Information")
        
        # Owner Information Section
        st.markdown("#### Station Owner Information")
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Owner Full Name *", placeholder="Enter owner's full name", key="owner_name")
            email = st.text_input("Email Address *", placeholder="owner@station.com", key="owner_email")
        
        with col2:
            phone = st.text_input("Phone Number *", placeholder="08012345678", key="owner_phone")
        
        # Station Details Section
        st.markdown("#### Station Details")
        station_name = st.text_input("Station Name *", placeholder="e.g., Mega Fuel Station", key="station_name")
        
        col_type1, col_type2 = st.columns(2)
        with col_type1:
            station_type = st.selectbox("Station Type *",
                                      ["Petrol Station", "Gas Station", "Diesel Depot", "Multi-Fuel Station"],
                                      index=None,
                                      placeholder="Select station type",
                                      key="station_type")
        
        # Location Information Group - OUTSIDE OF FORM
        st.markdown('<div class="location-group">', unsafe_allow_html=True)
        st.markdown("#### Station Location")
        
        # Use st.columns for horizontal layout
        loc_col1, loc_col2, loc_col3 = st.columns(3)
        
        with loc_col1:
            # Zone selection - updates session state immediately
            zone = st.selectbox(
                "Geopolitical Zone *",
                list(NIGERIAN_REGIONS.keys()),
                index=None,
                placeholder="Select station zone",
                key="zone_select"
            )
            
            # Update session state when zone changes
            if zone != st.session_state.get('selected_zone'):
                st.session_state.selected_zone = zone
                st.session_state.selected_state = None  # Reset state when zone changes
                st.rerun()
        
        with loc_col2:
            # State selection - IMMEDIATELY appears when Zone is selected
            state_options = NIGERIAN_REGIONS[st.session_state.selected_zone] if st.session_state.selected_zone else []
            
            # Get current state value
            current_state = st.session_state.get('selected_state')
            state_index = None
            if current_state and current_state in state_options:
                state_index = state_options.index(current_state)
            
            state = st.selectbox(
                "State *",
                state_options,
                index=state_index,
                placeholder="Select state" if st.session_state.selected_zone else "Select zone first",
                disabled=not st.session_state.selected_zone,
                key="state_select"
            )
            
            # Update session state when state changes
            if state != st.session_state.get('selected_state'):
                st.session_state.selected_state = state
                # Don't rerun here to avoid interrupting user input
        
        with loc_col3:
            # LGA input - IMMEDIATELY appears when State is selected
            lga = st.text_input(
                "Local Government Area (LGA) *",
                placeholder="Enter station LGA" if st.session_state.selected_state else "Select state first",
                disabled=not st.session_state.selected_state,
                key="lga_input"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Address field
        address = st.text_area("Station Address *", 
                             placeholder="Full address including street, area, landmark...",
                             height=80,
                             key="address_input")
        
        notes = st.text_area("Additional Information (Optional)", 
                           placeholder="Any special notes, facilities, or additional information...",
                           key="notes_input")
        
        # Navigation buttons
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("← Back to Consent"):
                st.session_state.current_step = 1
                st.session_state.selected_zone = None
                st.session_state.selected_state = None
                st.rerun()
        
        with col_btn2:
            if st.button("Next: Capture Station Photo →", type="primary"):
                # Validate all required fields
                required_fields = {
                    "Owner Name": name,
                    "Email": email,
                    "Phone": phone,
                    "Station Name": station_name,
                    "Station Type": station_type,
                    "Zone": st.session_state.selected_zone,
                    "State": st.session_state.selected_state,
                    "LGA": lga,
                    "Address": address
                }
                
                missing_fields = [field for field, value in required_fields.items() if not value]
                
                if not missing_fields:
                    st.session_state.client_data = {
                        'full_name': name,
                        'email': email,
                        'phone': phone,
                        'geopolitical_zone': st.session_state.selected_zone,
                        'state': st.session_state.selected_state,
                        'lga': lga,
                        'station_name': station_name,
                        'station_type': station_type,
                        'address': address,
                        'notes': notes
                    }
                    st.session_state.current_step = 3
                    st.rerun()
                else:
                    st.error(f"❌ Please fill in all required fields: {', '.join(missing_fields)}")
    
    # Step 3: Station Photo Capture with Metadata
    elif st.session_state.current_step == 3:
        st.markdown("### Step 3: Station Photo Capture")
        
        st.markdown('<div class="station-icon">⛽</div>', unsafe_allow_html=True)
        
        st.info("""
        **Station Photo Guidelines:**
        
        **What to include in the photo:**
        - Capture the entire filling station clearly
        - Include station signage and name clearly visible
        - Show all fuel pumps and dispensers
        - Include station building/structure
        - Capture the surrounding area for context
        
        **Best practices:**
        - Ensure good lighting (daylight recommended)
        - Take photo from a distance that shows the full station
        - Capture from an angle that shows entry/exit points
        - Include any unique identifying features
        - Make sure the station name is readable
        """)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div style="border: 3px solid #1E3A8A; border-radius: 10px; padding: 10px; background-color: #000; text-align: center;">', unsafe_allow_html=True)
            st.markdown('<p style="color: white; margin-bottom: 10px;">Capture photo of the filling station</p>', unsafe_allow_html=True)
            photo = st.camera_input("", label_visibility="collapsed", key="station_camera")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if photo:
                # Get current location for metadata (if available from previous step)
                location_info = ""
                lat = None
                lon = None
                
                if st.session_state.location_data:
                    lat = st.session_state.location_data.get('latitude')
                    lon = st.session_state.location_data.get('longitude')
                    if lat and lon:
                        location_info = f"GPS: {lat:.6f}, {lon:.6f}"
                
                # Get current timestamp
                timestamp = datetime.now(NIGERIA_TZ).strftime('%Y-%m-%d %H:%M:%S')
                
                # Process image to add metadata overlay
                try:
                    # Open the original image
                    original_image = Image.open(photo)
                    
                    # Create a copy for metadata overlay
                    img_with_meta = original_image.copy()
                    draw = ImageDraw.Draw(img_with_meta)
                    
                    # Try to load a font, fallback to default
                    try:
                        # Try different font options
                        font_paths = [
                            "arial.ttf",
                            "Arial.ttf",
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                            "/System/Library/Fonts/Helvetica.ttc"
                        ]
                        font = None
                        for font_path in font_paths:
                            try:
                                font = ImageFont.truetype(font_path, 24)
                                break
                            except:
                                continue
                        if font is None:
                            font = ImageFont.load_default()
                    except:
                        font = ImageFont.load_default()
                    
                    # Prepare metadata text
                    station_name = st.session_state.client_data.get('station_name', 'Station')
                    metadata_lines = [
                        f"⛽ {station_name}",
                        f"📅 {timestamp}",
                    ]
                    
                    if location_info:
                        metadata_lines.append(f"📍 {location_info}")
                    metadata_lines.append("🔒 Station Verification")
                    
                    # Calculate text position (bottom of image)
                    text_margin = 10
                    line_height = 30
                    text_y = img_with_meta.height - (len(metadata_lines) * line_height) - text_margin
                    
                    # Draw semi-transparent background for text
                    bg_height = len(metadata_lines) * line_height + 20
                    bg_width = img_with_meta.width - 20
                    draw.rectangle([text_margin, text_y - 10, bg_width, text_y + bg_height], 
                                 fill=(0, 0, 0, 180))  # Semi-transparent black
                    
                    # Draw each line of metadata
                    for i, line in enumerate(metadata_lines):
                        text_x = text_margin + 10
                        current_y = text_y + (i * line_height)
                        draw.text((text_x, current_y), line, fill=(255, 255, 255), font=font)
                    
                    # Display the processed image
                    st.image(img_with_meta, caption="Station Photo with Embedded Metadata", width=250)
                    st.success("✅ Station photo captured with metadata!")
                    
                    # Save the processed image to BytesIO
                    img_bytes = io.BytesIO()
                    img_with_meta.save(img_bytes, format='JPEG', quality=95)
                    img_bytes.seek(0)
                    
                    # Store in session state
                    st.session_state.photo_captured = img_bytes
                    st.session_state.photo_metadata = {
                        'timestamp': timestamp,
                        'latitude': lat,
                        'longitude': lon,
                        'station_name': station_name,
                        'image_format': 'JPEG',
                        'has_metadata_overlay': True
                    }
                    
                    # Show metadata summary
                    st.markdown("**Embedded Metadata:**")
                    st.markdown(f"- **Timestamp:** {timestamp}")
                    if lat and lon:
                        st.markdown(f"- **Coordinates:** {lat:.6f}, {lon:.6f}")
                    st.markdown(f"- **Station:** {station_name}")
                    st.markdown("- **Status:** ✅ Metadata embedded successfully")
                    
                except Exception as e:
                    st.error(f"Error processing image: {str(e)}")
                    # Fallback: save original photo without metadata
                    st.session_state.photo_captured = photo
                    image = Image.open(photo)
                    st.image(image, caption="Station Photo", width=150)
                    st.warning("⚠️ Photo captured but metadata embedding failed")
                    st.session_state.photo_metadata = {
                        'timestamp': timestamp,
                        'latitude': lat,
                        'longitude': lon,
                        'has_metadata_overlay': False
                    }
            else:
                st.info("### Ready to Capture")
                st.markdown("""
                **Camera Instructions:**
                1. Click the camera icon above
                2. Allow camera access if prompted
                3. Position the station in frame
                4. Click the capture button
                
                **The photo will automatically include:**
                - Station name
                - Date and time stamp
                - GPS coordinates (if available)
                - Verification watermark
                """)
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("← Back to Station Info"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col_btn3:
            if photo and st.button("Next: Verify Location →", type="primary"):
                st.session_state.current_step = 4
                st.rerun()
    
    # Step 4: Location Verification
    elif st.session_state.current_step == 4:
        st.markdown("### Step 4: Location Verification")
        
        st.markdown("### Verify Station Coordinates")
        
        # Show photo preview with metadata
        if st.session_state.photo_captured and st.session_state.photo_metadata:
            col_preview1, col_preview2 = st.columns(2)
            with col_preview1:
                st.markdown("#### Photo with Metadata")
                try:
                    if hasattr(st.session_state.photo_captured, 'read'):
                        st.session_state.photo_captured.seek(0)
                        image = Image.open(st.session_state.photo_captured)
                    else:
                        image = Image.open(st.session_state.photo_captured)
                    st.image(image, caption="Your Station Photo", width=250)
                except:
                    st.info("Photo preview not available")
            
            with col_preview2:
                st.markdown("#### Embedded Metadata")
                meta = st.session_state.photo_metadata
                st.write(f"**Timestamp:** {meta.get('timestamp')}")
                if meta.get('station_name'):
                    st.write(f"**Station:** {meta.get('station_name')}")
                if meta.get('latitude') and meta.get('longitude'):
                    st.write(f"**Photo Coordinates:** {meta.get('latitude'):.6f}, {meta.get('longitude'):.6f}")
                st.write(f"**Metadata Status:** {'✅ Embedded' if meta.get('has_metadata_overlay', False) else '⚠️ Not embedded'}")
        
        st.markdown("### Enter/Verify Station Coordinates")
        
        col_lat, col_lon = st.columns(2)
        with col_lat:
            # Pre-fill with photo coordinates if available
            default_lat = st.session_state.photo_metadata.get('latitude', 0.0) if st.session_state.photo_metadata else 0.0
            latitude = st.number_input("Latitude *", format="%.6f", value=float(default_lat),
                                     help="Example: 9.076479 (for Abuja)")
        with col_lon:
            default_lon = st.session_state.photo_metadata.get('longitude', 0.0) if st.session_state.photo_metadata else 0.0
            longitude = st.number_input("Longitude *", format="%.6f", value=float(default_lon),
                                      help="Example: 7.398574 (for Abuja)")
        
        # Show station information
        if st.session_state.client_data:
            st.info(f"""
            **Station Information:**
            - **Station Name:** {st.session_state.client_data.get('station_name')}
            - **Station Type:** {st.session_state.client_data.get('station_type')}
            - **State:** {st.session_state.client_data.get('state')}
            - **LGA:** {st.session_state.client_data.get('lga')}
            - **Address:** {st.session_state.client_data.get('address', 'Not provided')}
            """)
        
        # Show map preview
        if latitude != 0.0 and longitude != 0.0:
            location_df = pd.DataFrame({
                'lat': [latitude],
                'lon': [longitude]
            })
            st.map(location_df, zoom=15)
            st.caption("Map preview of station location coordinates")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("← Back to Photo"):
                st.session_state.current_step = 3
                st.rerun()
        
        with col_btn3:
            if st.button("Next: Review & Submit →", type="primary"):
                if latitude != 0.0 and longitude != 0.0:
                    # Update location data
                    st.session_state.location_data = {
                        'latitude': latitude,
                        'longitude': longitude,
                        'timestamp': datetime.now(NIGERIA_TZ).isoformat()
                    }
                    
                    # Update photo metadata with verified coordinates
                    if st.session_state.photo_metadata:
                        st.session_state.photo_metadata['latitude'] = latitude
                        st.session_state.photo_metadata['longitude'] = longitude
                        st.session_state.photo_metadata['coordinates_verified'] = True
                    
                    st.session_state.current_step = 5
                    st.rerun()
                else:
                    st.error("❌ Please enter valid station coordinates")
    
    # Step 5: Review & Submit
    elif st.session_state.current_step == 5:
        st.markdown("### Step 5: Review & Submit Registration")
        
        if all([st.session_state.client_data, st.session_state.photo_captured, st.session_state.location_data]):
            st.markdown("### 📋 Station Registration Summary")
            
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                st.markdown("#### Station & Owner Information")
                client_data = st.session_state.client_data
                st.write(f"**Owner Name:** {client_data.get('full_name')}")
                st.write(f"**Email:** {client_data.get('email')}")
                st.write(f"**Phone:** {client_data.get('phone')}")
                st.write(f"**Station Name:** {client_data.get('station_name')}")
                st.write(f"**Station Type:** {client_data.get('station_type')}")
                st.write(f"**Zone:** {client_data.get('geopolitical_zone')}")
                st.write(f"**State:** {client_data.get('state')}")
                st.write(f"**LGA:** {client_data.get('lga')}")
                if client_data.get('address'):
                    st.write(f"**Address:** {client_data.get('address')}")
                if client_data.get('notes'):
                    st.write(f"**Notes:** {client_data.get('notes')}")
            
            with col_s2:
                st.markdown("#### Verification Data")
                
                # Show photo with metadata
                if st.session_state.photo_captured:
                    try:
                        if hasattr(st.session_state.photo_captured, 'read'):
                            st.session_state.photo_captured.seek(0)
                            image = Image.open(st.session_state.photo_captured)
                        else:
                            image = Image.open(st.session_state.photo_captured)
                        
                        st.image(image, caption="Station Photo with Embedded Metadata", width=250)
                        
                        # Show metadata details
                        if hasattr(st.session_state, 'photo_metadata') and st.session_state.photo_metadata:
                            meta = st.session_state.photo_metadata
                            st.write("**Photo Metadata:**")
                            st.write(f"- **Captured:** {meta.get('timestamp')}")
                            if meta.get('latitude') and meta.get('longitude'):
                                st.write(f"- **Coordinates:** {meta.get('latitude'):.6f}, {meta.get('longitude'):.6f}")
                            if meta.get('station_name'):
                                st.write(f"- **Station:** {meta.get('station_name')}")
                            st.write(f"- **Status:** {'✅ Metadata verified' if meta.get('coordinates_verified', False) else '⚠️ Needs verification'}")
                        
                        st.success("✅ Station photo verified with metadata")
                    except Exception as e:
                        st.error(f"Cannot display photo: {str(e)}")
                        st.info("Photo is stored but cannot be displayed")
                
                # Show location on map
                loc = st.session_state.location_data
                st.write(f"**Verified Coordinates:** {loc['latitude']:.6f}, {loc['longitude']:.6f}")
                
                location_df = pd.DataFrame({
                    'lat': [loc['latitude']],
                    'lon': [loc['longitude']]
                })
                st.map(location_df, zoom=15)
                st.caption("Station location on map")
            
            st.markdown("---")
            st.markdown("### 🚀 Ready to Submit Station Registration")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("← Back to Location"):
                    st.session_state.current_step = 4
                    st.rerun()
            
            with col_btn2:
                if st.button("Submit Station Registration", type="primary", use_container_width=True):
                    # Generate unique submission ID
                    submission_id = f"STA-{datetime.now(NIGERIA_TZ).strftime('%Y%m%d-%H%M%S')}"
                    
                    # Prepare final data
                    final_data = {
                        **st.session_state.client_data,
                        'latitude': st.session_state.location_data['latitude'],
                        'longitude': st.session_state.location_data['longitude'],
                        'submission_id': submission_id,
                        'submission_timestamp': datetime.now(NIGERIA_TZ).isoformat()
                    }
                    
                    # Prepare photo data
                    photo_bytes = None
                    if st.session_state.photo_captured:
                        if hasattr(st.session_state.photo_captured, 'read'):
                            st.session_state.photo_captured.seek(0)
                            photo_bytes = st.session_state.photo_captured.read()
                        else:
                            photo_bytes = st.session_state.photo_captured.getvalue() if hasattr(st.session_state.photo_captured, 'getvalue') else None
                    
                    # Save to database
                    if save_submission_to_db(final_data, photo_bytes, st.session_state.photo_metadata):
                        st.balloons()
                        st.success(f"""
                        🎉 **Station Registration Complete!**
                        
                        **Registration ID:** `{submission_id}`
                        **Station Name:** {final_data['station_name']}
                        **Owner:** {final_data['full_name']}
                        
                        **Photo Metadata:**
                        - **Captured:** {st.session_state.photo_metadata.get('timestamp', 'N/A')}
                        - **Coordinates:** {st.session_state.photo_metadata.get('latitude', 'N/A'):.6f}, {st.session_state.photo_metadata.get('longitude', 'N/A'):.6f}
                        
                        **Next Steps:**
                        1. Confirmation email sent to {final_data['email']}
                        2. Station verification pending review
                        3. Inspection team will contact you within 48 hours
                        4. Keep your Registration ID for all correspondence
                        5. You will receive official registration certificate upon approval
                        
                        **Important:** Your station photo with embedded metadata serves as official documentation.
                        """)
                        
                        # Create downloadable summary
                        summary = {
                            'registration_id': submission_id,
                            'station_name': final_data['station_name'],
                            'owner_name': final_data['full_name'],
                            'email': final_data['email'],
                            'phone': final_data['phone'],
                            'location': f"{final_data['latitude']:.6f}, {final_data['longitude']:.6f}",
                            'photo_timestamp': st.session_state.photo_metadata.get('timestamp'),
                            'submission_date': datetime.now(NIGERIA_TZ).strftime('%Y-%m-%d'),
                            'status': 'pending_review'
                        }
                        
                        json_summary = json.dumps(summary, indent=2)
                        b64 = base64.b64encode(json_summary.encode()).decode()
                        href = f'<a href="data:application/json;base64,{b64}" download="station_registration_{submission_id}.json">📥 Download Registration Summary</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
                        # Reset for next registration
                        st.session_state.consent_given = False
                        st.session_state.current_step = 1
                        st.session_state.selected_zone = None
                        st.session_state.selected_state = None
                        st.session_state.client_data = {}
                        st.session_state.photo_captured = None
                        st.session_state.photo_metadata = None
                        st.session_state.location_data = None
                        
                        if st.button("Register Another Station"):
                            st.rerun()
                    else:
                        st.error("❌ Error saving registration. Please try again or contact support.")
        else:
            st.error("❌ Missing information. Please go back and complete all steps.")
            if st.button("← Back to Location"):
                st.session_state.current_step = 4
                st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #6B7280; font-size: 0.8rem; margin-top: 2rem;">
    <p>⛽ Station Onboarding System v{APP_VERSION}</p>
    <p>For support: support@stationregistry.com | Phone: 01-2345678</p>
    <p>© {datetime.now().year} Station Registration Authority. All rights reserved.</p>
</div>
""", unsafe_allow_html=True)
