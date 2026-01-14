import streamlit as st
import time
from datetime import timedelta
from database import cursor, conn
from streak import init_streak, render_streak_ui

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
        SELECT rr.id, au.name
        FROM rematch_requests rr
        JOIN auth_users au ON au.id = rr.from_user
        WHERE rr.to_user = ? AND rr.status = 'pending'
    """, (user_id,))
    return cursor.fetchall()


def accept_request(req_id, from_user):
    cursor.execute("""
        UPDATE rematch_requests SET status='accepted' WHERE id=?
    """, (req_id,))
    conn.commit()

    # Put both users back into waiting
    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE user_id IN (?, ?)
    """, (st.session_state.user_id, from_user))
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
    # PROFILE
    # -------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles WHERE user_id=?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    if not profile:
        st.warning("Please complete your profile from Dashboard.")
        return

    role, grade, time_slot, strong, weak, teaches = profile

    st.subheader("Profile Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Role", role)
    c2.metric("Grade", grade)
    c3.metric("Time Slot", time_slot)

    st.divider()

    render_streak_ui()
    st.divider()

    # -------------------------------------------------
    # 📜 MATCH HISTORY
    # -------------------------------------------------
    st.subheader("📜 Match History")

    history = load_match_history(st.session_state.user_id)

    if not history:
        st.info("No completed sessions yet.")
    else:
        for match_id, rating, partner_id, partner_name in history:
            with st.expander(f"👤 {partner_name} • ⭐ {rating}/5"):
                st.write(f"**Session ID:** {match_id}")
                st.write(f"**Rating Given:** {rating}/5")

                if st.button(
                    f"🔁 Request Re-match with {partner_name}",
                    key=f"rematch_{match_id}"
                ):
                    send_rematch_request(partner_id)
                    st.success("Re-match request sent!")

    st.divider()

    # -------------------------------------------------
    # 🔔 INCOMING REMATCH REQUESTS
    # -------------------------------------------------
    st.subheader("🔔 Rematch Requests")

    requests = load_incoming_requests(st.session_state.user_id)

    if not requests:
        st.info("No new requests.")
    else:
        for req_id, sender_name in requests:
            col1, col2 = st.columns([3,1])
            col1.write(f"👤 {sender_name} wants to study again")
            if col2.button("Accept", key=f"accept_{req_id}"):
                accept_request(req_id, sender_name)
                st.success("Request accepted! Go to Matchmaking.")
                st.rerun()
