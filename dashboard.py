import streamlit as st
import time
from datetime import date, timedelta
from database import cursor

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
# DASHBOARD
# =========================================================
def dashboard_page():

    st.title(f"Hello, {st.session_state.user_name} 👋")

    # =====================================================
    # PROFILE
    # =====================================================
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))

    profile = cursor.fetchone()
    if not profile:
        st.warning("Please complete your profile first.")
        return

    role, grade, time_slot, strong, weak, teaches = profile

    st.subheader("Your Details")

    col1, col2 = st.columns(2)
    col1.write("**Role:** " + role)
    col1.write("**Grade:** " + grade)
    col1.write("**Time Slot:** " + time_slot)

    col2.write("**Subjects:**")
    col2.write((teaches or strong or weak or "—").replace(",", ", "))

    st.divider()

    # =====================================================
    # FETCH SESSION DATA
    # =====================================================
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

    # =====================================================
    # LEADERBOARD
    # =====================================================
    cursor.execute("""
        SELECT mentor, COUNT(*) as sessions, AVG(rating) as avg_rating
        FROM ratings
        GROUP BY mentor
        ORDER BY sessions DESC, avg_rating DESC
    """)
    leaderboard = cursor.fetchall()

    leaderboard_rank = next(
        (i + 1 for i, r in enumerate(leaderboard) if r[0] == st.session_state.user_name),
        "—"
    )

    # =====================================================
    # ANIMATED STATS
    # =====================================================
    st.subheader("Your Progress")

    c1, c2, c3, c4 = st.columns(4)

    with st.spinner("Updating your stats..."):
        time.sleep(0.6)

    c1.metric("🔥 Streak", f"{streak} days", delta="+1 today" if streak else None)
    time.sleep(0.2)

    c2.metric("🏆 Leaderboard Rank", f"#{leaderboard_rank}")
    time.sleep(0.2)

    c3.metric("🤝 Sessions", total_sessions)
    time.sleep(0.2)

    c4.metric("⭐ Avg Rating", avg_rating)

    # Progress animation
    st.progress(min(streak / 30, 1.0))

    st.divider()

    # =====================================================
    # HISTORY
    # =====================================================
    st.subheader("Session History")

    if rows:
        history = []
        for r in rows[-10:][::-1]:
            history.append({
                "Partner": r[0],
                "Rating": r[1],
                "Date": r[2]
            })
        st.table(history)
    else:
        st.info("No sessions yet. Start matchmaking!")
