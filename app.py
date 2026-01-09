"""
Streamlit Camera & Geolocation App
MIT License - For production use by registered businesses
Copyright (c) 2024 [Your IT Company Name]

This app captures photos with geolocation data during client onboarding.
Ensure compliance with local privacy laws (GDPR, CCPA, etc.).
"""

import streamlit as st
import json
import base64
from datetime import datetime
import pandas as pd
import os
from PIL import Image
import io
import time

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

# JavaScript for geolocation
def get_location_js():
    """JavaScript to get geolocation"""
    js_code = """
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    // Send location data back to Streamlit
                    const data = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date().toISOString()
                    };
                    
                    // Create a hidden element with the data
                    const elem = document.createElement('div');
                    elem.id = 'locationData';
                    elem.innerText = JSON.stringify(data);
                    document.body.appendChild(elem);
                    
                    // Trigger Streamlit to read the data
                    const event = new Event('locationCaptured');
                    document.dispatchEvent(event);
                },
                function(error) {
                    // Error handling
                    const errorData = {
                        error: true,
                        code: error.code,
                        message: error.message
                    };
                    const elem = document.createElement('div');
                    elem.id = 'locationData';
                    elem.innerText = JSON.stringify(errorData);
                    document.body.appendChild(elem);
                    
                    const event = new Event('locationCaptured');
                    document.dispatchEvent(event);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        } else {
            const errorData = {
                error: true,
                message: "Geolocation is not supported by this browser."
            };
            const elem = document.createElement('div');
            elem.id = 'locationData';
            elem.innerText = JSON.stringify(errorData);
            document.body.appendChild(elem);
            
            const event = new Event('locationCaptured');
            document.dispatchEvent(event);
        }
    }
    
    // Run on page load if needed
    // getLocation();
    </script>
    """
    return js_code

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
    Region = ["North Central", "North West", "North East", "South South", "South East", "South West"]
    selected_Region = st.selectbox("Select Region *", Region)
    
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
- If automatic location fails, use manual entry below
""")
st.markdown('</div>', unsafe_allow_html=True)

# Inject JavaScript for geolocation
st.components.v1.html(get_location_js(), height=0)

# Location capture button
if st.button("📍 Get My Current Location", key="get_location"):
    # Inject JavaScript to trigger geolocation
    trigger_js = """
    <script>
    getLocation();
    
    // Poll for location data
    function checkForLocationData() {
        const elem = document.getElementById('locationData');
        if (elem) {
            const data = JSON.parse(elem.innerText);
            // Send to Streamlit via URL parameters (simplified approach)
            window.location.href = window.location.href.split('?')[0] + '?location=' + encodeURIComponent(elem.innerText);
        } else {
            setTimeout(checkForLocationData, 500);
        }
    }
    checkForLocationData();
    </script>
    """
    
    st.components.v1.html(trigger_js, height=0)
    
    # Check for location data in URL
    query_params = st.query_params
    if 'location' in query_params:
        try:
            location_data = json.loads(query_params['location'])
            
            if 'error' in location_data and location_data['error']:
                st.error(f"Location error: {location_data.get('message', 'Unknown error')}")
            else:
                st.session_state.location_data = {
                    'latitude': location_data['latitude'],
                    'longitude': location_data['longitude'],
                    'accuracy': location_data.get('accuracy', 'Unknown'),
                    'timestamp': location_data.get('timestamp', datetime.now().isoformat()),
                    'source': 'gps'
                }
                
                # Display location data
                st.markdown('<div class="data-box">', unsafe_allow_html=True)
                st.success("✅ Location captured successfully!")
                st.metric("Latitude", f"{location_data['latitude']:.6f}")
                st.metric("Longitude", f"{location_data['longitude']:.6f}")
                st.metric("Accuracy", f"±{location_data.get('accuracy', 'Unknown'):.1f} meters")
                
                # Show map preview
                map_data = pd.DataFrame({
                    'lat': [location_data['latitude']],
                    'lon': [location_data['longitude']]
                })
                st.map(map_data, zoom=14)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Clear the query parameter
                del st.query_params['location']
                
        except Exception as e:
            st.error(f"Error processing location: {str(e)}")
    else:
        # Show manual entry option if automatic fails
        st.info("If location capture doesn't work automatically, please use manual entry below:")
    
    # Manual location entry as fallback
    with st.expander("📝 Manual Location Entry", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            manual_lat = st.number_input("Latitude", format="%.6f", value=0.0, key="manual_lat")
        with col2:
            manual_lon = st.number_input("Longitude", format="%.6f", value=0.0, key="manual_lon")
        
        location_source = st.selectbox("Location Source", 
                                     ["GPS - Automatic", "Manually Entered", "Selected from Map"])
        
        if st.button("💾 Save Manual Location"):
            if manual_lat != 0.0 and manual_lon != 0.0:
                st.session_state.location_data = {
                    'latitude': manual_lat,
                    'longitude': manual_lon,
                    'accuracy': None,
                    'timestamp': datetime.now().isoformat(),
                    'source': location_source
                }
                st.success("Manual location saved successfully!")
            else:
                st.error("Please enter valid coordinates (not 0,0)")

# Display current location if captured
if st.session_state.location_data:
    st.markdown('<div class="data-box">', unsafe_allow_html=True)
    st.subheader("📍 Current Location Data")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Latitude", f"{st.session_state.location_data['latitude']:.6f}")
    with col2:
        st.metric("Longitude", f"{st.session_state.location_data['longitude']:.6f}")
    
    st.caption(f"Source: {st.session_state.location_data.get('source', 'Unknown')} | "
               f"Captured: {st.session_state.location_data['timestamp'][:19]}")
    
    # Show on map
    map_data = pd.DataFrame({
        'lat': [st.session_state.location_data['latitude']],
        'lon': [st.session_state.location_data['longitude']]
    })
    st.map(map_data, zoom=14)
    st.markdown('</div>', unsafe_allow_html=True)

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
            'app_version': APP_VERSION,
            'consent_timestamp': datetime.now().isoformat()
        }
        
        # Display success message
        st.balloons()
        st.success(f"""
        🎉 **Onboarding Complete!**
        
        **Submission ID:** {final_data['submission_id']}
        
        **Next Steps:**
        1. You will receive a confirmation email at {final_data['email']}
        2. Our team will verify your information within 24 hours
        3. Service delivery will be scheduled based on your location
        
        **Estimated Service Area:** {final_data['location']['latitude']:.4f}, {final_data['location']['longitude']:.4f}
        """)
        
        # Display summary
        st.markdown("### 📋 Submission Summary")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Client", final_data['full_name'])
        with col2:
            st.metric("Product", final_data['product'].split(' - ')[0])
        with col3:
            st.metric("Status", "Submitted")
        
        # Data preview (in production, this would save to database)
        with st.expander("View Collected Data (Preview)"):
            # Don't show full data in production - this is just for demo
            preview_data = {
                'submission_id': final_data['submission_id'],
                'client_name': final_data['full_name'],
                'email': final_data['email'],
                'product': final_data['product'],
                'location': final_data['location'],
                'timestamp': final_data['timestamp']
            }
            st.json(preview_data, expanded=False)
            
            # Create download option (in production, this would be secure)
            json_str = json.dumps(preview_data, indent=2)
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="onboarding_data_{final_data["submission_id"]}.json">📥 Download Data Summary (JSON)</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        # In production: Save to database here
        st.info("""
        **Production Note:** In a production environment, this data would be:
        - Encrypted and saved to secure database
        - Sent to your CRM system
        - Processed for service scheduling
        - Accessed only by authorized personnel
        """)
        
        # Increment submission count
        st.session_state.submission_count += 1
        
        # Show reset option
        if st.button("➕ Start New Client Onboarding"):
            # Reset only specific fields, keep consent
            st.session_state.photo_captured = None
            st.session_state.location_data = None
            st.session_state.client_data = {}
            st.rerun()

# Admin/Privacy Section
with st.expander("🔒 Privacy & Data Management"):
    st.markdown("""
    ### Data Management
    *All data is handled in compliance with privacy regulations.*
    
    **Data Retention Policy:**
    - Client information: 7 years (legal requirement)
    - Location data: 2 years (service optimization)
    - Photos: 1 year (verification purposes)
    
    **Your Rights Under GDPR/CCPA:**
    - Right to access your data
    - Right to rectification
    - Right to erasure ("right to be forgotten")
    - Right to restrict processing
    - Right to data portability
    - Right to object to processing
    
    **Contact Our Data Protection Officer:** 
    📧 privacy@yourcompany.com
    📞 [Privacy Office Phone]
    """)
    
    if st.button("🚫 Revoke My Consent (Clear All Data)"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("All session data cleared. Consent revoked.")
        st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div class="footer">
    <p>App Version {APP_VERSION} | MIT Licensed © 2024</p>
    <p>For technical support: support@yourcompany.com | Phone: [Support Number]</p>
    <p>Submissions this session: {st.session_state.submission_count}</p>
    <p><small>This application uses browser geolocation API. Accuracy depends on device capabilities.</small></p>
</div>
""", unsafe_allow_html=True)
