import streamlit as st
import time
from datetime import timedelta
from database import cursor, conn
from streak import init_streak, render_streak_ui

# Note: Ensure 'client' is imported or available from your main app script
# If this is a separate file, you may need: from ai_helper import client

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
        INSERT INTO rematch_requests (from_user, to_user)
        VALUES (?, ?)
    """, (st.session_state.user_id, to_user_id))
    conn.commit()

def load_incoming_requests(user_id):
    cursor.execute("""
        SELECT rr.id, au.name, au.id
        FROM rematch_requests rr
        JOIN auth_users au ON au.id = rr.from_user
        WHERE rr.to_user = ? AND rr.status = 'pending'
    """, (user_id,))
    return cursor.fetchall()

def accept_request(req_id, from_user_id):
    cursor.execute("""
        UPDATE rematch_requests SET status='accepted' WHERE id=?
    """, (req_id,))
    conn.commit()
    cursor.execute("""
        UPDATE profiles SET status='waiting', match_id=NULL
        WHERE user_id IN (?, ?)
    """, (st.session_state.user_id, from_user_id))
    conn.commit()

# =====================================================
# DASHBOARD
# =====================================================
def dashboard_page():
    init_streak()

    st.title(f"Welcome back, {st.session_state.user_name}")
    st.caption("Your learning journey at a glance")
    st.divider()

    # -------------------------------------------------
    # PROFILE FETCH
    # -------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles WHERE user_id=?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    edit_mode = st.session_state.get("edit_profile", False)

    # -------------------------------------------------
    # PROFILE CREATE / EDIT
    # -------------------------------------------------
    if not profile or edit_mode:
        st.subheader("Profile Setup" if not profile else " Edit Profile")

        db_role = profile[0] if profile else "Student"
        raw_grade = profile[1] if profile else "Grade 1"
        try:
            grade_index = int(str(raw_grade).split()[-1]) - 1
            grade_index = max(0, min(grade_index, 9))
        except:
            grade_index = 0

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
                st.info("As a Student, tell us your strengths and areas for improvement.")
                strong = st.multiselect("Strong Subjects", SUBJECTS, default=strong_list)
                weak = st.multiselect("Weak Subjects", SUBJECTS, default=weak_list)
            else:
                st.info("As a Teacher, select the subjects you are qualified to instruct.")
                teaches = st.multiselect("Subjects You Teach", SUBJECTS, default=teach_list)

            submitted = st.form_submit_button("Save Profile")

            if submitted:
                cursor.execute("""
                    INSERT OR REPLACE INTO profiles (
                        user_id, role, grade, time,
                        strong_subjects, weak_subjects, teaches, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting')
                """, (
                    st.session_state.user_id, role, grade, time_slot,
                    ",".join(strong) if role == "Student" else "",
                    ",".join(weak) if role == "Student" else "",
                    ",".join(teaches) if role == "Teacher" else ""
                ))
                conn.commit()
                st.session_state.edit_profile = False
                st.success("Profile saved successfully!")
                st.rerun()
        return

    # -------------------------------------------------
    # PROFILE OVERVIEW
    # -------------------------------------------------
    role, grade, time_slot, strong, weak, teaches = profile
    st.subheader("Profile Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Role", role)
    c2.metric("Grade", grade)
    c3.metric("Time Slot", time_slot)

    st.write("")
    col1, col2 = st.columns(2)

    if role == "Student":
        with col1:
            st.markdown("### Strong Subjects")
            s_list = strong.split(",") if strong else []
            if s_list:
                for s in s_list: st.success(s)
            else: st.info("None added")
        with col2:
            st.markdown("### Weak Subjects")
            w_list = weak.split(",") if weak else []
            if w_list:
                for w in w_list: st.warning(w)
            else: st.info("None added")
    else:
        with col1:
            st.markdown("### Subjects You Teach")
            t_list = teaches.split(",") if teaches else []
            if t_list:
                for t in t_list: st.success(t)
            else: st.info("None added")

    st.write("")
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
                st.write(f"**Session ID:** {match_id}")
                if st.button(f"↻ Request Re-match with {partner_name}", key=f"rematch_{match_id}"):
                    send_rematch_request(partner_id)
                    st.success("Re-match request sent!")

    st.divider()

    # -------------------------------------------------
    # REMATCH REQUESTS
    # -------------------------------------------------
    st.subheader("Rematch Requests")
    requests = load_incoming_requests(st.session_state.user_id)
    if not requests:
        st.info("No new requests.")
    else:
        for req_id, sender_name, sender_id in requests:
            col1, col2 = st.columns([3,1])
            col1.write(f"👤 {sender_name} wants to study again")
            if col2.button("Accept", key=f"accept_{req_id}"):
                accept_request(req_id, sender_id)
                st.success("Accepted! Go to Matchmaking.")
                st.rerun()
