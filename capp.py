import streamlit as st

st.set_page_config(page_title="Station Onboarding", page_icon="⛽")

st.title("⛽ Station Onboarding System")
st.write("Register your filling station")

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 1

# Step indicator
steps = ["Consent", "Information", "Photo", "Location", "Review"]
cols = st.columns(5)
for i, (col, step_name) in enumerate(zip(cols, steps), 1):
    with col:
        is_active = i == st.session_state.step
        st.markdown(f"**{'✅' if i < st.session_state.step else '🔘'} Step {i}: {step_name}**")

# Step content
if st.session_state.step == 1:
    st.header("Step 1: Consent")
    if st.checkbox("I agree to the terms"):
        if st.button("Continue"):
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    st.header("Step 2: Information")
    # Add your form fields here
    if st.button("Continue"):
        st.session_state.step = 3
        st.rerun()
    if st.button("Back"):
        st.session_state.step = 1
        st.rerun()

# Continue with other steps...

st.markdown("---")
st.caption("Station Onboarding System")
