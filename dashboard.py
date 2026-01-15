import streamlit as st
import time
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
        SELECT 
            sr.match_id,
            sr.rating,
            au.id,
            au.name
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
        UPDATE profiles
        SET status='waiting', match_id=NULL
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

        # prefill values
        role = profile[0] if profile else "Student"
        grade = profile[1] if profile else "Grade 1"
        time_slot = profile[2] if profile else TIME_SLOTS[0]
        strong_list = profile[3].split(",") if profile and profile[3] else []
        weak_list = profile[4].split(",") if profile and profile[4] else []
        teach_list = profile[5].split(",") if profile and profile[5] else []

        with st.form("profile_form"):
            role = st.radio("Role", ["Student", "Teacher"], horizontal=True, index=0 if role=="Student" else 1)
            grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)], index=int(grade.split()[-1]) - 1)
            time_slot = st.selectbox("Available Time Slot", TIME_SLOTS, index=TIME_SLOTS.index(time_slot))

            strong, weak, teaches = [], [], []

            if role == "Student":
                strong = st.multiselect("Strong Subjects", SUBJECTS, default=strong_list)
                weak = st.multiselect("Weak Subjects", SUBJECTS, default=weak_list)
            else:
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
                st.session_state.user_id,
                role,
                grade,
                time_slot,
                ",".join(strong),
                ",".join(weak),
                ",".join(teaches)
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
    strong_list = strong.split(",") if strong else []
    weak_list = weak.split(",") if weak else []
    teach_list = teaches.split(",") if teaches else []

    st.subheader("Profile Overview")

    c1, c2, c3 = st.columns(3)
    c1.metric("Role", role)
    c2.metric("Grade", grade)
    c3.metric("Time Slot", time_slot)

    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Strong Subjects")
        if strong_list or teach_list:
            for s in (strong_list or teach_list):
                st.success(s)
        else:
            st.info("Not added")

    with col2:
        st.markdown("### Weak Subjects")
        if weak_list:
            for w in weak_list:
                st.warning(w)
        else:
            st.info("Not added")

    st.write("")
    if st.button("✎ Edit Profile"):
        st.session_state.edit_profile = True
        st.rerun()

    st.divider()

    # -------------------------------------------------
    # STREAK
    # -------------------------------------------------
    render_streak_ui()
    st.divider()

    # -------------------------------------------------
    # 📜 MATCH HISTORY
    # -------------------------------------------------
    st.subheader("⚙︎ Match History")

    history = load_match_history(st.session_state.user_id)

    if not history:
        st.info("No completed sessions yet.")
    else:
        for match_id, rating, partner_id, partner_name in history:
            with st.expander(f"👤 {partner_name} • ⭐ {rating}/5"):
                st.write(f"**Session ID:** {match_id}")
                st.write(f"**Rating Given:** {rating}/5")

                if st.button(
                    f"↻ Request Re-match with {partner_name}",
                    key=f"rematch_{match_id}"
                ):
                    send_rematch_request(partner_id)
                    st.success("Re-match request sent!")

    st.divider()

    # -------------------------------------------------
    # 🔔 REMATCH REQUESTS
    # -------------------------------------------------
    st.subheader("⚙︎ Rematch Requests")

    requests = load_incoming_requests(st.session_state.user_id)

    if not requests:
        st.info("No new requests.")
    else:
        for req_id, sender_name, sender_id in requests:
            col1, col2 = st.columns([3,1])
            col1.write(f"👤 {sender_name} wants to study again")
            if col2.button("Accept", key=f"accept_{req_id}"):
                accept_request(req_id, sender_id)
                st.success("Request accepted! Go to Matchmaking.")
                st.rerun()
