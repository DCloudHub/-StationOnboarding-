"""
Station Onboarding System
MIT License - For production use
"""

import streamlit as st
import json
import base64
from datetime import datetime
import pandas as pd
from PIL import Image
import io
import sqlite3
import csv
import hashlib
import pytz

# Page configuration
st.set_page_config(
    page_title="Station Onboarding",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
APP_VERSION = "1.0.0"
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
if 'photo_captured' not in st.session_state:
    st.session_state.photo_captured = None
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
    .consent-item {
        margin: 1rem 0;
        padding: 0.5rem;
        background-color: #f3f4f6;
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
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    conn.commit()
    return conn

DB_CONN = init_database()

def save_submission_to_db(submission_data):
    try:
        c = DB_CONN.cursor()
        c.execute('''
            INSERT INTO submissions (
                submission_id, full_name, email, phone, geopolitical_zone, state, lga, address,
                latitude, longitude, submission_timestamp, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            'pending'
        ))
        
        DB_CONN.commit()
        return True
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return False

def get_all_submissions():
    try:
        c = DB_CONN.cursor()
        c.execute('SELECT * FROM submissions ORDER BY submission_timestamp DESC')
        return c.fetchall()
    except:
        return []

# Step indicator function
def show_step_indicator():
    steps = [
        {"number": 1, "label": "Consent"},
        {"number": 2, "label": "Information"}, 
        {"number": 3, "label": "Photo"},
        {"number": 4, "label": "Location"},
        {"number": 5, "label": "Review"}
    ]
    
    html = '<div class="step-container">'
    
    for step in steps:
        is_active = "active" if step["number"] == st.session_state.current_step else ""
        html += f'''
        <div class="step-item {is_active}">
            <div class="step-number">{step["number"]}</div>
            <div class="step-label">{step["label"]}</div>
        </div>
        '''
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">📍 Station Onboarding</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #4B5563; margin-bottom: 2rem;">Complete your registration in 5 simple steps</p>', unsafe_allow_html=True)

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
        if st.button("View Submissions"):
            st.session_state.view_submissions = True
            st.rerun()
        if st.button("Logout"):
            st.session_state.admin_authenticated = False
            st.session_state.view_submissions = False
            st.rerun()

# Main App
if st.session_state.admin_authenticated and st.session_state.view_submissions:
    st.markdown("## Admin Dashboard")
    
    submissions = get_all_submissions()
    if submissions:
        df = pd.DataFrame(submissions, columns=[
            'ID', 'Submission ID', 'Name', 'Email', 'Phone', 'Zone', 'State',
            'LGA', 'Address', 'Lat', 'Lon', 'Time', 'Status'
        ])
        st.dataframe(df[['Submission ID', 'Name', 'Phone', 'Zone', 'State', 'Time', 'Status']])
    else:
        st.info("No submissions yet")
    
    if st.button("← Back to Form"):
        st.session_state.view_submissions = False
        st.rerun()

else:
    show_step_indicator()
    
    # Step 1: Consent - UPDATED: SINGLE CHECKBOX
    if st.session_state.current_step == 1:
        st.markdown("### Step 1: Consent & Agreement")
        
        with st.expander("📋 Read Complete Terms & Conditions", expanded=True):
            st.markdown("""
            ## Data Collection Consent
            
            By checking the consent box below, you agree to ALL of the following:
            
            ### 1. Photo Capture Consent
            - You consent to have your photo taken for identity verification
            - The photo will be used solely for verification purposes
            - Photo will be stored securely and deleted after verification
            
            ### 2. Location Data Consent  
            - You consent to share your precise location coordinates
            - Location data will be used for service delivery planning
            - Coordinates will be used to determine service eligibility
            
            ### 3. Personal Information Consent
            - You consent to provide your full name, email, and phone number
            - This information will be used for communication and service delivery
            - Data will be handled in accordance with privacy regulations
            
            ### 4. Terms & Conditions Acceptance
            - You agree to abide by our Terms & Conditions
            - You acknowledge our Privacy Policy
            - You understand your data rights under applicable laws
            
            ### Your Data Rights:
            - Right to access your data
            - Right to correction
            - Right to deletion (where applicable)
            - Right to restrict processing
            """)
        
        st.markdown('<div class="consent-box">', unsafe_allow_html=True)
        
        # SINGLE CONSENT CHECKBOX - MERGED ALL
        consent_all = st.checkbox(
            "✅ **I consent to ALL of the above:**\n"
            "- Photo capture for identity verification\n"
            "- Location data collection for service delivery\n" 
            "- Personal information processing\n"
            "- Terms & Conditions and Privacy Policy\n\n"
            "By checking this box, I acknowledge that I have read and understood all the terms above.",
            help="Check this box to give your consent for all data collection and processing"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Continue to Step 2", type="primary"):
            if consent_all:
                st.session_state.consent_given = True
                st.session_state.current_step = 2
                st.rerun()
            else:
                st.error("⚠️ You must give your consent to proceed with registration")
    
    # Step 2: Information
    elif st.session_state.current_step == 2:
        st.markdown("### Step 2: Personal Information")
        
        with st.form("info_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name *", placeholder="Enter your full name")
                email = st.text_input("Email Address *", placeholder="example@email.com")
            
            with col2:
                phone = st.text_input("Phone Number *", placeholder="08012345678")
                zone = st.selectbox("Geopolitical Zone *", 
                                   list(NIGERIAN_REGIONS.keys()),
                                   index=None,
                                   placeholder="Select your zone")
            
            if zone:
                state = st.selectbox("State *", 
                                    NIGERIAN_REGIONS[zone],
                                    index=None,
                                    placeholder="Select your state")
            else:
                state = None
            
            if state:
                lga = st.text_input("Local Government Area (LGA) *", 
                                   placeholder="Enter your LGA")
                address = st.text_area("Detailed Address (Optional)", 
                                      placeholder="House number, street, area...",
                                      height=100)
            
            notes = st.text_area("Additional Information (Optional)", 
                               placeholder="Any special requirements or notes...")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                back = st.form_submit_button("← Back to Consent")
            with col_btn2:
                next_btn = st.form_submit_button("Next: Take Photo →", type="primary")
            
            if back:
                st.session_state.current_step = 1
                st.rerun()
            
            if next_btn:
                if all([name, email, phone, zone, state, lga]):
                    st.session_state.client_data = {
                        'full_name': name,
                        'email': email,
                        'phone': phone,
                        'geopolitical_zone': zone,
                        'state': state,
                        'lga': lga,
                        'address': address,
                        'notes': notes
                    }
                    st.session_state.current_step = 3
                    st.rerun()
                else:
                    st.error("❌ Please fill in all required fields (*)")
    
    # Step 3: Photo
    elif st.session_state.current_step == 3:
        st.markdown("### Step 3: Photo Verification")
        
        st.info("""
        **Photo Guidelines:**
        - Ensure good lighting
        - Face the camera directly  
        - Remove sunglasses/hat if possible
        - Make sure your face is clearly visible
        """)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div style="border: 3px solid #1E3A8A; border-radius: 10px; padding: 10px; background-color: #000;">', unsafe_allow_html=True)
            photo = st.camera_input("Click the camera icon to take your photo", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if photo:
                st.session_state.photo_captured = photo
                image = Image.open(photo)
                st.image(image, caption="Your Photo", width=150)
                st.success("✅ Photo captured successfully!")
            else:
                st.info("Take a photo using the camera above")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("← Back to Info"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col_btn3:
            if photo and st.button("Next: Enter Location →", type="primary"):
                st.session_state.current_step = 4
                st.rerun()
    
    # Step 4: Location
    elif st.session_state.current_step == 4:
        st.markdown("### Step 4: Location Details")
        
        st.markdown("### Enter Your Exact Coordinates")
        
        col_lat, col_lon = st.columns(2)
        with col_lat:
            latitude = st.number_input("Latitude *", format="%.6f", value=0.0,
                                     help="Example: 9.076479 (for Abuja)")
        with col_lon:
            longitude = st.number_input("Longitude *", format="%.6f", value=0.0,
                                      help="Example: 7.398574 (for Abuja)")
        
        if st.session_state.client_data:
            st.info(f"""
            **Your Information:**
            - **State:** {st.session_state.client_data.get('state')}
            - **LGA:** {st.session_state.client_data.get('lga')}
            - **Address:** {st.session_state.client_data.get('address', 'Not provided')}
            """)
        
        # Show map preview if coordinates are entered
        if latitude != 0.0 and longitude != 0.0:
            location_df = pd.DataFrame({
                'lat': [latitude],
                'lon': [longitude]
            })
            st.map(location_df, zoom=12)
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("← Back to Photo"):
                st.session_state.current_step = 3
                st.rerun()
        
        with col_btn3:
            if st.button("Next: Review & Submit →", type="primary"):
                if latitude != 0.0 and longitude != 0.0:
                    st.session_state.location_data = {
                        'latitude': latitude,
                        'longitude': longitude,
                        'timestamp': datetime.now(NIGERIA_TZ).isoformat()
                    }
                    st.session_state.current_step = 5
                    st.rerun()
                else:
                    st.error("❌ Please enter valid coordinates")
    
    # Step 5: Review
    elif st.session_state.current_step == 5:
        st.markdown("### Step 5: Review & Submit")
        
        if all([st.session_state.client_data, st.session_state.photo_captured, st.session_state.location_data]):
            st.markdown("### 📋 Registration Summary")
            
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                st.markdown("#### Personal Information")
                client_data = st.session_state.client_data
                st.write(f"**Name:** {client_data.get('full_name')}")
                st.write(f"**Email:** {client_data.get('email')}")
                st.write(f"**Phone:** {client_data.get('phone')}")
                st.write(f"**Zone:** {client_data.get('geopolitical_zone')}")
                st.write(f"**State:** {client_data.get('state')}")
                st.write(f"**LGA:** {client_data.get('lga')}")
                if client_data.get('address'):
                    st.write(f"**Address:** {client_data.get('address')}")
                if client_data.get('notes'):
                    st.write(f"**Notes:** {client_data.get('notes')}")
            
            with col_s2:
                st.markdown("#### Verification Data")
                
                # Show photo
                if st.session_state.photo_captured:
                    image = Image.open(st.session_state.photo_captured)
                    st.image(image, caption="Verification Photo", width=150)
                    st.success("✅ Photo verified")
                
                # Show location
                loc = st.session_state.location_data
                st.write(f"**Coordinates:** {loc['latitude']:.6f}, {loc['longitude']:.6f}")
                
                # Show location on map
                location_df = pd.DataFrame({
                    'lat': [loc['latitude']],
                    'lon': [loc['longitude']]
                })
                st.map(location_df, zoom=12)
            
            st.markdown("---")
            st.markdown("### 🚀 Ready to Submit")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("← Back to Location"):
                    st.session_state.current_step = 4
                    st.rerun()
            
            with col_btn2:
                if st.button("Submit Registration", type="primary", use_container_width=True):
                    # Generate submission ID
                    submission_id = f"SUB-{datetime.now(NIGERIA_TZ).strftime('%Y%m%d-%H%M%S')}"
                    
                    # Prepare final data
                    final_data = {
                        **st.session_state.client_data,
                        'latitude': st.session_state.location_data['latitude'],
                        'longitude': st.session_state.location_data['longitude'],
                        'submission_id': submission_id,
                        'submission_timestamp': datetime.now(NIGERIA_TZ).isoformat()
                    }
                    
                    # Save to database
                    if save_submission_to_db(final_data):
                        st.balloons()
                        st.success(f"""
                        🎉 **Registration Complete!**
                        
                        **Submission ID:** `{submission_id}`
                        **Name:** {final_data['full_name']}
                        **Email:** {final_data['email']}
                        
                        **Next Steps:**
                        1. Confirmation email sent to {final_data['email']}
                        2. Your application is pending review
                        3. You'll be contacted within 48 hours
                        4. Keep your Submission ID for reference
                        """)
                        
                        # Reset for next user
                        st.session_state.consent_given = False
                        st.session_state.current_step = 1
                        st.session_state.client_data = {}
                        st.session_state.photo_captured = None
                        st.session_state.location_data = None
                        
                        if st.button("Start New Registration"):
                            st.rerun()
                    else:
                        st.error("❌ Error saving submission. Please try again.")
        else:
            st.error("❌ Missing information. Please go back and complete all steps.")
            if st.button("← Back to Location"):
                st.session_state.current_step = 4
                st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #6B7280; font-size: 0.8rem; margin-top: 2rem;">
    <p>Station Onboarding System v{APP_VERSION}</p>
    <p>For support: support@station.com</p>
</div>
""", unsafe_allow_html=True)
