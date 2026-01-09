"""
Streamlit Camera & Geolocation App
MIT License - For production use by registered businesses
Copyright (c) 2024 [Your IT Company Name]

This app captures photos with geolocation data during client onboarding.
Ensure compliance with local privacy laws (GDPR, CCPA, etc.).
"""

import streamlit as st
from streamlit_js_eval import streamlit_js_eval, get_geolocation
import json
import base64
from datetime import datetime
import pandas as pd
import os
from PIL import Image
import io

# Page configuration
st.set_page_config(
    page_title="Client Onboarding - Photo & Location",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Constants
APP_VERSION = "1.0.0"
PRIVACY_POLICY_URL = "https://yourcompany.com/privacy"  # Update with actual URL
TERMS_URL = "https://yourcompany.com/terms"  # Update with actual URL

# Initialize session state
def init_session_state():
    if 'consent_given' not in st.session_state:
        st.session_state.consent_given = False
    if 'location_data' not in st.session_state:
        st.session_state.location_data = None
    if 'photo_captured' not in st.session_state:
        st.session_state.photo_captured = None
    if 'client_data' not in st.session_state:
        st.session_state.client_data = {}
    if 'submission_count' not in st.session_state:
        st.session_state.submission_count = 0

init_session_state()

# Custom CSS for better UI
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
        width: 100%;
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.75rem;
        border-radius: 5px;
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
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">📍 Client Onboarding System</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Secure Photo Capture with Location Verification</p>', unsafe_allow_html=True)

# Terms and Conditions Content
TERMS_CONTENT = f"""
## Terms & Conditions and Privacy Notice

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}

### 1. Consent to Data Collection
By using this application, you consent to:

1. **Camera Access**: Capture your photo for identity verification
2. **Location Collection**: Capture your device's GPS coordinates (latitude/longitude)
3. **Data Storage**: Secure storage of your photo and location data
4. **Data Usage**: Use of this data for service delivery and verification purposes

### 2. Data We Collect
- **Photo**: Image captured through your device camera
- **Location**: GPS coordinates (latitude, longitude) with timestamp
- **Device Information**: Browser type, IP address (anonymized)
- **Timestamp**: Date and time of submission

### 3. How We Use Your Data
- Verify your identity during onboarding
- Deliver services to your location
- Prevent fraud and ensure security
- Improve our services

### 4. Data Security
- All data is encrypted during transmission
- Access is restricted to authorized personnel only
- Data retention according to business needs and legal requirements

### 5. Your Rights
You have the right to:
- Access your personal data
- Request correction of inaccurate data
- Request deletion of your data (subject to legal requirements)
- Withdraw consent (contact our privacy officer)

### 6. Third-Party Sharing
We do not sell your data. We may share with:
- Service providers (under strict confidentiality)
- Legal authorities (when required by law)

### 7. Contact Information
For privacy concerns:
- Email: privacy@yourcompany.com
- Phone: [Your Contact Number]
- Address: [Your Business Address]

**By proceeding, you acknowledge you have read and agree to these terms.**

Full terms: {TERMS_URL}
Privacy Policy: {PRIVACY_POLICY_URL}
"""

# Consent Section
if not st.session_state.consent_given:
    st.markdown("## 📋 Consent Agreement")
    
    with st.expander("📄 Read Complete Terms & Conditions", expanded=True):
        st.markdown(TERMS_CONTENT)
    
    st.markdown('<div class="consent-box">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        consent_1 = st.checkbox(
            "I consent to camera access for photo capture",
            help="Required to take your photo"
        )
    
    with col2:
        consent_2 = st.checkbox(
            "I consent to location sharing for service delivery",
            help="Required to get your GPS coordinates"
        )
    
    consent_3 = st.checkbox(
        "I have read and agree to the Terms & Conditions and Privacy Policy",
        help="Required to proceed"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("✅ Give Consent & Proceed"):
        if consent_1 and consent_2 and consent_3:
            st.session_state.consent_given = True
            st.rerun()
        else:
            st.error("⚠️ Please agree to all consent requirements to proceed")
    
    st.markdown("---")
    st.markdown(f'<div class="footer">App Version {APP_VERSION} | MIT Licensed © 2024</div>', unsafe_allow_html=True)
    st.stop()

# Main App - After Consent
st.success("✅ Consent recorded. You may now proceed with onboarding.")

# Client Information Form
st.markdown("## 👤 Client Information")
with st.form("client_info"):
    col1, col2 = st.columns(2)
    
    with col1:
        full_name = st.text_input("Full Name *", placeholder="Enter your full name")
        email = st.text_input("Email Address *", placeholder="your.email@example.com")
    
    with col2:
        phone = st.text_input("Phone Number *", placeholder="+1 (555) 123-4567")
        client_id = st.text_input("Client Reference ID", placeholder="Optional")
    
    # Product selection
    products = ["Product A - $99", "Product B - $149", "Product C - $199", "Custom Package"]
    selected_product = st.selectbox("Select Product *", products)
    
    notes = st.text_area("Additional Notes", placeholder="Any special requirements or notes...")
    
    submit_info = st.form_submit_button("💾 Save Client Information")
    
    if submit_info:
        if full_name and email and phone and selected_product:
            st.session_state.client_data = {
                'full_name': full_name,
                'email': email,
                'phone': phone,
                'client_id': client_id,
                'product': selected_product,
                'notes': notes,
                'timestamp': datetime.now().isoformat()
            }
            st.success("Client information saved successfully!")
        else:
            st.error("Please fill in all required fields (*)")

# Photo Capture Section
st.markdown("## 📷 Photo Capture")
st.markdown('<div class="warning-box">', unsafe_allow_html=True)
st.info("""
**Instructions:**
1. Ensure good lighting
2. Face the camera directly
3. Remove sunglasses/hat if possible
4. Make sure your entire face is visible
""")
st.markdown('</div>', unsafe_allow_html=True)

# Camera input
st.markdown('<div class="camera-frame">', unsafe_allow_html=True)
photo = st.camera_input("Take a clear photo for verification", key="camera")
st.markdown('</div>', unsafe_allow_html=True)

if photo:
    st.session_state.photo_captured = photo
    st.success("✅ Photo captured successfully!")
    
    # Display captured photo
    image = Image.open(photo)
    st.image(image, caption="Captured Photo", width=300)

# Location Capture Section
st.markdown("## 📍 Location Capture")
st.markdown('<div class="warning-box">', unsafe_allow_html=True)
st.warning("""
**Location Access Required:**
- Click 'Get My Location' to capture GPS coordinates
- Ensure location services are enabled on your device
- You may need to allow location access in browser permissions
""")
st.markdown('</div>', unsafe_allow_html=True)

# Get location button
if st.button("📍 Get My Current Location", key="get_location"):
    with st.spinner("Getting your location..."):
        try:
            # Using streamlit_js_eval to get geolocation
            location = get_geolocation()
            
            if location and 'coords' in location:
                st.session_state.location_data = {
                    'latitude': location['coords']['latitude'],
                    'longitude': location['coords']['longitude'],
                    'accuracy': location['coords']['accuracy'],
                    'timestamp': datetime.now().isoformat()
                }
                
                # Display location data
                st.markdown('<div class="data-box">', unsafe_allow_html=True)
                st.success("✅ Location captured successfully!")
                st.metric("Latitude", f"{location['coords']['latitude']:.6f}")
                st.metric("Longitude", f"{location['coords']['longitude']:.6f}")
                st.metric("Accuracy", f"±{location['coords']['accuracy']:.1f} meters")
                
                # Show map preview
                map_data = pd.DataFrame({
                    'lat': [location['coords']['latitude']],
                    'lon': [location['coords']['longitude']]
                })
                st.map(map_data, zoom=14)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error("⚠️ Could not retrieve location. Please ensure location services are enabled.")
                
        except Exception as e:
            st.error(f"Error getting location: {str(e)}")
            st.info("If location capture fails, you can manually enter coordinates below:")
            
            col1, col2 = st.columns(2)
            with col1:
                manual_lat = st.number_input("Latitude", format="%.6f")
            with col2:
                manual_lon = st.number_input("Longitude", format="%.6f")
            
            if manual_lat and manual_lon:
                if st.button("Use Manual Coordinates"):
                    st.session_state.location_data = {
                        'latitude': manual_lat,
                        'longitude': manual_lon,
                        'accuracy': None,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'manual'
                    }
                    st.success("Manual coordinates saved!")

# Final Submission
st.markdown("---")
st.markdown("## ✅ Final Submission")

if st.button("🚀 Complete Onboarding", type="primary"):
    # Validation checks
    errors = []
    
    if not st.session_state.client_data:
        errors.append("Please complete client information")
    
    if not st.session_state.photo_captured:
        errors.append("Please capture a photo")
    
    if not st.session_state.location_data:
        errors.append("Please capture location data")
    
    if errors:
        for error in errors:
            st.error(error)
    else:
        # Prepare final data
        final_data = {
            **st.session_state.client_data,
            'photo_captured': True,
            'location': st.session_state.location_data,
            'submission_id': f"SUB-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'app_version': APP_VERSION
        }
        
        # Display success message
        st.balloons()
        st.success("""
        🎉 **Onboarding Complete!**
        
        **Next Steps:**
        1. You will receive a confirmation email
        2. Our team will verify your information
        3. Service delivery will be scheduled
        
        **Reference ID:** {}
        """.format(final_data['submission_id']))
        
        # Display summary
        st.markdown("### 📋 Submission Summary")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Client", final_data['full_name'])
        with col2:
            st.metric("Product", final_data['product'].split(' - ')[0])
        with col3:
            st.metric("Location Captured", "✅")
        
        # Data preview (in production, this would save to database)
        with st.expander("View Collected Data (Preview)"):
            st.json(final_data, expanded=False)
            
            # Create download option
            json_str = json.dumps(final_data, indent=2)
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="onboarding_data_{final_data["submission_id"]}.json">📥 Download Data (JSON)</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        # Reset for next submission (except consent)
        st.session_state.photo_captured = None
        st.session_state.location_data = None
        st.session_state.client_data = {}
        st.session_state.submission_count += 1
        
        # Show reset option
        if st.button("➕ Start New Onboarding"):
            st.rerun()

# Admin/Privacy Section (hidden by default)
with st.expander("🔒 Privacy & Data Management"):
    st.markdown("""
    ### Data Management
    *All data is handled in compliance with privacy regulations.*
    
    **Your Rights:**
    - Right to access your data
    - Right to rectification
    - Right to erasure
    - Right to data portability
    
    **Contact Privacy Officer:** privacy@yourcompany.com
    """)
    
    if st.button("🚫 Revoke My Consent (Reset Session)"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div class="footer">
    <p>App Version {APP_VERSION} | MIT Licensed © 2024</p>
    <p>For support: support@yourcompany.com | Phone: [Support Number]</p>
    <p>Total submissions this session: {st.session_state.submission_count}</p>
</div>
""", unsafe_allow_html=True)
