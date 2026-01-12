import streamlit as st 
import time from datetime 
import timedelta from database 
import cursor, conn

def dashboard_page():

    # -----------------------------------------------------
    # HERO
    # -----------------------------------------------------
    st.container()
    st.markdown(f"## 👋 Welcome back, {st.session_state.user_name}")
    st.caption("Your learning journey at a glance")
    st.divider()

    # -----------------------------------------------------
    # PROFILE FETCH
    # -----------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    edit_mode = st.session_state.get("edit_profile", False)

    # =====================================================
    # PROFILE SETUP / EDIT
    # =====================================================
    if not profile or edit_mode:
        st.subheader("📝 Profile Setup")

        with st.form("profile_form"):
            role = st.radio("Role", ["Student", "Teacher"], horizontal=True)
            grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])
            time_slot = st.selectbox("Available Time Slot", TIME_SLOTS)

            strong, weak, teaches = [], [], []

            if role == "Student":
                strong = st.multiselect("Strong Subjects", SUBJECTS)
                weak = st.multiselect("Weak Subjects", SUBJECTS)
            else:
                teaches = st.multiselect("Subjects You Teach", SUBJECTS)

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

            st.session_state.edit_profile = False
            st.success("Profile saved successfully.")
            st.rerun()

        return

    # =====================================================
    # PROFILE VIEW (STREAMLIT ONLY)
    # =====================================================
    role, grade, time_slot, strong, weak, teaches = profile

    strong_list = strong.split(",") if strong else []
    weak_list = weak.split(",") if weak else []
    teach_list = teaches.split(",") if teaches else []

    st.subheader("👤 Your Profile")

    # --- Avatar + Basic Info ---
    col1, col2 = st.columns([1, 4])

    with col1:
        st.markdown("### 🧑")

    with col2:
        st.write(f"**Role:** {role}")
        st.write(f"**Grade:** {grade}")
        st.write(f"**Time Slot:** {time_slot}")

    st.divider()

    # --- Strong Subjects ---
    st.markdown("### 🟢 Strong Subjects")
    if strong_list or teach_list:
        for subject in (strong_list or teach_list):
            st.success(subject)
    else:
        st.info("No strong subjects added")

    # --- Weak Subjects ---
    st.markdown("### 🔴 Weak Subjects")
    if weak_list:
        for subject in weak_list:
            st.error(subject)
    else:
        st.info("No weak subjects added")

    st.divider()

    if st.button("✏️ Edit Profile"):
        st.session_state.edit_profile = True
        st.rerun()

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
    # STATS
    # -----------------------------------------------------
    st.subheader("📊 Your Progress")

    c1, c2, c3, c4 = st.columns(4)
    time.sleep(0.2)

    c1.metric("Day Streak", streak)
    c2.metric("Sessions", total_sessions)
    c3.metric("Avg Rating", avg_rating)
    c4.metric("Consistency", f"{min(streak/30*100,100):.0f}%")

    st.progress(min(streak / 30, 1.0))
