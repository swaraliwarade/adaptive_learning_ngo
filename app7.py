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
# GLOBAL UI STYLES (UNCHANGED)
# =========================================================
st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Inter','Segoe UI',sans-serif; }

.stApp { background: linear-gradient(135deg,#f5f7fa,#eef1f5); }
@media (prefers-color-scheme: dark) {
  .stApp { background: linear-gradient(135deg,#121212,#1c1c1c); }
}

section[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(200,200,200,0.3);
}

.sidebar-header {
  padding:1.2rem;border-radius:16px;
  background:linear-gradient(135deg,#6366f1,#4f46e5);
  color:white;margin-bottom:1rem;
}

.nav-item {
  display:flex;align-items:center;gap:.75rem;
  padding:.65rem .9rem;border-radius:12px;
}
.nav-item:hover { background: rgba(99,102,241,.12); }
.nav-active {
  background: rgba(99,102,241,.22);
  border-left:4px solid #4f46e5;
}

.card {
  background: rgba(255,255,255,.92);
  border-radius:18px;padding:1.6rem;
  box-shadow:0 12px 30px rgba(0,0,0,.06);
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
    "proposed_match": None,   # NEW
    "proposed_score": None    # NEW
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
      <h3 style="margin:0;">Sahay</h3>
      <p style="margin:0;font-size:.85rem;">{st.session_state.user_name}</p>
    </div>
    """, unsafe_allow_html=True)

    for label in ["Dashboard","Matchmaking","Learning Materials","Practice","Admin"]:
        if st.button(label, use_container_width=True):
            st.session_state.page = label
            st.rerun()

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
elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")
    if key == "ngo-admin-123":
        admin_page()
