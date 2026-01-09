"""
Station Onboarding
MIT License - For production use by registered businesses
Copyright (c) 2024 Station Onboarding System
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
    page_title="Station Onboarding",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
APP_VERSION = "1.0.0"
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
        'current_step': 1
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
            app_version TEXT
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
        password_hash = hashlib.sha256('Admin123!'.encode()).hexdigest()
        c.execute('''
            INSERT INTO admin_users (username, password_hash, full_name, email, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', password_hash, 'System Administrator', 'admin@yourcompany.com', 'admin', datetime.now(NIGERIA_TZ).isoformat()))
    
    conn.commit()
    return conn

# Initialize database
DB_CONN = init_database()

# Helper functions
def save_submission_to_db(submission_data: Dict, photo_bytes: bytes = None):
    """Save submission to database"""
    try:
        c = DB_CONN.cursor()
        
        c.execute('''
            INSERT INTO submissions (
                submission_id, full_name, email, phone, geopolitical_zone, state, lga, address,
                latitude, longitude, photo_data, consent_timestamp, submission_timestamp,
                status, notes, app_version
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
            photo_bytes,
            submission_data.get('consent_timestamp'),
            submission_data.get('submission_timestamp'),
            'pending',
            submission_data.get('notes', ''),
            submission_data.get('app_version')
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
        
        c.execute('PRAGMA table_info(submissions)')
        columns = [column[1] for column in c.fetchall()]
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        
        return output.getvalue()
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

# Custom CSS with simpler header
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4B5563;
        text-align: center;
        margin-bottom: 2rem;
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
    }
    .step.active {
        background-color: #1E3A8A;
        color: white;
        border-radius: 5px;
        font-weight: bold;
    }
    .step-number {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 5px;
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
</style>
""", unsafe_allow_html=True)

# Step indicator component
def show_step_indicator():
    """Display step indicator"""
    steps = ["Consent", "Information", "Photo", "Location", "Review"]
    
    html = '<div class="step-indicator">'
    for i, step in enumerate(steps, 1):
        status = "active" if i == st.session_state.current_step else ""
        html += f'''
        <div class="step {status}">
            <div class="step-number">{i}</div>
            <div>{step}</div>
        </div>
        '''
    html += '</div>'
    
    # Use st.markdown with unsafe_allow_html=True
    st.markdown(html, unsafe_allow_html=True)

# SIMPLE HEADER
st.markdown('<h1 class="main-header">📍 Station Onboarding</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Complete your registration in 5 simple steps</p>', unsafe_allow_html=True)

# Admin Login in Sidebar
with st.sidebar:
    if not st.session_state.admin_authenticated:
        st.markdown("### Admin Login")
        admin_username = st.text_input("Username")
        admin_password = st.text_input("Password", type="password")
        
        if st.button("Login"):
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
        st.success(f"Welcome, {st.session_state.admin_user[3]}")
        if st.button("View Submissions"):
            st.session_state.view_submissions = True
            st.rerun()
        if st.button("Logout"):
            st.session_state.admin_authenticated = False
            st.session_state.view_submissions = False
            st.rerun()

# Main App Logic
if st.session_state.admin_authenticated and st.session_state.view_submissions:
    # ADMIN DASHBOARD
    st.markdown("## Admin Dashboard")
    
    c = DB_CONN.cursor()
    c.execute("SELECT COUNT(*) FROM submissions")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'pending'")
    pending = c.fetchone()[0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Submissions", total)
    with col2:
        st.metric("Pending Review", pending)
    
    submissions = get_all_submissions()
    if submissions:
        df = pd.DataFrame(submissions, columns=[
            'ID', 'Submission ID', 'Full Name', 'Email', 'Phone', 'Zone', 'State',
            'LGA', 'Lat', 'Lon', 'Time', 'Status', 'Notes'
        ])
        
        display_df = df[['Submission ID', 'Full Name', 'Phone', 'Zone', 'State', 'Time', 'Status']]
        display_df['Time'] = pd.to_datetime(display_df['Time']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(display_df, use_container_width=True, height=300)
        
        if st.button("Export to CSV"):
            csv_data = export_submissions_to_csv()
            if csv_data:
                b64 = base64.b64encode(csv_data.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="submissions.csv">📥 Download CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
    
    if st.button("← Back to Form"):
        st.session_state.view_submissions = False
        st.rerun()

else:
    # MAIN ONBOARDING FORM
    show_step_indicator()
    
    # Step 1: Consent
    if st.session_state.current_step == 1:
        st.markdown("### Step 1: Consent & Agreement")
        
        with st.expander("📄 Read Terms & Conditions", expanded=True):
            st.markdown(f"""
            ## Terms & Conditions
            
            **Last Updated:** {datetime.now(NIGERIA_TZ).strftime('%d %B %Y')}
            
            ### Data Collection Consent
            By proceeding, you consent to:
            
            1. **Photo Capture**: For identity verification
            2. **Location Data**: Collection of your location information
            3. **Personal Information**: Name, phone, email
            4. **Data Storage**: Secure storage as per regulations
            
            **Full Terms:** {TERMS_URL}
            **Privacy Policy:** {PRIVACY_POLICY_URL}
            """)
        
        col1, col2 = st.columns(2)
        with col1:
            consent_1 = st.checkbox("I consent to photo capture")
            consent_3 = st.checkbox("I agree to Terms & Conditions")
        
        with col2:
            consent_2 = st.checkbox("I consent to location data collection")
            consent_4 = st.checkbox("I acknowledge my data rights")
        
        if st.button("✅ Give Consent & Continue", type="primary"):
            if all([consent_1, consent_2, consent_3, consent_4]):
                st.session_state.consent_given = True
                st.session_state.current_step = 2
                st.rerun()
            else:
                st.error("Please agree to all consent requirements")
    
    # Step 2: Personal Information
    elif st.session_state.current_step == 2:
        st.markdown("### Step 2: Personal Information")
        
        with st.form("personal_info"):
            full_name = st.text_input("Full Name *", placeholder="Enter your full name")
            email = st.text_input("Email Address *", placeholder="example@email.com")
            phone = st.text_input("Phone Number *", placeholder="08012345678")
            
            selected_region = st.selectbox(
                "Geopolitical Zone *",
                list(NIGERIAN_REGIONS.keys()),
                index=None,
                placeholder="Select your zone"
            )
            
            if selected_region:
                states = NIGERIAN_REGIONS[selected_region]
                selected_state = st.selectbox(
                    "State *",
                    states,
                    index=None,
                    placeholder="Select your state"
                )
                
                if selected_state:
                    lga = st.text_input("Local Government Area (LGA) *", placeholder="Enter your LGA")
                    address = st.text_area("Detailed Address", placeholder="House number, street, area...")
            
            notes = st.text_area("Additional Information (Optional)", placeholder="Any special notes...")
            
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
        st.markdown("### Step 3: Photo Verification")
        
        st.info("**Instructions:** Ensure good lighting and face the camera directly.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div class="camera-frame">', unsafe_allow_html=True)
            photo = st.camera_input("Take your photo for verification")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if photo:
                st.session_state.photo_captured = photo
                image = Image.open(photo)
                st.image(image, caption="Your Photo", width=150)
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
        st.markdown("### Step 4: Location Details")
        
        st.markdown("### Enter Your Coordinates")
        
        col_lat, col_lon = st.columns(2)
        with col_lat:
            latitude = st.number_input("Latitude", format="%.6f", value=0.0)
        with col_lon:
            longitude = st.number_input("Longitude", format="%.6f", value=0.0)
        
        if st.session_state.client_data:
            st.write(f"**State:** {st.session_state.client_data.get('state')}")
            st.write(f"**LGA:** {st.session_state.client_data.get('lga')}")
        
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
                        'timestamp': datetime.now(NIGERIA_TZ).isoformat()
                    }
                    st.session_state.current_step = 5
                    st.rerun()
                else:
                    st.error("Please enter valid coordinates")
    
    # Step 5: Review & Submit
    elif st.session_state.current_step == 5:
        st.markdown("### Step 5: Review & Submit")
        
        if all([st.session_state.client_data, st.session_state.photo_captured, st.session_state.location_data]):
            st.markdown("#### Submission Summary")
            
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                client_data = st.session_state.client_data
                st.write(f"**Name:** {client_data.get('full_name')}")
                st.write(f"**Email:** {client_data.get('email')}")
                st.write(f"**Phone:** {client_data.get('phone')}")
                st.write(f"**Zone:** {client_data.get('geopolitical_zone')}")
                st.write(f"**State:** {client_data.get('state')}")
                st.write(f"**LGA:** {client_data.get('lga')}")
            
            with col_s2:
                loc = st.session_state.location_data
                st.write(f"**Coordinates:** {loc['latitude']:.6f}, {loc['longitude']:.6f}")
                
                if st.session_state.photo_captured:
                    image = Image.open(st.session_state.photo_captured)
                    st.image(image, caption="Verification Photo", width=150)
            
            if st.button("Submit Registration", type="primary", use_container_width=True):
                submission_id = f"SUB-{datetime.now(NIGERIA_TZ).strftime('%Y%m%d-%H%M%S')}"
                
                final_data = {
                    **st.session_state.client_data,
                    'latitude': st.session_state.location_data['latitude'],
                    'longitude': st.session_state.location_data['longitude'],
                    'submission_id': submission_id,
                    'app_version': APP_VERSION,
                    'consent_timestamp': datetime.now(NIGERIA_TZ).isoformat(),
                    'submission_timestamp': datetime.now(NIGERIA_TZ).isoformat()
                }
                
                photo_bytes = None
                if st.session_state.photo_captured:
                    photo_bytes = st.session_state.photo_captured.read()
                
                if save_submission_to_db(final_data, photo_bytes):
                    st.balloons()
                    st.success(f"""
                    🎉 **Registration Complete!**
                    
                    **Submission ID:** `{submission_id}`
                    
                    **Next Steps:**
                    1. Confirmation sent to {final_data['email']}
                    2. Application pending review
                    3. Contact within 48 hours
                    """)
                    
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
<div style="text-align: center; color: #6B7280; font-size: 0.8rem; margin-top: 3rem;">
    <p>Station Onboarding System v{APP_VERSION}</p>
    <p>For support: support@station.com</p>
</div>
""", unsafe_allow_html=True)
