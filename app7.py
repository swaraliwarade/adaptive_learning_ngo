import streamlit as st
import os
from groq import Groq

# SVG Logos instead of Emojis as requested
# 
# 

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Sahay | Peer Learning Matchmaking",
    page_icon="🌱",
    layout="wide"
)

# ---- GROQ SETUP ----
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_KEY = "PASTE_YOUR_GROQ_KEY_HERE"

client = Groq(api_key=GROQ_KEY)

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Import pages
from materials import materials_page
from practice import practice_page
from admin import admin_page
from auth import auth_page
from dashboard import dashboard_page
from matching import matchmaking_page

# Global UI Styles
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Poppins','Inter','Segoe UI',sans-serif; }
.stApp { background: linear-gradient(135deg,#f5f7fa,#eef1f5); }
section[data-testid="stSidebar"] { background: rgba(255,255,255,0.9); backdrop-filter: blur(12px); border-right: 1px solid rgba(200,200,200,0.3); }
.sidebar-header { padding:1.6rem; border-radius:20px; background: linear-gradient(135deg, #0f766e, #14b8a6, #22c55e); color:white; margin-bottom:1.4rem; text-align:center; box-shadow:0 12px 30px rgba(20,184,166,0.45); }
.sidebar-header .app-name { font-size:2.6rem; font-weight:800; letter-spacing:0.06em; }
.card { background: rgba(255,255,255,.95); border-radius:20px; padding:1.8rem; box-shadow:0 12px 30px rgba(0,0,0,.06); margin-bottom: 1.5rem; }
.donation-card { background: white; padding: 1.8rem; border-radius: 20px; border-left: 8px solid #10b981; margin-bottom: 1.5rem; box-shadow: 0 8px 20px rgba(0,0,0,0.04); }
.ripple-btn { background: #10b981; color: white !important; padding: 12px 24px; border: none; border-radius: 12px; cursor: pointer; font-weight: 600; text-decoration: none; display: inline-block; transition: background 0.5s; text-align: center; width: 100%; }
</style>
""", unsafe_allow_html=True)

# Session Initialization
for key, default in {"logged_in": False, "user_id": None, "user_name": "", "page": "Dashboard", "messages": [], "session_step": "discovery"}.items():
    st.session_state.setdefault(key, default)

if not st.session_state.logged_in:
    auth_page()
    st.stop()

# Sidebar Navigation
with st.sidebar:
    st.markdown(f'<div class="sidebar-header"><div class="app-name">Sahay</div><div class="username">{st.session_state.user_name}</div></div>', unsafe_allow_html=True)
    nav_options = ["Dashboard", "Matchmaking", "Learning Materials", "Practice", "AI Assistant", "Donations", "Admin"]
    for label in nav_options:
        if st.button(label, key=f"nav_{label}", use_container_width=True):
            st.session_state.page = label
            if label != "Matchmaking": st.session_state.session_step = "discovery"
            st.rerun()
    st.divider()
    if st.button("Logout", key="logout_btn", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- ROUTING ---
page = st.session_state.page
if page == "Dashboard": 
    dashboard_page()
elif page == "Matchmaking": 
    matchmaking_page()
elif page == "Learning Materials": 
    materials_page()
elif page == "Practice": 
    practice_page()
elif page == "AI Assistant":
    col_title, col_clear = st.columns([3, 1])
    with col_title:
        st.markdown("<div class='card'><h1 style='color:#0f766e; margin-bottom:0;'>Sahay AI Assistant</h1><p style='color:#64748b;'>Study Partner powered by Groq (Llama 3).</p></div>", unsafe_allow_html=True)
    
    with col_clear:
        st.write("")
        if st.button("Clear History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.markdown(message["content"])

    if prompt := st.chat_input("Ask Sahay AI..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                response = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "system", "content": "You are Sahay AI, an encouraging mentor for students."}] + 
                             [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                )
                res_text = response.choices[0].message.content
                st.markdown(res_text)
                st.session_state.messages.append({"role": "assistant", "content": res_text})
            except Exception as e:
                st.error("AI service error. Check your Groq API Key.")

elif page == "Donations":
    st.markdown("<div class='card'><h1 style='color:#0f766e;'>Support Education</h1><p style='color:#64748b;'>Help us bridge the educational gap.</p></div>", unsafe_allow_html=True)
    donations = [
        {"name": "Pratham", "url": "https://pratham.org/donation/", "desc": "Improving quality of education."},
        {"name": "Akshaya Patra", "url": "https://www.akshayapatra.org/onlinedonations", "desc": "Mid-day meals for students."},
        {"name": "Teach For India", "url": "https://www.teachforindia.org/donate", "desc": "Educational leadership."}
    ]
    for org in donations:
        st.markdown(f'''
            <div class="donation-card">
                <h3 style="margin:0; color:#0f766e;">{org["name"]}</h3>
                <p style="margin:0; color:#4b5563; font-size:0.95rem;">{org["desc"]}</p>
                <br><a href="{org["url"]}" target="_blank" class="ripple-btn">Donate Now</a>
            </div>
        ''', unsafe_allow_html=True)

elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")
    if key == "ngo-admin-123": admin_page()
