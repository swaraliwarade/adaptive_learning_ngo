import streamlit as st
import time
import uuid
from datetime import timedelta
from database import cursor, conn
from streak import init_streak, render_streak_ui

SUBJECTS = ["Mathematics", "English", "Science"]
TIME_SLOTS = ["4-5 PM", "5-6 PM", "6-7 PM"]

# -----------------------------------------------------
# HELPERS
# -----------------------------------------------------
def calculate_streak(dates):
    if not dates:
        return 0
    dates = sorted(set(dates), reverse=True)
    streak = 1
    for i in range(len(dates) - 1):
        if dates[i] - dates[i + 1] == timedelta(days=1):
            streak += 1
        else:
            break
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
    # Create a unique shared session ID
    new_match_id = f"rematch_{uuid.uuid4().hex[:8]}"
    
    # Mark request as accepted
    cursor.execute("UPDATE rematch_requests SET status='accepted' WHERE id=?", (req_id,))
    
    # Put both users in 'matched' status with the same ID
    cursor.execute("""
        UPDATE profiles 
        SET status='matched', match_id=?, accepted=1 
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
        st.toast(f"✨ You have {unread} new rematch request(s)!", icon="🔔")
        cursor.execute("UPDATE rematch_requests SET seen = 1 WHERE to_user = ?", (st.session_state.user_id,))
        conn.commit()

# =====================================================
# DASHBOARD
# =====================================================
def dashboard_page():
    init_streak()
    check_notifications()

    # -------------------------------------------------
    # ACTIVE SESSION DETECTION (For Rematches)
    # -------------------------------------------------
    cursor.execute("SELECT status, match_id FROM profiles WHERE user_id=?", (st.session_state.user_id,))
    current_status = cursor.fetchone()

    if current_status and current_status[0] == 'matched':
        st.warning("🚀 **You have an active study session ready!**")
        if st.button("Join Your Partner Now", use_container_width=True):
            st.session_state.page = "Matchmaking"
            st.rerun()
        st.divider()

    st.title(f"Welcome back, {st.session_state.user_name}")
    st.caption("Your learning journey at a glance")
    st.divider()

    # -------------------------------------------------
    # PROFILE FETCH & EDIT LOGIC
    # -------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles WHERE user_id=?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    edit_mode = st.session_state.get("edit_profile", False)

    if not profile or edit_mode:
        st.subheader("Profile Setup" if not profile else " Edit Profile")
        db_role = profile[0] if profile else "Student"
        raw_grade = profile[1] if profile else "Grade 1"
        try:
            grade_index = int(str(raw_grade).split()[-1]) - 1
            grade_index = max(0, min(grade_index, 9))
        except: grade_index = 0

        time_val = profile[2] if profile else TIME_SLOTS[0]
        ts_index = TIME_SLOTS.index(time_val) if time_val in TIME_SLOTS else 0

        strong_list = profile[3].split(",") if profile and profile[3] else []
        weak_list = profile[4].split(",") if profile and profile[4] else []
        teach_list = profile[5].split(",") if profile and profile[5] else []

        with st.form("profile_form"):
            role = st.selectbox("I am a:", ["Student", "Teacher"], index=0 if db_role=="Student" else 1)
            grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)], index=grade_index)
            time_slot = st.selectbox("Available Time Slot", TIME_SLOTS, index=ts_index)

            strong, weak, teaches = [], [], []
            if role == "Student":
                strong = st.multiselect("Strong Subjects", SUBJECTS, default=strong_list)
                weak = st.multiselect("Weak Subjects", SUBJECTS, default=weak_list)
            else:
                teaches = st.multiselect("Subjects You Teach", SUBJECTS, default=teach_list)

            if st.form_submit_button("Save Profile"):
                cursor.execute("""
                    INSERT OR REPLACE INTO profiles (
                        user_id, role, grade, time,
                        strong_subjects, weak_subjects, teaches, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting')
                """, (st.session_state.user_id, role, grade, time_slot,
                    ",".join(strong) if role == "Student" else "",
                    ",".join(weak) if role == "Student" else "",
                    ",".join(teaches) if role == "Teacher" else ""))
                conn.commit()
                st.session_state.edit_profile = False
                st.rerun()
        return

    # -------------------------------------------------
    # PROFILE DISPLAY
    # -------------------------------------------------
    role, grade, time_slot, strong, weak, teaches = profile
    st.subheader("Profile Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Role", role); c2.metric("Grade", grade); c3.metric("Time Slot", time_slot)

    if st.button("✎ Edit Profile"):
        st.session_state.edit_profile = True
        st.rerun()

    st.divider()
    render_streak_ui()
    st.divider()

    # -------------------------------------------------
    # MATCH HISTORY
    # -------------------------------------------------
    st.subheader("Match History")
    history = load_match_history(st.session_state.user_id)
    if not history:
        st.info("No completed sessions yet.")
    else:
        for match_id, rating, partner_id, partner_name in history:
            with st.expander(f"👤 {partner_name} • ⭐ {rating}/5"):
                if st.button(f"↻ Request Re-match", key=f"rem_btn_{match_id}"):
                    send_rematch_request(partner_id)
                    st.success("Request sent!")

    st.divider()

    # -------------------------------------------------
    # REMATCH REQUESTS
    # -------------------------------------------------
    st.subheader("Rematch Requests")
    requests = load_incoming_requests(st.session_state.user_id)
    if not requests:
        st.info("No new requests.")
    else:
        for req_id, sender_name, sender_id, seen_status in requests:
            col1, col2 = st.columns([3,1])
            badge = " <span style='background:#ff4b4b; color:white; padding:2px 6px; border-radius:4px; font-size:10px;'>NEW</span>" if seen_status == 0 else ""
            col1.markdown(f"👤 **{sender_name}** wants to study again{badge}", unsafe_allow_html=True)
            
            if col2.button("Accept & Join", key=f"acc_{req_id}"):
                accept_request(req_id, sender_id)
                st.session_state.page = "Matchmaking"
                st.rerun()
