import streamlit as st
import time
from datetime import date, timedelta
from database import cursor, conn

SUBJECTS = ["Mathematics", "English", "Science"]
TIME_SLOTS = ["4-5 PM", "5-6 PM", "6-7 PM"]

# =========================================================
# HELPERS
# =========================================================
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


# =========================================================
# DASHBOARD PAGE
# =========================================================
def dashboard_page():

    # -----------------------------------------------------
    # HERO
    # -----------------------------------------------------
    st.markdown(f"""
    <div class="card" style="
        background: linear-gradient(135deg, #6366f1, #4f46e5);
        color: white;
    ">
        <h2>Welcome back, {st.session_state.user_name}</h2>
        <p>Track your learning, mentoring, and impact — all in one place.</p>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------
    # PROFILE FETCH
    # -----------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    # =====================================================
    # PROFILE SETUP (IF NOT EXISTS)
    # =====================================================
    if not profile:
        st.markdown("""
        <div class="card">
            <h3>Complete Your Profile</h3>
            <p>
                Before we can match you with the right peers,
                please tell us about your grade, subjects, and availability.
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("profile_setup"):
            role = st.radio("Role", ["Student", "Teacher"], horizontal=True)
            grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])
            time_slot = st.selectbox("Available Time Slot", TIME_SLOTS)

            strong, weak, teaches = [], [], []

            if role == "Student":
                weak = st.multiselect("Subjects you need help with", SUBJECTS)
                strong = st.multiselect("Subjects you are good at", SUBJECTS)
            else:
                teaches = st.multiselect("Subjects you can teach", SUBJECTS)

            submitted = st.form_submit_button("Save Profile")

        if submitted:
            cursor.execute("DELETE FROM profiles WHERE user_id = ?", (st.session_state.user_id,))
            cursor.execute("""
                INSERT INTO profiles
                (user_id, role, grade, class, time, strong_subjects, weak_subjects, teaches)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state.user_id,
                role,
                grade,
                int(grade.split()[-1]),
                time_slot,
                ",".join(strong),
                ",".join(weak),
                ",".join(teaches)
            ))
            conn.commit()

            st.success("Profile saved successfully.")
            st.rerun()

        return  # STOP dashboard until profile exists

    # =====================================================
    # DASHBOARD CONTENT (PROFILE EXISTS)
    # =====================================================
    role, grade, time_slot, strong, weak, teaches = profile
    subjects = (teaches or strong or weak or "—").replace(",", ", ")

    # -----------------------------------------------------
    # PROFILE CARD
    # -----------------------------------------------------
    st.markdown(f"""
    <div class="card">
        <h3>Your Profile</h3>
        <div style="display:flex; gap:2rem; flex-wrap:wrap;">
            <div><strong>Role</strong><br>{role}</div>
            <div><strong>Grade</strong><br>{grade}</div>
            <div><strong>Time Slot</strong><br>{time_slot}</div>
            <div><strong>Subjects</strong><br>{subjects}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------
    # SESSION DATA
    # -----------------------------------------------------
    cursor.execute("""
        SELECT mentor, rating, session_date
        FROM ratings
        WHERE mentor = ? OR mentee = ?
    """, (st.session_state.user_name, st.session_state.user_name))

    rows = cursor.fetchall()
    session_dates = [r[2] for r in rows]

    streak = calculate_streak(session_dates)
    total_sessions = len(rows)
    avg_rating = round(sum(r[1] for r in rows) / total_sessions, 2) if total_sessions else "—"

    # -----------------------------------------------------
    # LEADERBOARD
    # -----------------------------------------------------
    cursor.execute("""
        SELECT mentor, COUNT(*) AS sessions, AVG(rating) AS avg_rating
        FROM ratings
        GROUP BY mentor
        ORDER BY sessions DESC, avg_rating DESC
    """)
    leaderboard = cursor.fetchall()

    leaderboard_rank = next(
        (i + 1 for i, r in enumerate(leaderboard) if r[0] == st.session_state.user_name),
        "—"
    )

    # -----------------------------------------------------
    # STATS
    # -----------------------------------------------------
    st.markdown("### Your Progress")

    c1, c2, c3, c4 = st.columns(4)

    with st.spinner("Loading insights..."):
        time.sleep(0.3)

    c1.metric("Day Streak", streak)
    c2.metric("Leaderboard Rank", f"#{leaderboard_rank}")
    c3.metric("Sessions Completed", total_sessions)
    c4.metric("Average Rating", avg_rating)

    st.markdown("**Consistency Goal (30 days)**")
    st.progress(min(streak / 30, 1.0))

    st.divider()

    # -----------------------------------------------------
    # SESSION HISTORY
    # -----------------------------------------------------
    st.markdown("### Recent Sessions")

    if rows:
        history = [{
            "Partner": r[0],
            "Rating": r[1],
            "Date": r[2].strftime("%d %b %Y")
        } for r in rows[-10:][::-1]]

        st.dataframe(history, use_container_width=True)
    else:
        st.info("No sessions yet — start matchmaking to begin your journey.")
