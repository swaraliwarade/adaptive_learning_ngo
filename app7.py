import streamlit as st
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
# INIT DATABASE
# =========================================================
init_db()

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Sahay | Peer Learning Matchmaking",
    layout="wide"
)

# =========================================================
# GLOBAL UI STYLES
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins','Inter','Segoe UI',sans-serif;
}

/* App background */
.stApp {
    background: linear-gradient(135deg,#f5f7fa,#eef1f5);
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(200,200,200,0.3);
}

/* Sidebar header */
.sidebar-header {
  padding:1.4rem;
  border-radius:18px;
  background:linear-gradient(135deg,#6366f1,#4f46e5);
  color:white;
  margin-bottom:1.2rem;
  text-align:center;
}

/* Cards */
.card {
  background: rgba(255,255,255,.95);
  border-radius:20px;
  padding:1.8rem;
  box-shadow:0 12px 30px rgba(0,0,0,.06);
}

/* ================= DONATE BUTTON ================= */
.donate-btn {
  position:relative;
  overflow:hidden;
  display:block;
  width:100%;
  padding:0.9rem 1rem;
  margin-top:1rem;
  border-radius:999px;
  text-align:center;
  font-weight:700;
  font-size:0.95rem;

  color:#ffffff !important;
  text-decoration:none !important;

  background:linear-gradient(135deg,#6366f1,#4f46e5);
  cursor:pointer;
  transition:transform 0.25s ease, box-shadow 0.25s ease;
}

/* Hover */
.donate-btn:hover {
  transform:translateY(-2px);
  box-shadow:0 10px 25px rgba(79,70,229,.35);
  background:linear-gradient(135deg,#4f46e5,#4338ca);
}

/* ================= RIPPLE EFFECT ================= */
.donate-btn::after {
  content:"";
  position:absolute;
  top:50%;
  left:50%;
  width:10px;
  height:10px;
  background:rgba(255,255,255,0.45);
  border-radius:50%;
  transform:translate(-50%,-50%) scale(0);
  opacity:0;
}

.donate-btn:active::after {
  animation:ripple 0.6s ease-out;
}

@keyframes ripple {
  0% {
    transform:translate(-50%,-50%) scale(0);
    opacity:0.7;
  }
  100% {
    transform:translate(-50%,-50%) scale(20);
    opacity:0;
  }
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
    "proposed_score": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

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
        <div style="font-size:2.4rem;font-weight:700;">
            Sahay
        </div>
        <div style="margin-top:0.45rem;font-size:0.95rem;">
            {st.session_state.user_name}
        </div>
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
    <div class="card">
        <h2>🤝 Support Education & Nutrition</h2>
        <p>
            Your contribution helps children learn better, stay nourished,
            and build a brighter future.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="card">
            <h4>Pratham</h4>
            <p>Improving foundational learning outcomes for millions of children.</p>
            <a class="donate-btn" href="https://pratham.org/donation/" target="_blank">
                Donate to Pratham
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
            <h4>Akshaya Patra</h4>
            <p>Ensuring no child is deprived of education due to hunger.</p>
            <a class="donate-btn" href="https://www.akshayapatra.org/onlinedonations" target="_blank">
                Donate to Akshaya Patra
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="card">
            <h4>Teach For India</h4>
            <p>Building a movement to eliminate educational inequity.</p>
            <a class="donate-btn" href="https://www.teachforindia.org/donate" target="_blank">
                Donate to Teach For India
            </a>
        </div>
        """, unsafe_allow_html=True)

elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")
    if key == "ngo-admin-123":
        admin_page()
