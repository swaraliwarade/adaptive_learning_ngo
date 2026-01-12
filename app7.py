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
from database import init_db, cursor, conn

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

/* Typography */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

/* Background */
.stApp {
    background: linear-gradient(135deg, #f5f7fa, #eef1f5);
}
@media (prefers-color-scheme: dark) {
    .stApp {
        background: linear-gradient(135deg, #121212, #1c1c1c);
    }
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.85);
    backdrop-filter: blur(12px);
    border-right: 1px solid rgba(200,200,200,0.3);
}
@media (prefers-color-scheme: dark) {
    section[data-testid="stSidebar"] {
        background: rgba(20,20,20,0.9);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
}

/* Sidebar header */
.sidebar-header {
    padding: 1.2rem;
    border-radius: 16px;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: white;
    margin-bottom: 1rem;
}

/* Navigation item */
.nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.65rem 0.9rem;
    margin-bottom: 0.4rem;
    border-radius: 12px;
    font-weight: 500;
    transition: all 0.2s ease;
}
.nav-item:hover {
    background: rgba(99,102,241,0.12);
}
.nav-active {
    background: rgba(99,102,241,0.22);
    border-left: 4px solid #4f46e5;
}

/* SVG icon base */
.nav-icon {
    width: 20px;
    height: 20px;
    background-color: currentColor;
    mask-size: contain;
    mask-repeat: no-repeat;
    mask-position: center;
    -webkit-mask-size: contain;
    -webkit-mask-repeat: no-repeat;
    -webkit-mask-position: center;
}

/* ---------- BETTER SVG ICONS ---------- */

/* Dashboard – analytics tiles */
.icon-dashboard {
    mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='3' width='7' height='7' rx='2'/><rect x='14' y='3' width='7' height='11' rx='2'/><rect x='3' y='14' width='11' height='7' rx='2'/></svg>");
}

/* Matchmaking – people connection */
.icon-match {
    mask-image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='7' cy='8' r='3'/><circle cx='17' cy='8' r='3'/><path d='M2 20c0-3 3-5 5-5'/><path d='M22 20c0-3-3-5-5-5'/><path d='M9 13h6'/></svg>\");
}

/* Materials – stacked books */
.icon-materials {
    mask-image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='4' width='14' height='4' rx='1'/><rect x='3' y='10' width='18' height='4' rx='1'/><rect x='3' y='16' width='16' height='4' rx='1'/></svg>\");
}

/* Practice – pencil/edit */
.icon-practice {
    mask-image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M3 21l3-1 12-12-2-2L4 18l-1 3z'/><path d='M14 4l2 2'/></svg>\");
}

/* Admin – shield/settings */
.icon-admin {
    mask-image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 3l8 4v5c0 5-3.5 9-8 9s-8-4-8-9V7l8-4z'/><circle cx='12' cy='13' r='2'/></svg>\");
}

/* Cards */
.card {
    background: rgba(255,255,255,0.92);
    border-radius: 18px;
    padding: 1.6rem;
    box-shadow: 0 12px 30px rgba(0,0,0,0.06);
    margin-bottom: 1.6rem;
}
@media (prefers-color-scheme: dark) {
    .card {
        background: rgba(30,30,30,0.9);
        box-shadow: 0 12px 30px rgba(0,0,0,0.35);
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
    "stage": 1,
    "profile": {},
    "current_match": None,
    "page": "Dashboard"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

SUBJECTS = ["Mathematics", "English", "Science"]

# =========================================================
# AUTH GATE
# =========================================================
if not st.session_state.logged_in:
    auth_page()
    st.stop()

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:

    st.markdown(f"""
    <div class="sidebar-header">
        <h3 style="margin:0;">Sahay</h3>
        <p style="margin:0;font-size:0.85rem;opacity:0.9;">
            {st.session_state.user_name}
        </p>
    </div>
    """, unsafe_allow_html=True)

    nav_items = [
        ("Dashboard", "icon-dashboard"),
        ("Matchmaking", "icon-match"),
        ("Learning Materials", "icon-materials"),
        ("Practice", "icon-practice"),
        ("Admin", "icon-admin")
    ]

    for label, icon in nav_items:
        active = "nav-active" if st.session_state.page == label else ""
        st.markdown(
            f"""
            <div class="nav-item {active}">
                <span class="nav-icon {icon}"></span>
                <span>{label}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button(label, key=f"nav_{label}", use_container_width=True):
            st.session_state.page = label
            st.rerun()

    st.divider()

    if st.button("Logout", use_container_width=True):
        for k in ["logged_in", "user_id", "user_name", "profile", "current_match"]:
            st.session_state[k] = None if k != "logged_in" else False
        st.session_state.stage = 1
        st.session_state.page = "Dashboard"
        st.rerun()

page = st.session_state.page

# =========================================================
# PAGE ROUTING
# =========================================================
if page == "Dashboard":
    dashboard_page()

elif page == "Matchmaking":
    matchmaking_page()

elif page == "Learning Materials":
    materials_page()

elif page == "Practice":
    practice_page()

elif page == "Admin":
    admin_key = st.text_input("Admin Access Key", type="password")
    if admin_key == "ngo-admin-123":
        admin_page()
    else:
        st.warning("Unauthorized access")

