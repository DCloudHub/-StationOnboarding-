"""
Streamlit Camera & Geolocation App with Nigerian Regions
MIT License - For production use by registered businesses
Copyright (c) 2026 GT Solutions LTD

This app captures photos with geolocation data during client onboarding.
Ensure compliance with local privacy laws (GDPR, NDPR, etc.).
"""

import streamlit as st
import json
import base64
from datetime import datetime, timedelta
import pandas as pd
from PIL import Image
import requests
import folium
from streamlit_folium import folium_static, st_folium
import io
import sqlite3
import csv
from typing import Dict, List, Optional
import hashlib
import pytz

# Page configuration
st.set_page_config(
    page_title="Client Onboarding - Photo & Location",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
APP_VERSION = "1.0.0"
PRIVACY_POLICY_URL = "https://yourcompany.com/privacy"
TERMS_URL = "https://yourcompany.com/terms"
GOOGLE_MAPS_API_KEY = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
NIGERIA_TZ = pytz.timezone('Africa/Lagos')

# Nigerian Geopolitical Zones and States
NIGERIAN_REGIONS = {
    "North Central (Middle Belt)": [
        "Benue", "Kogi", "Kwara", "Nasarawa", "Niger", "Plateau", "Federal Capital Territory (FCT)"
    ],
    "North East": [
        "Adamawa", "Bauchi", "Borno", "Gombe", "Taraba", "Yobe"
    ],
    "North West": [
        "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Sokoto", "Zamfara"
    ],
    "South East": [
        "Abia", "Anambra", "Ebonyi", "Enugu", "Imo"
    ],
    "South South (Niger Delta)": [
        "Akwa Ibom", "Bayelsa", "Cross River", "Delta", "Edo", "Rivers"
    ],
    "South West": [
        "Ekiti", "Lagos", "Ogun", "Ondo", "Osun", "Oyo"
    ]
}

# Initialize session state
def init_session_state():
    default_states = {
        'consent_given': False,
        'location_data': None,
        'photo_captured': None,
        'client_data': {},
        'submission_count': 0,
        'map_center': [9.081999, 8.675277],  # Center of Nigeria
        'map_zoom': 6,
        'selected_location': None,
        'map_click_data': None,
        'is_admin': False,
        'admin_authenticated': False,
        'view_submissions': False,
        'selected_region': None,
        'selected_state': None
    }
    
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Database setup
def init_database():
    """Initialize SQLite database for storing submissions"""
    conn = sqlite3.connect('submissions.db', check_same_thread=False)
    c = conn.cursor()
    
    # Create submissions table
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
            photo_data BLOB,
            consent_timestamp TEXT,
            submission_timestamp TEXT,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            app_version TEXT,
            ip_address TEXT,
            device_info TEXT
        )
    ''')
    
    # Create admin users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            full_name TEXT,
            email TEXT,
            role TEXT DEFAULT 'viewer',
            created_at TEXT,
            last_login TEXT
        )
    ''')
    
    # Create default admin if not exists
    c.execute("SELECT COUNT(*) FROM admin_users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        # Default password: Admin123! (should be changed on first login)
        password_hash = hashlib.sha256('Admin123!'.encode()).hexdigest()
        c.execute('''
            INSERT INTO admin_users (username, password_hash, full_name, email, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', password_hash, 'System Administrator', 'admin@yourcompany.com', 'admin', datetime.now(NIGERIA_TZ).isoformat()))
    
    conn.commit()
    return conn

# Initialize database
DB_CONN = init_database()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4B5563;
        text-align: center;
        margin-bottom: 2rem;
    }
    .consent-box {
        border: 2px solid #E5E7EB;
        border-radius: 10px;
        padding: 1.5rem;
        background-color: #F9FAFB;
        margin: 1rem 0;
    }
    .data-box {
        border: 2px solid #10B981;
        border-radius: 10px;
        padding: 1.5rem;
        background-color: #ECFDF5;
        margin: 1rem 0;
    }
    .warning-box {
        border: 2px solid #F59E0B;
        border-radius: 10px;
        padding: 1rem;
        background-color: #FFFBEB;
        margin: 1rem 0;
    }
    .map-box {
        border: 3px solid #1E3A8A;
        border-radius: 10px;
        padding: 0;
        margin: 1rem 0;
        height: 500px;
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
    .camera-frame {
        border: 3px solid #1E3A8A;
        border-radius: 10px;
        padding: 10px;
        background-color: #000;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #6B7280;
        font-size: 0.8rem;
    }
    .map-instructions {
        background-color: #F0F9FF;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .admin-panel {
        background-color: #F8F9FA;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #6C757D;
    }
    .data-table {
        font-size: 0.9rem;
    }
    .status-pending { color: #F59E0B; font-weight: bold; }
    .status-approved { color: #10B981; font-weight: bold; }
    .status-rejected { color: #EF4444; font-weight: bold; }
    .region-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 0.1rem;
    }
    .north-central { background-color: #DBEAFE; color: #1E40AF; }
    .north-east { background-color: #FCE7F3; color: #BE185D; }
    .north-west { background-color: #FEF3C7; color: #92400E; }
    .south-east { background-color: #D1FAE5; color: #065F46; }
    .south-south { background-color: #E0E7FF; color: #3730A3; }
    .south-west { background-color: #FEE2E2; color: #991B1B; }
</style>
""", unsafe_allow_html=True)

# Helper functions
def save_submission_to_db(submission_data: Dict, photo_bytes: bytes = None):
    """Save submission to database"""
    try:
        c = DB_CONN.cursor()
        
        # Get IP address (simplified - in production use proper method)
        ip_address = "127.0.0.1"  # Default
        
        c.execute('''
            INSERT INTO submissions (
                submission_id, full_name, email, phone, geopolitical_zone, state, lga, address,
                latitude, longitude, photo_data, consent_timestamp, submission_timestamp,
                status, notes, app_version, ip_address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            photo_bytes,
            submission_data.get('consent_timestamp'),
            submission_data.get('submission_timestamp'),
            'pending',
            submission_data.get('notes', ''),
            submission_data.get('app_version'),
            ip_address
        ))
        
        DB_CONN.commit()
        return True
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return False

def get_all_submissions():
    """Retrieve all submissions from database"""
    try:
        c = DB_CONN.cursor()
        c.execute('''
            SELECT 
                id, submission_id, full_name, email, phone, geopolitical_zone, state,
                latitude, longitude, submission_timestamp, status, notes
            FROM submissions 
            ORDER BY submission_timestamp DESC
        ''')
        return c.fetchall()
    except Exception as e:
        st.error(f"Error fetching submissions: {str(e)}")
        return []

def get_submission_details(submission_id: str):
    """Get detailed information for a specific submission"""
    try:
        c = DB_CONN.cursor()
        c.execute('''
            SELECT * FROM submissions WHERE submission_id = ?
        ''', (submission_id,))
        return c.fetchone()
    except:
        return None

def update_submission_status(submission_id: str, status: str, admin_notes: str = ""):
    """Update submission status"""
    try:
        c = DB_CONN.cursor()
        c.execute('''
            UPDATE submissions 
            SET status = ?, notes = COALESCE(notes, '') || '\nAdmin: ' || ?
            WHERE submission_id = ?
        ''', (status, admin_notes, submission_id))
        DB_CONN.commit()
        return True
    except:
        return False

def export_submissions_to_csv():
    """Export all submissions to CSV format"""
    try:
        c = DB_CONN.cursor()
        c.execute('SELECT * FROM submissions')
        rows = c.fetchall()
        
        if not rows:
            return None
        
        # Get column names
        c.execute('PRAGMA table_info(submissions)')
        columns = [column[1] for column in c.fetchall()]
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        
        return output.getvalue()
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

# JavaScript for initial geolocation
def get_initial_location_js():
    """JavaScript to get initial geolocation for map centering"""
    return """
    <script>
    function getInitialLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const data = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    };
                    
                    const elem = document.createElement('div');
                    elem.id = 'initialLocation';
                    elem.innerText = JSON.stringify(data);
                    document.body.appendChild(elem);
                    
                    const event = new Event('initialLocationCaptured');
                    document.dispatchEvent(event);
                }
            );
        }
    }
    window.addEventListener('load', getInitialLocation);
    </script>
    """

# Header
st.markdown('<h1 class="main-header">📍 Nigerian Client Onboarding System</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Secure Photo Capture with Location Selection for Nigerian Regions</p>', unsafe_allow_html=True)

# Admin Login Section (Hidden in sidebar)
with st.sidebar:
    if not st.session_state.admin_authenticated:
        st.markdown("### 🔒 Admin Login")
        admin_username = st.text_input("Username", key="admin_user")
        admin_password = st.text_input("Password", type="password", key="admin_pass")
        
        if st.button("Login as Admin"):
            if admin_username and admin_password:
                password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
                c = DB_CONN.cursor()
                c.execute('SELECT * FROM admin_users WHERE username = ? AND password_hash = ?', 
                         (admin_username, password_hash))
                admin_user = c.fetchone()
                
                if admin_user:
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_user = admin_user
                    st.success(f"Welcome, {admin_user[3]}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        st.success(f"👋 Welcome, {st.session_state.admin_user[3]}!")
        if st.button("Logout"):
            st.session_state.admin_authenticated = False
            st.session_state.view_submissions = False
            st.rerun()

# Main App Logic
if st.session_state.admin_authenticated and st.session_state.view_submissions:
    # ADMIN DASHBOARD VIEW
    st.markdown("## 📊 Admin Dashboard - Client Submissions")
    
    # Dashboard metrics
    c = DB_CONN.cursor()
    c.execute("SELECT COUNT(*) FROM submissions")
    total_submissions = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'pending'")
    pending_submissions = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'approved'")
    approved_submissions = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM submissions WHERE DATE(submission_timestamp) = DATE('now')")
    today_submissions = c.fetchone()[0]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Submissions", total_submissions)
    with col2:
        st.metric("Pending Review", pending_submissions, delta=f"{pending_submissions/total_submissions*100:.1f}%" if total_submissions > 0 else "0%")
    with col3:
        st.metric("Approved", approved_submissions)
    with col4:
        st.metric("Today's Submissions", today_submissions)
    
    # Filters
    st.markdown("### 🔍 Filter Submissions")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        filter_status = st.selectbox("Status", ["All", "pending", "approved", "rejected"])
    
    with col_f2:
        filter_zone = st.selectbox("Geopolitical Zone", ["All"] + list(NIGERIAN_REGIONS.keys()))
    
    with col_f3:
        filter_date = st.date_input("Submission Date", value=None)
    
    # Fetch filtered submissions
    query = "SELECT * FROM submissions WHERE 1=1"
    params = []
    
    if filter_status != "All":
        query += " AND status = ?"
        params.append(filter_status)
    
    if filter_zone != "All":
        query += " AND geopolitical_zone = ?"
        params.append(filter_zone)
    
    if filter_date:
        query += " AND DATE(submission_timestamp) = ?"
        params.append(filter_date.isoformat())
    
    query += " ORDER BY submission_timestamp DESC"
    
    c.execute(query, params)
    submissions = c.fetchall()
    
    # Display submissions table
    if submissions:
        st.markdown(f"### 📋 Showing {len(submissions)} Submissions")
        
        # Convert to DataFrame for display
        df = pd.DataFrame(submissions, columns=[
            'ID', 'Submission ID', 'Full Name', 'Email', 'Phone', 'Geopolitical Zone', 'State',
            'LGA', 'Address', 'Latitude', 'Longitude', 'Photo', 'Consent Time', 'Submission Time',
            'Status', 'Notes', 'App Version', 'IP', 'Device Info'
        ])
        
        # Display relevant columns
        display_df = df[[
            'Submission ID', 'Full Name', 'Email', 'Phone', 'Geopolitical Zone', 
            'State', 'Submission Time', 'Status'
        ]].copy()
        
        # Format submission time
        display_df['Submission Time'] = pd.to_datetime(display_df['Submission Time']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Add status colors
        def color_status(val):
            if val == 'pending':
                return 'color: #F59E0B'
            elif val == 'approved':
                return 'color: #10B981'
            elif val == 'rejected':
                return 'color: #EF4444'
            return ''
        
        styled_df = display_df.style.applymap(color_status, subset=['Status'])
        
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # Detailed view
        st.markdown("### 👁️ Detailed View")
        selected_id = st.selectbox("Select submission to view details:", 
                                  display_df['Submission ID'].tolist())
        
        if selected_id:
            details = get_submission_details(selected_id)
            if details:
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    st.markdown("#### Client Information")
                    st.write(f"**Name:** {details[2]}")
                    st.write(f"**Email:** {details[3]}")
                    st.write(f"**Phone:** {details[4]}")
                    st.write(f"**Zone:** {details[5]}")
                    st.write(f"**State:** {details[6]}")
                    st.write(f"**LGA:** {details[7]}")
                    st.write(f"**Address:** {details[8]}")
                    
                    # Show location on map
                    if details[9] and details[10]:
                        map_df = pd.DataFrame({
                            'lat': [details[9]],
                            'lon': [details[10]]
                        })
                        st.map(map_df, zoom=12)
                
                with col_d2:
                    st.markdown("#### Submission Details")
                    st.write(f"**Submission ID:** {details[1]}")
                    st.write(f"**Submission Time:** {details[13]}")
                    st.write(f"**Status:** {details[14]}")
                    st.write(f"**Notes:** {details[15]}")
                    st.write(f"**Coordinates:** {details[9]:.6f}, {details[10]:.6f}")
                    
                    # Status update
                    st.markdown("#### Update Status")
                    new_status = st.selectbox("New Status", ["pending", "approved", "rejected"])
                    admin_notes = st.text_area("Admin Notes")
                    
                    if st.button("Update Status"):
                        if update_submission_status(selected_id, new_status, admin_notes):
                            st.success("Status updated successfully!")
                            st.rerun()
                    
                    # View photo if available
                    if details[11]:
                        try:
                            photo_bytes = details[11]
                            image = Image.open(io.BytesIO(photo_bytes))
                            st.image(image, caption="Client Photo", width=200)
                        except:
                            st.info("Photo not available for display")
        
        # Export options
        st.markdown("### 📤 Export Data")
        col_e1, col_e2 = st.columns(2)
        
        with col_e1:
            if st.button("Export to CSV"):
                csv_data = export_submissions_to_csv()
                if csv_data:
                    b64 = base64.b64encode(csv_data.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="submissions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv">📥 Download CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
        
        with col_e2:
            # Statistics by region
            st.markdown("#### 📊 Regional Distribution")
            c.execute("SELECT geopolitical_zone, COUNT(*) FROM submissions GROUP BY geopolitical_zone")
            zone_stats = c.fetchall()
            
            for zone, count in zone_stats:
                st.write(f"{zone}: {count} submissions")
    
    else:
        st.info("No submissions found matching the filters.")
    
    # Back to main app
    if st.button("← Back to Onboarding Form"):
        st.session_state.view_submissions = False
        st.rerun()

else:
    # MAIN ONBOARDING FORM
    
    # Terms and Conditions
    TERMS_CONTENT = f"""
    ## Terms & Conditions and Privacy Notice (NDPR Compliant)
    
    **Last Updated:** {datetime.now(NIGERIA_TZ).strftime('%Y-%m-%d')}
    
    ### 1. Consent to Data Collection
    By using this application, you consent to collection of your data in compliance with Nigeria Data Protection Regulation (NDPR) 2019.
    
    ### 2. Data We Collect
    - **Personal Information**: Name, email, phone number
    - **Location Data**: State, LGA, and precise coordinates
    - **Photograph**: For identity verification
    - **Demographic Data**: Geopolitical zone information
    
    ### 3. Purpose of Data Collection
    - Service delivery planning
    - Demographic analysis
    - Fraud prevention
    - Regulatory compliance
    
    ### 4. Your Rights Under NDPR
    - Right to be informed
    - Right to access
    - Right to rectification
    - Right to erasure
    - Right to restrict processing
    - Right to data portability
    - Right to object
    - Rights related to automated decision making
    
    **Full NDPR Compliance:** {TERMS_URL}
    **Privacy Policy:** {PRIVACY_POLICY_URL}
    """
    
    # Consent Section
    if not st.session_state.consent_given:
        st.markdown("## 📋 Consent Agreement (NDPR Compliant)")
        
        with st.expander("📄 Read Complete Terms & Conditions", expanded=True):
            st.markdown(TERMS_CONTENT)
        
        st.markdown('<div class="consent-box">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            consent_1 = st.checkbox(
                "I consent to camera access for photo capture",
                help="Required for identity verification"
            )
        
        with col2:
            consent_2 = st.checkbox(
                "I consent to location and demographic data collection",
                help="Required for service delivery planning"
            )
        
        consent_3 = st.checkbox(
            "I have read and agree to the Terms & Conditions and Privacy Policy",
            help="Required to proceed"
        )
        
        consent_4 = st.checkbox(
            "I acknowledge my rights under Nigeria Data Protection Regulation (NDPR)",
            help="Required for NDPR compliance"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("✅ Give Consent & Proceed", type="primary"):
            if consent_1 and consent_2 and consent_3 and consent_4:
                st.session_state.consent_given = True
                st.components.v1.html(get_initial_location_js(), height=0)
                st.rerun()
            else:
                st.error("⚠️ Please agree to all consent requirements to proceed")
        
        st.markdown("---")
        st.markdown(f'<div class="footer">App Version {APP_VERSION} | NDPR Compliant | MIT Licensed © 2024</div>', unsafe_allow_html=True)
        st.stop()
    
    # Main Onboarding Form
    st.success("✅ Consent recorded. Please complete your information.")
    
    col_main_left, col_main_right = st.columns([1, 1])
    
    with col_main_left:
        # Client Information Form
        st.markdown("### 👤 Personal Information")
        with st.form("client_info"):
            full_name = st.text_input("Full Name *", placeholder="Enter your full name")
            email = st.text_input("Email Address *", placeholder="your.email@example.com")
            phone = st.text_input("Phone Number *", placeholder="e.g., 08012345678")
            
            # Nigerian Geopolitical Zone Selection
            st.markdown("### 🇳🇬 Location Information")
            
            # Region selection with visual badges
            selected_region = st.selectbox(
                "Select Geopolitical Zone *",
                list(NIGERIAN_REGIONS.keys()),
                index=None,
                placeholder="Choose your geopolitical zone"
            )
            
            # State selection based on region
            if selected_region:
                states = NIGERIAN_REGIONS[selected_region]
                selected_state = st.selectbox(
                    "Select State *",
                    states,
                    index=None,
                    placeholder="Choose your state"
                )
                
                # LGA selection (simplified - in production, load actual LGAs)
                if selected_state:
                    lga = st.text_input("Local Government Area (LGA) *", 
                                       placeholder="Enter your LGA")
                    
                    # Address
                    address = st.text_area("Detailed Address", 
                                         placeholder="House number, street, area, town...")
            
            # Additional notes
            notes = st.text_area("Additional Information", 
                               placeholder="Any special requirements or notes...")
            
            submit_info = st.form_submit_button("💾 Save Information")
            
            if submit_info:
                if all([full_name, email, phone, selected_region, selected_state, lga]):
                    st.session_state.client_data = {
                        'full_name': full_name,
                        'email': email,
                        'phone': phone,
                        'geopolitical_zone': selected_region,
                        'state': selected_state,
                        'lga': lga,
                        'address': address,
                        'notes': notes,
                        'timestamp': datetime.now(NIGERIA_TZ).isoformat()
                    }
                    st.session_state.selected_region = selected_region
                    st.session_state.selected_state = selected_state
                    st.success("Information saved successfully!")
                else:
                    st.error("Please fill in all required fields (*)")
        
        # Photo Capture Section
        st.markdown("### 📷 Photo Capture")
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.info("""
        **Instructions for Nigerian ID Verification:**
        1. Ensure good lighting
        2. Face the camera directly
        3. Remove cap/headgear (except for religious purposes)
        4. Ensure clear view of face
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Camera input
        st.markdown('<div class="camera-frame">', unsafe_allow_html=True)
        photo = st.camera_input("Take photo for verification", key="camera")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if photo:
            st.session_state.photo_captured = photo
            st.success("✅ Photo captured successfully!")
            
            # Display captured photo
            image = Image.open(photo)
            st.image(image, caption="Verification Photo", width=250)
    
    with col_main_right:
        # Location Selection Section
        st.markdown("### 📍 Select Your Exact Location")
        
        # Map instructions
        st.markdown('<div class="map-instructions">', unsafe_allow_html=True)
        st.markdown("""
        **Map Instructions:**
        1. **Zoom/Pan**: Find your exact location in Nigeria
        2. **Click**: Click on your exact house/building location
        3. **Verify**: Check the coordinates match your address
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Initialize map center based on selected state
        map_center = st.session_state.map_center
        if st.session_state.selected_state:
            # Approximate coordinates for Nigerian states (simplified)
            state_coords = {
                "Lagos": [6.5244, 3.3792],
                "Abuja": [9.0765, 7.3986],
                "Kano": [12.0022, 8.5920],
                # Add more states as needed
            }
            if st.session_state.selected_state in state_coords:
                map_center = state_coords[st.session_state.selected_state]
                st.session_state.map_center = map_center
                st.session_state.map_zoom = 12
        
        # Create and display map
        marker_location = st.session_state.selected_location
        st.markdown('<div class="map-box">', unsafe_allow_html=True)
        
        m = folium.Map(
            location=map_center,
            zoom_start=st.session_state.map_zoom,
            tiles='OpenStreetMap',
            control_scale=True
        )
        
        # Add Nigeria boundary overlay (optional)
        folium.TileLayer('CartoDB positron').add_to(m)
        
        # Add click event
        m.add_child(folium.LatLngPopup())
        
        # Add marker if selected
        if marker_location:
            folium.Marker(
                location=marker_location,
                popup=f"Selected Location<br>Lat: {marker_location[0]:.6f}<br>Lon: {marker_location[1]:.6f}",
                icon=folium.Icon(color='red', icon='home')
            ).add_to(m)
        
        # Display map
        map_data = st_folium(
            m,
            width=700,
            height=450,
            returned_objects=["last_clicked", "center", "zoom"]
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Handle map interactions
        if map_data and map_data.get("last_clicked"):
            click_lat = map_data["last_clicked"]["lat"]
            click_lng = map_data["last_clicked"]["lng"]
            
            st.session_state.selected_location = [click_lat, click_lng]
            st.session_state.location_data = {
                'latitude': click_lat,
                'longitude': click_lng,
                'source': 'map_selection',
                'map_zoom': map_data.get("zoom", st.session_state.map_zoom),
                'timestamp': datetime.now(NIGERIA_TZ).isoformat()
            }
            
            # Display selection
            st.markdown('<div class="data-box">', unsafe_allow_html=True)
            st.success("📍 Location selected!")
            
            col_lat, col_lng = st.columns(2)
            with col_lat:
                st.metric("Latitude", f"{click_lat:.6f}")
            with col_lng:
                st.metric("Longitude", f"{click_lng:.6f}")
            
            st.caption(f"**State:** {st.session_state.selected_state}")
            st.caption(f"**LGA:** {st.session_state.client_data.get('lga', 'Not specified')}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("✅ Confirm This Location", type="primary"):
                st.success("Location confirmed!")
    
    # Final Submission
    st.markdown("---")
    st.markdown("## ✅ Review & Submit")
    
    if st.session_state.client_data and st.session_state.photo_captured and st.session_state.location_data:
        # Display summary
        col_sum1, col_sum2, col_sum3 = st.columns(3)
        
        with col_sum1:
            st.metric("👤 Client", st.session_state.client_data.get('full_name', 'N/A'))
            st.caption(f"📧 {st.session_state.client_data.get('email', 'N/A')}")
        
        with col_sum2:
            region = st.session_state.client_data.get('geopolitical_zone', 'N/A')
            state = st.session_state.client_data.get('state', 'N/A')
            st.metric("📍 Location", state)
            st.caption(f"🗺️ {region}")
        
        with col_sum3:
            if st.session_state.location_data:
                loc = st.session_state.location_data
                st.metric("📌 Coordinates", "Captured")
                st.caption(f"Lat: {loc['latitude']:.4f}, Lon: {loc['longitude']:.4f}")
    
    # Submit button
    if st.button("🚀 Complete Nigerian Onboarding", type="primary", use_container_width=True):
        if not all([st.session_state.client_data, st.session_state.photo_captured, st.session_state.location_data]):
            st.error("Please complete all sections before submitting")
        else:
            # Generate submission ID
            submission_id = f"NG-{datetime.now(NIGERIA_TZ).strftime('%Y%m%d-%H%M%S')}"
            
            # Prepare final data
            final_data = {
                **st.session_state.client_data,
                'latitude': st.session_state.location_data['latitude'],
                'longitude': st.session_state.location_data['longitude'],
                'submission_id': submission_id,
                'app_version': APP_VERSION,
                'consent_timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                'submission_timestamp': datetime.now(NIGERIA_TZ).isoformat()
            }
            
            # Save photo bytes
            photo_bytes = None
            if st.session_state.photo_captured:
                photo_bytes = st.session_state.photo_captured.read()
            
            # Save to database
            if save_submission_to_db(final_data, photo_bytes):
                st.balloons()
                st.success(f"""
                🎉 **Onboarding Complete!**
                
                **Submission ID:** `{submission_id}`
                **Thank you,** {final_data['full_name']}!
                
                **Next Steps:**
                1. Confirmation email sent to {final_data['email']}
                2. Your submission is now pending review
                3. Service team will contact you within 48 hours
                4. Keep your Submission ID for reference
                """)
                
                # Display submission details
                with st.expander("📋 View Your Submission", expanded=True):
                    st.json({
                        'submission_id': submission_id,
                        'client_name': final_data['full_name'],
                        'geopolitical_zone': final_data['geopolitical_zone'],
                        'state': final_data['state'],
                        'lga': final_data['lga'],
                        'coordinates': f"{final_data['latitude']:.6f}, {final_data['longitude']:.6f}",
                        'submission_time': final_data['submission_timestamp']
                    }, expanded=False)
                
                # Reset for next submission
                st.session_state.submission_count += 1
                st.session_state.photo_captured = None
                st.session_state.location_data = None
                st.session_state.selected_location = None
                st.session_state.client_data = {}
                
                if st.button("➕ Start New Onboarding"):
                    st.rerun()
            else:
                st.error("Error saving submission. Please try again or contact support.")

# Admin Access Button (visible only to admins)
if st.session_state.admin_authenticated and not st.session_state.view_submissions:
    if st.sidebar.button("📊 View All Submissions"):
        st.session_state.view_submissions = True
        st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div class="footer">
    <p>🇳🇬 Nigerian Client Onboarding System v{APP_VERSION}</p>
    <p>NDPR Compliant | MIT Licensed © 2024 | For support: support@yourcompany.ng</p>
    <p>Submissions this session: {st.session_state.submission_count}</p>
</div>
""", unsafe_allow_html=True)
