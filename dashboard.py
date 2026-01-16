import streamlit as st
import time
import uuid
import requests
from datetime import timedelta
from database import cursor, conn
from streak import init_streak, render_streak_ui
from streamlit_lottie import st_lottie

SUBJECTS = ["Mathematics", "English", "Science"]
TIME_SLOTS = ["4-5 PM", "5-6 PM", "6-7 PM"]

# -----------------------------------------------------
# UI & ANIMATION HELPERS
# -----------------------------------------------------
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def inject_emerald_dashboard_styles():
    st.markdown("""
        <style>
        .stApp { background-color: #f0fdf4; }
        
        /* Emerald Card Style */
        .profile-card {
            background: white;
            padding: 30px;
            border-radius: 24px;
            border-bottom: 6px solid #10b981;
            box-shadow: 0 12px 30px rgba(5, 150, 105, 0.08);
            margin-bottom: 25px;
            color: #064e3b;
        }

        /* Metric Box Styling */
        [data-testid="stMetricValue"] {
            color: #059669 !important;
            font-weight: 800 !important;
        }

        /* Ripple-Effect Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 0.7rem 1.5rem !important;
            font-weight: 700 !important;
            width: 100%;
            transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
            box-shadow: 0 4px 10px rgba(16, 185, 129, 0.2) !important;
        }

        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 18px rgba(16, 185, 129, 0.3) !important;
            filter: brightness(1.05);
        }

        /* Active Session Pulse */
        .pulse-box {
            background: #ecfdf5;
            border: 2px solid #10b981;
            padding: 15px;
            border-radius: 15px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------
# CORE LOGIC HELPERS (UNCHANGED FEATURES)
# -----------------------------------------------------
def calculate_streak(dates):
    if not dates: return 0
    dates = sorted(set(dates), reverse=True)
    streak = 1
    for i in range(len(dates) - 1):
        if dates[i] - dates[i + 1] == timedelta(days=1): streak += 1
        else: break
    return streak

def load_match_history(user_id):
    cursor.execute("""
        SELECT sr.match_id, sr.rating, au.id, au.name
        FROM session_ratings sr
        JOIN auth_users au ON au.id != sr.rater_id
        WHERE sr.rater_id = ?
        ORDER BY sr.rowid DESC
    """, (user_id,))
    return cursor.fetchall()

def send_rematch_request(to_user_id):
    cursor.execute("""
        INSERT INTO rematch_requests (from_user, to_user, status, seen)
        VALUES (?, ?, 'pending', 0)
    """, (st.session_state.user_id, to_user_id))
    conn.commit()

def load_incoming_requests(user_id):
    cursor.execute("""
        SELECT rr.id, au.name, au.id, rr.seen
        FROM rematch_requests rr
        JOIN auth_users au ON au.id = rr.from_user
        WHERE rr.to_user = ? AND rr.status = 'pending'
        ORDER BY rr.id DESC
    """, (user_id,))
    return cursor.fetchall()

def accept_request(req_id, from_user_id):
    new_match_id = f"rematch_{uuid.uuid4().hex[:8]}"
    cursor.execute("UPDATE rematch_requests SET status='accepted' WHERE id=?", (req_id,))
    cursor.execute("""
        UPDATE profiles SET status='matched', match_id=?, accepted=1 
        WHERE user_id IN (?, ?)
    """, (new_match_id, st.session_state.user_id, from_user_id))
    conn.commit()
    return new_match_id

def check_notifications():
    cursor.execute("""
        SELECT COUNT(*) FROM rematch_requests 
        WHERE to_user = ? AND status = 'pending' AND seen = 0
    """, (st.session_state.user_id,))
    unread = cursor.fetchone()[0]
    if unread > 0:
        st.toast(f"New connection request received!", icon="🟢")
        cursor.execute("UPDATE rematch_requests SET seen = 1 WHERE to_user = ?", (st.session_state.user_id,))
        conn.commit()

# =====================================================
# DASHBOARD PAGE
# =====================================================
def dashboard_page():
    inject_emerald_dashboard_styles()
    init_streak()
    check_notifications()

    # Load Animations
    anim_welcome = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_m6cuL6.json")
    anim_history = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_vnik96pv.json")
    anim_alert = load_lottieurl("https://assets3.lottiefiles.com/packages/lf20_Tkwjw8.json")

    # 1. Active Session Pulse
    cursor.execute("SELECT status, match_id FROM profiles WHERE user_id=?", (st.session_state.user_id,))
    current_status = cursor.fetchone()

    if current_status and current_status[0] == 'matched':
        st.markdown("""
            <div class='pulse-box'>
                <h4 style='color:#065f46; margin:0;'>Learning Node Active</h4>
                <p style='color:#065f46; font-size:0.9rem;'>Your partner is waiting in the live session.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Join Session", key="join_pulse"):
            st.session_state.page = "Matchmaking"
            st.rerun()
        st.write("")

    # 2. Welcome Header
    col_w1, col_w2 = st.columns([0.7, 0.3])
    with col_w1:
        st.markdown(f"<h1 style='color:#064e3b; margin-bottom:0;'>Hello, {st.session_state.user_name}</h1>", unsafe_allow_html=True)
        st.caption("Central Learning Hub | Emerald Network")
    with col_w2:
        if anim_welcome: st_lottie(anim_welcome, height=100, key="welcome_anim")

    st.divider()

    # 3. Profile Logic
    cursor.execute("SELECT role, grade, time, strong_subjects, weak_subjects, teaches FROM profiles WHERE user_id=?", (st.session_state.user_id,))
    profile = cursor.fetchone()
    edit_mode = st.session_state.get("edit_profile", False)

    if not profile or edit_mode:
        with st.container():
            st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
            st.subheader("Update Node Profile")
            db_role = profile[0] if profile else "Student"
            # (Selection logic remains same as original)
            with st.form("profile_form"):
                role = st.selectbox("Current Role", ["Student", "Teacher"], index=0 if db_role=="Student" else 1)
                grade = st.selectbox("Class Level", [f"Grade {i}" for i in range(1, 11)])
                time_slot = st.selectbox("Preferred Time", TIME_SLOTS)
                
                if role == "Student":
                    strong = st.multiselect("Proficient Subjects", SUBJECTS)
                    weak = st.multiselect("Focus Subjects", SUBJECTS)
                    teaches = []
                else:
                    teaches = st.multiselect("Instructional Subjects", SUBJECTS)
                    strong, weak = [], []

                if st.form_submit_button("Synchronize Profile"):
                    cursor.execute("""
                        INSERT OR REPLACE INTO profiles (
                            user_id, role, grade, time, strong_subjects, weak_subjects, teaches, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting')
                    """, (st.session_state.user_id, role, grade, time_slot,
                        ",".join(strong), ",".join(weak), ",".join(teaches)))
                    conn.commit()
                    st.session_state.edit_profile = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        return

    # 4. Profile Display
    role, grade, time_slot, strong, weak, teaches = profile
    st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Network Role", role)
    c2.metric("Grade level", grade)
    c3.metric("Time Slot", time_slot)
    
    if st.button("Edit Profile Details"):
        st.session_state.edit_profile = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # 5. Streak Section
    render_streak_ui()
    st.write("")

    # 6. History & Requests
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### Session History")
        history = load_match_history(st.session_state.user_id)
        if not history:
            st.caption("No history logged yet.")
        else:
            for m_id, rat, p_id, p_name in history:
                with st.expander(f"Partner: {p_name} | ⭐ {rat}"):
                    if st.button("Request Rematch", key=f"rem_{m_id}"):
                        send_rematch_request(p_id)
                        st.success("Request Broadcasted")

    with col_right:
        st.markdown("### Incoming Requests")
        reqs = load_incoming_requests(st.session_state.user_id)
        if not reqs:
            st.caption("No pending requests.")
            if anim_history: st_lottie(anim_history, height=120, key="hist_anim")
        else:
            for rid, sname, sid, seen in reqs:
                st.markdown(f"""
                    <div style='background:white; padding:10px; border-radius:10px; border-left:4px solid #10b981; margin-bottom:10px;'>
                        <small style='color:#10b981;'>REMATCH REQUEST</small><br>
                        <b>{sname}</b> is ready to study.
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Accept & Sync", key=f"acc_{rid}"):
                    accept_request(rid, sid)
                    st.session_state.page = "Matchmaking"
                    st.rerun()
