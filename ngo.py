import streamlit as st

# 1. Page Configuration for Accessibility
st.set_page_config(
    page_title="NGO Donation Portal",
    page_icon="🤝",
    layout="centered"
)

# 2. Main Title (H1 for Screen Readers)
st.title("Support Local NGOs")

# 3. Descriptive Content
st.write("""
### Help us make a difference.
Below you will find a link to our comprehensive directory of verified NGOs. 
Each organization has been vetted to ensure your donations reach those in need.
""")

st.divider()

# --- LINK SECTION ---
# PASTE YOUR WEBSITE LINK HERE
MY_NGO_WEBSITE_URL = "https://your-ngo-website.com"

# Using a standard Streamlit link button which is highly accessible
st.link_button(
    label="👉 Click here to view the NGO Donation List", 
    url=MY_NGO_WEBSITE_URL,
    help="This link will open our NGO directory in a new browser tab.",
    use_container_width=True
)
# ---------------------

st.divider()

# 4. Additional Accessibility Information
with st.expander("Accessibility Information"):
    st.write("""
    - **Keyboard Users:** Use the 'Tab' key to navigate to the donation button.
    - **Screen Readers:** The button above is labeled clearly to indicate it opens an external directory.
    - **Contrast:** We use high-contrast colors to ensure readability for all users.
    """)

# 5. Footer
st.caption("© 2026 NGO Connect. Empowering change through community support.")