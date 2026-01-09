"""
Streamlit Camera & Geolocation App with Nigerian Regions
MIT License - For production use by registered businesses
Copyright (c) 2024 [Your IT Company Name]

This app captures photos with geolocation data during client onboarding.
Ensure compliance with Nigeria Data Protection Regulation (NDPR).
"""

import streamlit as st
import json
import base64
from datetime import datetime, timedelta
import pandas as pd
from PIL import Image
import io
import sqlite3
import csv
import hashlib
import pytz
from typing import Dict, List

# Page configuration
st.set_page_config(
    page_title="Nigerian Client Onboarding",
    page_icon="🇳🇬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
APP_VERSION = "2.0.0"
PRIVACY_POLICY_URL = "https://yourcompany.com/privacy"
TERMS_URL = "https://yourcompany.com/terms"
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

# State coordinates for map display (approximate)
STATE_COORDINATES = {
    "Lagos": {"lat": 6.5244, "lon": 3.3792},
    "Abuja": {"lat": 9.0765, "lon": 7.3986},
    "Kano": {"lat": 12.0022, "lon": 8.5920},
    "Rivers": {"lat": 4.8417, "lon": 7.0083},
    "Delta": {"lat": 5.5320, "lon": 5.8980},
    "Oyo": {"lat": 7.3775, "lon": 3.9470},
    "Kaduna": {"lat": 10.5264, "lon": 7.4388},
    "Plateau": {"lat": 9.8965, "lon": 8.8583},
    "Ondo": {"lat": 7.2574, "lon": 5.2058},
    "Enugu": {"lat": 6.4584, "lon": 7.5464},
    "Sokoto": {"lat": 13.0059, "lon": 5.2476},
    "Borno": {"lat": 11.8333, "lon": 13.1500},
    "Bauchi": {"lat": 10.3103, "lon": 9.8439},
    "Akwa Ibom": {"lat": 4.9057, "lon": 7.8537},
    "Ogun": {"lat": 6.9980, "lon": 3.4737},
    "Niger": {"lat": 9.6000, "lon": 6.5500},
    "Imo": {"lat": 5.4836, "lon": 7.0333},
    "Benue": {"lat": 7.3369, "lon": 8.7404},
    "Anambra": {"lat": 6.2107, "lon": 6.7989},
    "Adamawa": {"lat": 9.3265, "lon": 12.3984},
    "Abia": {"lat": 5.4527, "lon": 7.5248},
    "Edo": {"lat": 6.3427, "lon": 5.6250},
    "Taraba": {"lat": 8.7167, "lon": 11.3667},
    "Katsina": {"lat": 12.9908, "lon": 7.6000},
    "Kebbi": {"lat": 12.4500, "lon": 4.1994},
    "Cross River": {"lat": 5.8702, "lon": 8.5988},
    "Bayelsa": {"lat": 4.9261, "lon": 6.2642},
    "Yobe": {"lat": 12.0000, "lon": 11.5000},
    "Zamfara": {"lat": 12.1700, "lon": 6.6600},
    "Osun": {"lat": 7.5629, "lon": 4.5200},
    "Kogi": {"lat": 7.8000, "lon": 6.7333},
    "Nasarawa": {"lat": 8.5000, "lon": 8.5000},
    "Jigawa": {"lat": 12.7500, "lon": 9.9667},
    "Ekiti": {"lat": 7.6333, "lon": 5.2167},
    "Gombe": {"lat": 10.2897, "lon": 11.1711},
    "Ebonyi": {"lat": 6.3167, "lon": 8.1000},
    "Kwara": {"lat": 8.5000, "lon": 4.5500},
    "Federal Capital Territory (FCT)": {"lat": 9.0765, "lon": 7.3986}
}

# Initialize session state
def init_session_state():
    default_states = {
        'consent_given': False,
        'location_data': None,
        'photo_captured': None,
        'client_data': {},
        'submission_count': 0,
        'is_admin': False,
        'admin_authenticated': False,
        'view_submissions': False,
        'selected_region': None,
        'selected_state': None,
        'current_step': 1  # 1: Consent, 2: Info, 3: Photo, 4: Location, 5: Review
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
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin-bottom: 2rem;
    }
    .step {
        text-align: center;
        flex: 1;
        padding: 10px;
        border-bottom: 3px solid #E5E7EB;
        color: #9CA3AF;
    }
    .step.active {
        border-bottom: 3px solid #1E3A8A;
        color: #1E3A8A;
        font-weight: bold;
    }
    .step.completed {
        border-bottom: 3px solid #10B981;
        color: #10B981;
    }
    .step-number {
        background-color: #E5E7EB;
        color: #6B7280;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 5px;
    }
    .step.active .step-number {
        background-color: #1E3A8A;
        color: white;
    }
    .step.completed .step-number {
        background-color: #10B981;
        color: white;
    }
    .region-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.2rem;
        font-size: 0.9rem;
    }
    .north-central { background-color: #DBEAFE; color: #1E40AF; border: 1px solid #1E40AF; }
    .north-east { background-color: #FCE7F3; color: #BE185D; border: 1px solid #BE185D; }
    .north-west { background-color: #FEF3C7; color: #92400E; border: 1px solid #92400E; }
    .south-east { background-color: #D1FAE5; color: #065F46; border: 1px solid #065F46; }
    .south-south { background-color: #E0E7FF; color: #3730A3; border: 1px solid #3730A3; }
    .south-west { background-color: #FEE2E2; color: #991B1B; border: 1px solid #991B1B; }
    .admin-panel {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def save_submission_to_db(submission_data: Dict, photo_bytes: bytes = None):
    """Save submission to database"""
    try:
        c = DB_CONN.cursor()
        
        # Get IP address (simplified)
        ip_address = "127.0.0.1"
        
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
                id, submission_id, full_name, email, phone, geopolitical_zone, state, lga,
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

def get_region_class(region_name: str) -> str:
    """Get CSS class for region badge"""
    region_classes = {
        "North Central (Middle Belt)": "north-central",
        "North East": "north-east",
        "North West": "north-west",
        "South East": "south-east",
        "South South (Niger Delta)": "south-south",
        "South West": "south-west"
    }
    return region_classes.get(region_name, "")

# Step indicator component
def show_step_indicator():
    """Display step indicator"""
    steps = [
        {"num": 1, "label": "Consent", "key": "consent"},
        {"num": 2, "label": "Information", "key": "info"},
        {"num": 3, "label": "Photo", "key": "photo"},
        {"num": 4, "label": "Location", "key": "location"},
        {"num": 5, "label": "Review", "key": "review"}
    ]
    
    html = '<div class="step-indicator">'
    for step in steps:
        status = ""
        if step["num"] < st.session_state.current_step:
            status = "completed"
        elif step["num"] == st.session_state.current_step:
            status = "active"
        
        html += f'''
        <div class="step {status}">
            <div class="step-number">{step["num"]}</div>
            <div>{step["label"]}</div>
        </div>
        '''
    html += '</div>'
    
    st.markdown(html, unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🇳🇬 Nigerian Client Onboarding System</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Secure Registration with Photo & Location Verification</p>', unsafe_allow_html=True)

# Admin Login in Sidebar
with st.sidebar:
    st.markdown("### 🔐 Admin Access")
    
    if not st.session_state.admin_authenticated:
        admin_username = st.text_input("Admin Username", key="admin_user")
        admin_password = st.text_input("Admin Password", type="password", key="admin_pass")
        
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
        st.success(f"👋 Welcome, {st.session_state.admin_user[3]}")
        
        if st.button("📊 View Submissions Dashboard"):
            st.session_state.view_submissions = True
            st.rerun()
        
        if st.button("Logout"):
            st.session_state.admin_authenticated = False
            st.session_state.view_submissions = False
            st.rerun()

# Main App Logic
if st.session_state.admin_authenticated and st.session_state.view_submissions:
    # ADMIN DASHBOARD
    st.markdown("## 📊 Admin Dashboard - Client Submissions")
    
    # Dashboard metrics
    c = DB_CONN.cursor()
    c.execute("SELECT COUNT(*) FROM submissions")
    total_submissions = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'pending'")
    pending_submissions = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'approved'")
    approved_submissions = c.fetchone()[0]
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Submissions", total_submissions)
    with col2:
        st.metric("Pending Review", pending_submissions)
    with col3:
        st.metric("Approved", approved_submissions)
    
    # Filters
    st.markdown("### 🔍 Filter Options")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        filter_status = st.selectbox("Filter by Status", ["All", "pending", "approved", "rejected"])
    
    with col_f2:
        filter_zone = st.selectbox("Filter by Zone", ["All"] + list(NIGERIAN_REGIONS.keys()))
    
    with col_f3:
        filter_state = st.selectbox("Filter by State", ["All"] + [state for states in NIGERIAN_REGIONS.values() for state in states])
    
    # Fetch filtered submissions
    query = "SELECT * FROM submissions WHERE 1=1"
    params = []
    
    if filter_status != "All":
        query += " AND status = ?"
        params.append(filter_status)
    
    if filter_zone != "All":
        query += " AND geopolitical_zone = ?"
        params.append(filter_zone)
    
    if filter_state != "All":
        query += " AND state = ?"
        params.append(filter_state)
    
    query += " ORDER BY submission_timestamp DESC"
    
    c.execute(query, params)
    submissions = c.fetchall()
    
    # Display submissions
    if submissions:
        st.markdown(f"### 📋 Showing {len(submissions)} Submissions")
        
        # Convert to DataFrame
        df = pd.DataFrame(submissions, columns=[
            'ID', 'Submission ID', 'Full Name', 'Email', 'Phone', 'Geopolitical Zone', 'State',
            'LGA', 'Address', 'Latitude', 'Longitude', 'Photo', 'Consent Time', 'Submission Time',
            'Status', 'Notes', 'App Version', 'IP', 'Device Info'
        ])
        
        # Display table
        display_df = df[[
            'Submission ID', 'Full Name', 'Phone', 'Geopolitical Zone', 
            'State', 'Submission Time', 'Status'
        ]].copy()
        
        # Format datetime
        display_df['Submission Time'] = pd.to_datetime(display_df['Submission Time']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Show table
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # Detailed view
        st.markdown("### 👁️ View Submission Details")
        selected_id = st.selectbox("Select a submission:", display_df['Submission ID'].tolist())
        
        if selected_id:
            details = get_submission_details(selected_id)
            if details:
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    st.markdown("#### Client Information")
                    st.write(f"**Submission ID:** {details[1]}")
                    st.write(f"**Full Name:** {details[2]}")
                    st.write(f"**Email:** {details[3]}")
                    st.write(f"**Phone:** {details[4]}")
                    st.write(f"**Geopolitical Zone:** {details[5]}")
                    st.write(f"**State:** {details[6]}")
                    st.write(f"**LGA:** {details[7]}")
                    st.write(f"**Address:** {details[8]}")
                    st.write(f"**Coordinates:** {details[9]:.6f}, {details[10]:.6f}")
                    
                    # Show approximate location on Streamlit map
                    if details[9] and details[10]:
                        location_df = pd.DataFrame({
                            'lat': [details[9]],
                            'lon': [details[10]]
                        })
                        st.map(location_df, zoom=10)
                
                with col_d2:
                    st.markdown("#### Submission Details")
                    st.write(f"**Submission Time:** {details[13]}")
                    st.write(f"**Status:** {details[14]}")
                    st.write(f"**Notes:** {details[15]}")
                    
                    # Display photo if available
                    if details[11]:
                        try:
                            photo_bytes = details[11]
                            image = Image.open(io.BytesIO(photo_bytes))
                            st.image(image, caption="Client Photo", width=200)
                        except:
                            st.info("Photo not available for display")
                    
                    # Status update
                    st.markdown("#### Update Status")
                    new_status = st.selectbox("Change Status", ["pending", "approved", "rejected"])
                    admin_notes = st.text_area("Admin Notes (Optional)")
                    
                    if st.button("Update Status"):
                        if update_submission_status(selected_id, new_status, admin_notes):
                            st.success("✅ Status updated successfully!")
                            st.rerun()
        
        # Export data
        st.markdown("### 📤 Export Data")
        if st.button("Export All to CSV"):
            csv_data = export_submissions_to_csv()
            if csv_data:
                b64 = base64.b64encode(csv_data.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="submissions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv">📥 Download CSV File</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        # Regional statistics
        st.markdown("### 📊 Regional Statistics")
        c.execute("SELECT geopolitical_zone, COUNT(*) FROM submissions GROUP BY geopolitical_zone")
        zone_stats = c.fetchall()
        
        for zone, count in zone_stats:
            region_class = get_region_class(zone)
            st.markdown(f'<span class="region-badge {region_class}">{zone}: {count} submissions</span>', unsafe_allow_html=True)
    
    else:
        st.info("No submissions found with the current filters.")
    
    # Back to main app
    if st.button("← Back to Onboarding Form"):
        st.session_state.view_submissions = False
        st.rerun()

else:
    # MAIN ONBOARDING FORM
    
    # Show step indicator
    show_step_indicator()
    
    # Step 1: Consent
    if st.session_state.current_step == 1:
        st.markdown("## 📋 Step 1: Consent & Agreement")
        
        TERMS_CONTENT = f"""
        ## Terms & Conditions (NDPR Compliant)
        
        **Last Updated:** {datetime.now(NIGERIA_TZ).strftime('%d %B %Y')}
        
        ### Data Collection Consent
        By proceeding, you consent to:
        
        1. **Photo Capture**: For identity verification purposes
        2. **Location Data**: Collection of your state, LGA, and coordinates
        3. **Personal Information**: Name, phone number, and email address
        4. **Data Storage**: Secure storage as per NDPR guidelines
        
        ### Your Rights Under NDPR
        - Right to access your data
        - Right to correction
        - Right to deletion
        - Right to restrict processing
        
        **Full Terms:** {TERMS_URL}
        **Privacy Policy:** {PRIVACY_POLICY_URL}
        """
        
        with st.expander("📄 Read Terms & Conditions", expanded=True):
            st.markdown(TERMS_CONTENT)
        
        st.markdown('<div class="consent-box">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            consent_1 = st.checkbox("I consent to photo capture", key="consent1")
            consent_3 = st.checkbox("I agree to the Terms & Conditions", key="consent3")
        
        with col2:
            consent_2 = st.checkbox("I consent to location data collection", key="consent2")
            consent_4 = st.checkbox("I acknowledge my NDPR rights", key="consent4")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("✅ Give Consent & Continue", type="primary"):
            if all([consent_1, consent_2, consent_3, consent_4]):
                st.session_state.consent_given = True
                st.session_state.current_step = 2
                st.rerun()
            else:
                st.error("Please agree to all consent requirements")
    
    # Step 2: Personal Information
    elif st.session_state.current_step == 2:
        st.markdown("## 👤 Step 2: Personal Information")
        
        with st.form("personal_info"):
            col1, col2 = st.columns(2)
            
            with col1:
                full_name = st.text_input("Full Name *", placeholder="Enter your full name")
                email = st.text_input("Email Address *", placeholder="example@email.com")
            
            with col2:
                phone = st.text_input("Phone Number *", placeholder="08012345678")
                
                # Nigerian Geopolitical Zone
                selected_region = st.selectbox(
                    "Geopolitical Zone *",
                    list(NIGERIAN_REGIONS.keys()),
                    index=None,
                    placeholder="Select your zone"
                )
            
            # State selection based on region
            if selected_region:
                states = NIGERIAN_REGIONS[selected_region]
                selected_state = st.selectbox(
                    "State *",
                    states,
                    index=None,
                    placeholder="Select your state"
                )
                
                # LGA and Address
                if selected_state:
                    lga = st.text_input("Local Government Area (LGA) *", 
                                       placeholder="Enter your LGA")
                    address = st.text_area("Detailed Address", 
                                         placeholder="House number, street, area...")
            
            notes = st.text_area("Additional Information (Optional)", 
                               placeholder="Any special notes or requirements...")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.form_submit_button("← Back"):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col_btn2:
                if st.form_submit_button("💾 Save & Continue →", type="primary"):
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
                        st.session_state.current_step = 3
                        st.rerun()
                    else:
                        st.error("Please fill in all required fields (*)")
    
    # Step 3: Photo Capture
    elif st.session_state.current_step == 3:
        st.markdown("## 📷 Step 3: Photo Verification")
        
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.info("""
        **Photo Guidelines:**
        - Ensure good lighting
        - Face the camera directly
        - Remove sunglasses/hat
        - Make sure face is clearly visible
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div class="camera-frame">', unsafe_allow_html=True)
            photo = st.camera_input("Take your photo for verification", key="camera")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if photo:
                st.session_state.photo_captured = photo
                image = Image.open(photo)
                st.image(image, caption="Your Photo", width=200)
                st.success("✅ Photo captured!")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("← Back to Info"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col_btn3:
            if photo and st.button("Continue to Location →", type="primary"):
                st.session_state.current_step = 4
                st.rerun()
    
    # Step 4: Location Selection
    elif st.session_state.current_step == 4:
        st.markdown("## 📍 Step 4: Location Details")
        
        if st.session_state.selected_state in STATE_COORDINATES:
            # Show approximate location on map
            coords = STATE_COORDINATES[st.session_state.selected_state]
            location_df = pd.DataFrame({
                'lat': [coords['lat']],
                'lon': [coords['lon']]
            })
            
            st.info(f"**Selected State:** {st.session_state.selected_state}")
            st.map(location_df, zoom=8)
        
        # Manual coordinate input
        st.markdown("### Enter Your Exact Coordinates")
        
        col_lat, col_lon = st.columns(2)
        with col_lat:
            latitude = st.number_input("Latitude", format="%.6f", value=0.0, 
                                     help="Enter your latitude coordinate")
        with col_lon:
            longitude = st.number_input("Longitude", format="%.6f", value=0.0,
                                      help="Enter your longitude coordinate")
        
        # Verify address
        st.markdown("### Verify Your Address")
        if st.session_state.client_data:
            st.write(f"**State:** {st.session_state.client_data.get('state')}")
            st.write(f"**LGA:** {st.session_state.client_data.get('lga')}")
            st.write(f"**Address:** {st.session_state.client_data.get('address', 'Not provided')}")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("← Back to Photo"):
                st.session_state.current_step = 3
                st.rerun()
        
        with col_btn3:
            if st.button("Continue to Review →", type="primary"):
                if latitude != 0.0 and longitude != 0.0:
                    st.session_state.location_data = {
                        'latitude': latitude,
                        'longitude': longitude,
                        'source': 'manual_entry',
                        'timestamp': datetime.now(NIGERIA_TZ).isoformat()
                    }
                    st.session_state.current_step = 5
                    st.rerun()
                else:
                    st.error("Please enter valid coordinates")
    
    # Step 5: Review & Submit
    elif st.session_state.current_step == 5:
        st.markdown("## ✅ Step 5: Review & Submit")
        
        if all([st.session_state.client_data, st.session_state.photo_captured, st.session_state.location_data]):
            # Display summary
            st.markdown("### 📋 Submission Summary")
            
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                st.markdown("#### Personal Information")
                client_data = st.session_state.client_data
                st.write(f"**Name:** {client_data.get('full_name')}")
                st.write(f"**Email:** {client_data.get('email')}")
                st.write(f"**Phone:** {client_data.get('phone')}")
                
                region = client_data.get('geopolitical_zone')
                region_class = get_region_class(region)
                st.markdown(f'**Geopolitical Zone:** <span class="region-badge {region_class}">{region}</span>', unsafe_allow_html=True)
                
                st.write(f"**State:** {client_data.get('state')}")
                st.write(f"**LGA:** {client_data.get('lga')}")
                st.write(f"**Address:** {client_data.get('address', 'Not provided')}")
            
            with col_s2:
                st.markdown("#### Verification Data")
                
                # Show photo
                if st.session_state.photo_captured:
                    image = Image.open(st.session_state.photo_captured)
                    st.image(image, caption="Verification Photo", width=150)
                
                # Show location
                loc = st.session_state.location_data
                st.write(f"**Coordinates:** {loc['latitude']:.6f}, {loc['longitude']:.6f}")
                
                # Show on map
                location_df = pd.DataFrame({
                    'lat': [loc['latitude']],
                    'lon': [loc['longitude']]
                })
                st.map(location_df, zoom=12)
            
            # Final submission
            st.markdown("---")
            st.markdown("### 🚀 Ready to Submit")
            
            if st.button("Submit Onboarding Application", type="primary", use_container_width=True):
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
                    **Thank you for registering!**
                    
                    **Next Steps:**
                    1. Confirmation sent to {final_data['email']}
                    2. Your application is pending review
                    3. You'll be contacted within 48 hours
                    """)
                    
                    # Show completion details
                    with st.expander("📄 View Submission Details", expanded=True):
                        st.json({
                            'submission_id': submission_id,
                            'name': final_data['full_name'],
                            'zone': final_data['geopolitical_zone'],
                            'state': final_data['state'],
                            'submission_time': final_data['submission_timestamp']
                        }, expanded=False)
                    
                    # Reset for next submission
                    st.session_state.submission_count += 1
                    st.session_state.current_step = 1
                    st.session_state.consent_given = False
                    st.session_state.photo_captured = None
                    st.session_state.location_data = None
                    st.session_state.client_data = {}
                    
                    if st.button("Start New Registration"):
                        st.rerun()
                else:
                    st.error("Error saving submission. Please try again.")
        
        else:
            st.error("Missing information. Please go back and complete all steps.")
            if st.button("← Back to Location"):
                st.session_state.current_step = 4
                st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div class="footer">
    <p>🇳🇬 Nigerian Client Onboarding System v{APP_VERSION} | NDPR Compliant</p>
    <p>MIT Licensed © 2024 | For support: support@yourcompany.ng</p>
    <p>Total submissions this session: {st.session_state.submission_count}</p>
</div>
""", unsafe_allow_html=True)
