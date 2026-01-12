# matching.py
import streamlit as st
from database import cursor

SUBJECTS = ["Mathematics", "English", "Science"]

# -------------------------------------------------
# LOAD ALL PROFILES FROM DB
# -------------------------------------------------
def load_profiles():
    cursor.execute("""
        SELECT 
            a.name,
            p.role,
            p.grade,
            p.time,
            p.strong_subjects,
            p.weak_subjects,
            p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id = p.user_id
    """)
    rows = cursor.fetchall()

    users = []
    for r in rows:
        users.append({
            "name": r[0],
            "role": r[1],                     # Student / Teacher
            "grade": r[2],                    # Grade 10
            "time": r[3],                     # 5-6 PM
            "strong": (
                r[6].split(",") if r[6] else  # teaches (for mentors)
                r[4].split(",") if r[4] else []
            ),
            "weak": r[5].split(",") if r[5] else []
        })

    return users


# -------------------------------------------------
# COMPATIBILITY SCORING
# -------------------------------------------------
def calculate_compatibility(mentor, mentee):
    score = 0
    reasons = []

    # 1️⃣ Weak ↔ Strong subject match (MOST IMPORTANT)
    for subject in mentee["weak"]:
        if subject in mentor["strong"]:
            score += 50
            reasons.append(f"Strong in {subject} ↔ Weak in {subject}")

    # 2️⃣ Same grade
    if mentor["grade"] == mentee["grade"]:
        score += 25
        reasons.append("Same grade")

    # 3️⃣ Same time slot
    if mentor["time"] == mentee["time"]:
        score += 15
        reasons.append("Same time slot")

    return score, reasons


# -------------------------------------------------
# FIND MATCHES FOR CURRENT USER
# -------------------------------------------------
def find_matches(current_user, all_users):
    matches = []

    for other in all_users:
        # Skip self
        if other["name"] == current_user["name"]:
            continue

        # Opposite roles only
        if other["role"] == current_user["role"]:
            continue

        # Assign mentor / mentee correctly
        mentor = other if other["role"] in ["Teacher"] else current_user
        mentee = current_user if current_user["role"] in ["Student"] else other

        score, reasons = calculate_compatibility(mentor, mentee)

        if score >= 40:  # minimum quality threshold
            matches.append({
                "mentor": mentor["name"],
                "mentee": mentee["name"],
                "score": score,
                "reasons": reasons
            })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


# -------------------------------------------------
# STREAMLIT PAGE
# -------------------------------------------------
def matchmaking_page():

    st.markdown("""
    <div class="card">
        <h2>Peer Learning Matchmaking</h2>
        <p>
            We match students and mentors based on complementary strengths,
            same grade, and available time slots.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # LOAD CURRENT USER PROFILE
    # -------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    if not profile:
        st.warning("Please complete your profile first.")
        return

    role, grade, time, strong, weak, teaches = profile

    current_user = {
        "name": st.session_state.user_name,
        "role": role,
        "grade": grade,
        "time": time,
        "strong": teaches.split(",") if teaches else strong.split(",") if strong else [],
        "weak": weak.split(",") if weak else []
    }

    # -------------------------------------------------
    # FIND MATCHES
    # -------------------------------------------------
    all_users = load_profiles()
    results = find_matches(current_user, all_users)

    # -------------------------------------------------
    # DISPLAY RESULTS
    # -------------------------------------------------
    if results:
        st.success(f"Found {len(results)} compatible match(es)")

        for r in results:
            st.markdown(f"""
            <div class="card">
                <h4>Compatibility Score: {r['score']}%</h4>
                <strong>Mentor:</strong> {r['mentor']}<br>
                <strong>Mentee:</strong> {r['mentee']}<br><br>
                <strong>Why this match?</strong>
                <ul>
                    {''.join(f"<li>{reason}</li>" for reason in r['reasons'])}
                </ul>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No compatible matches found yet.")
