import streamlit as st
import os

# =========================================================
# PAGE CONFIG (MUST BE FIRST)
# =========================================================
st.set_page_config(
    page_title="Sahay | Peer Learning Matchmaking",
    page_icon="🌱",
    layout="wide"
)

# ---- DIRECTORY SETUP FOR FILE SHARING ----
if not os.path.exists("uploads"):
    os.makedirs("uploads")

from datetime import date

# ---- IMPORT PAGES ----
from materials import materials_page
from practice import practice_page
from admin import admin_page
from auth import auth_page
from dashboard import dashboard_page
from matching import matchmaking_page

# ---- DATABASE ----
from database import init_db

# =========================================================
# GLOBAL UI STYLES (EMERALD THEME + RIPPLE EFFECT)
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins','Inter','Segoe UI',sans-serif;
}

.stApp {
    background: linear-gradient(135deg,#f5f7fa,#eef1f5);
}

section[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(200,200,200,0.3);
}

.sidebar-header {
  padding:1.6rem;
  border-radius:20px;
  background: linear-gradient(135deg, #0f766e, #14b8a6, #22c55e);
  color:white;
  margin-bottom:1.4rem;
  text-align:center;
  box-shadow:0 12px 30px rgba(20,184,166,0.45);
}

.sidebar-header .app-name {
  font-size:2.6rem;
  font-weight:800;
  letter-spacing:0.06em;
}

.sidebar-header .username {
  margin-top:0.4rem;
  font-size:0.95rem;
  opacity:0.9;
}

.card {
  background: rgba(255,255,255,.95);
  border-radius:20px;
  padding:1.8rem;
  box-shadow:0 12px 30px rgba(0,0,0,.06);
  margin-bottom: 1.5rem;
}

/* --- DONATION CARD STYLING --- */
.donation-card {
    background: white; 
    padding: 1.8rem; 
    border-radius: 20px; 
    border-left: 8px solid #10b981; 
    margin-bottom: 1.5rem; 
    box-shadow: 0 8px 20px rgba(0,0,0,0.04);
    transition: all 0.3s ease;
}

.donation-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 25px rgba(16, 185, 129, 0.1);
}

/* --- EMERALD RIPPLE BUTTON --- */
.ripple-btn {
    background: #10b981;
    color: white !important;
    padding: 14px 28px;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 600;
    text-decoration: none;
    display: inline-block;
    position: relative;
    overflow: hidden;
    transition: background 0.5s;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);
    text-align: center;
}

.ripple-btn:hover {
    background: #0d9488 radial-gradient(circle, transparent 1%, #0d9488 1%) center/15000%;
}

.ripple-btn:active {
    background-color: #0f766e;
    background-size: 100%;
    transition: background 0s;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# SESSION STATE INIT
# =========================================================
for key, default in {
    "logged_in": False,
    "user_id": None,
    "user_name": "",
    "page": "Dashboard",
    "proposed_match": None,
    "proposed_score": None,
    "session_step": "discovery" 
}.items():
    st.session_state.setdefault(key, default)

# =========================================================
# AUTH GATE
# =========================================================
if not st.session_state.logged_in:
    auth_page()
    st.stop()

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-header">
        <div class="app-name">Sahay</div>
        <div class="username">{st.session_state.user_name}</div>
    </div>
    """, unsafe_allow_html=True)

    for label in [
        "Dashboard",
        "Matchmaking",
        "Learning Materials",
        "Practice",
        "Donations",
        "Admin"
    ]:
        if st.button(label, use_container_width=True):
            st.session_state.page = label
            if label != "Matchmaking":
                st.session_state.session_step = "discovery"
            st.rerun()

    st.divider()

    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# =========================================================
# ROUTING
# =========================================================
page = st.session_state.page

if page == "Dashboard":
    dashboard_page()

elif page == "Matchmaking":
    matchmaking_page()

elif page == "Learning Materials":
    materials_page()

elif page == "Practice":
    practice_page()

elif page == "Donations":
    st.markdown("""
        <div class='card'>
            <h1 style='color:#0f766e; margin-bottom:0;'>Support Education</h1>
            <p style='color:#64748b;'>Choose a platform below to make a direct impact on a student's future.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Organization Data with SVG Vector Art
    donations = [
        {
            "name": "Pratham",
            "url": "https://pratham.org/donation/",
            "desc": "Focuses on high-quality, low-cost, and replicable interventions to address gaps in the education system and ensure every child is learning well.",
            "icon": '<svg viewBox="0 0 24 24" width="45" height="45" stroke="#0f766e" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>'
        },
        {
            "name": "Akshaya Patra",
            "url": "https://www.akshayapatra.org/onlinedonations",
            "desc": "The world's largest NGO-run mid-day meal programme, serving wholesome food to over 2 million children in India every school day.",
            "icon": '<svg viewBox="0 0 24 24" width="45" height="45" stroke="#0f766e" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>'
        },
        {
            "name": "Teach For India",
            "url": "https://www.teachforindia.org/donate",
            "desc": "A movement of promising leaders who commit two years to teaching full-time in under-resourced schools to eliminate educational inequity.",
            "icon": '<svg viewBox="0 0 24 24" width="45" height="45" stroke="#0f766e" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>'
        }
    ]

    for org in donations:
        st.markdown(f"""
        <div class="donation-card">
            <div style="display: flex; align-items: start; gap: 25px; margin-bottom: 20px;">
                <div style="background: #f0fdf4; padding: 12px; border-radius: 12px;">{org['icon']}</div>
                <div>
                    <h2 style="margin:0; color:#0f766e; font-size: 1.5rem;">{org['name']}</h2>
                    <p style="margin:8px 0 0 0; color:#475569; line-height:1.6; font-size:1rem;">{org['desc']}</p>
                </div>
            </div>
            <a href="{org['url']}" target="_blank" class="ripple-btn">
                Contribute to {org['name']} →
            </a>
        </div>
        """, unsafe_allow_html=True)

elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")
    if key == "ngo-admin-123":
        admin_page()
