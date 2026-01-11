import streamlit as st
import time

# ---- IMPORT PAGES ----
from materials import materials_page
from practice import practice_page
from ratings import show_rating_ui
from matching import find_matches


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
    page_title="Peer Learning Matchmaking System",
    layout="wide"
)

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Matchmaking", "Learning Materials", "Practice"]
)

# =========================================================
# SESSION STATE INIT
# =========================================================
if "stage" not in st.session_state:
    st.session_state.stage = 1

if "profile" not in st.session_state:
    st.session_state.profile = {}

if "user_profile" not in st.session_state:
    st.session_state.user_profile = {}

if "current_match" not in st.session_state:
    st.session_state.current_match = None

if "rating" not in st.session_state:
    st.session_state.rating = 0

SUBJECTS = ["Mathematics", "English", "Science"]

# =========================================================
# DATABASE LOADERS
# =========================================================
def load_users():
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()

    mentors, mentees = [], []

    for r in rows:
        user = {
            "name": r[0],
            "role": r[1],
            "grade": r[2],
            "class": r[3],
            "time": r[4],
            "strong_subjects": r[5].split(",") if r[5] else [],
            "weak_subjects": r[6].split(",") if r[6] else [],
            "teaches": r[7].split(",") if r[7] else []
        }

        if user["role"] == "Teacher" or user["strong_subjects"]:
            mentors.append(user)
        if user["weak_subjects"]:
            mentees.append(user)

    return mentors, mentees

# =========================================================
# MATCHING LOGIC
# =========================================================
def calculate_match_score(mentee, mentor):
    score = 0
    reasons = []

    for weak in mentee.get("weak_subjects", []):
        if weak in mentor.get("teaches", mentor.get("strong_subjects", [])):
            score += 50
            reasons.append(f"+50 {weak}")

    if mentor["time"] == mentee["time"]:
        score += 20
        reasons.append("+20 time match")

    if mentor["grade"] == mentee["grade"]:
        score += 10
        reasons.append("+10 same grade")

    return score, reasons

def find_best_mentor(mentee, mentors):
    best, best_score, best_reasons = None, -1, []

    for mentor in mentors:
        if mentor["name"] == mentee["name"]:
            continue
        score, reasons = calculate_match_score(mentee, mentor)
        if score > best_score:
            best, best_score, best_reasons = mentor, score, reasons

    return (best, best_score, best_reasons) if best_score >= 15 else (None, 0, [])

# =========================================================
# PAGE ROUTING
# =========================================================

# =========================
# MATCHMAKING
# =========================
if page == "Matchmaking":

    st.title("Peer Learning Matchmaking System")

    mentors, mentees = load_users()

    # -------------------------
    # PROFILE CREATION
    # -------------------------
    if st.session_state.stage == 1:
        st.header("Create Your Profile")

        role = st.radio("Role", ["Student", "Teacher"])
        name = st.text_input("Full Name")
        grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])
        time_slot = st.selectbox("Time Slot", ["4-5 PM", "5-6 PM", "6-7 PM"])

        strong, weak, teaches = [], [], []

        if role == "Student":
            strong = st.multiselect("Strong Subjects", SUBJECTS)
            weak = st.multiselect("Weak Subjects", SUBJECTS)
        else:
            teaches = st.multiselect("Subjects You Teach", SUBJECTS)

        if st.button("Submit Profile & Find Match", type="primary"):
            profile = {
                "name": name.strip(),
                "role": role,
                "grade": grade,
                "class": int(grade.split()[-1]),
                "time": time_slot,
                "strong_subjects": strong,
                "weak_subjects": weak,
                "teaches": teaches
            }

            cursor.execute("""
            INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile["name"],
                profile["role"],
                profile["grade"],
                profile["class"],
                profile["time"],
                ",".join(strong),
                ",".join(weak),
                ",".join(teaches)
            ))
            conn.commit()

            st.session_state.profile = profile
            st.session_state.user_profile = profile
            st.session_state.stage = 2
            st.rerun()

    # -------------------------
    # MATCH RESULTS
    # -------------------------
    if st.session_state.stage == 2:
        mentee = st.session_state.profile
        mentor, score, reasons = find_best_mentor(mentee, mentors)

        if mentor:
            st.success(f"Matched with {mentor['name']} (Score {score})")
            st.info(", ".join(reasons))

            st.session_state.current_match = {
                "mentor": mentor["name"],
                "mentee": mentee["name"]
            }

            if st.button("Start Session"):
                st.session_state.stage = 3
                st.rerun()
        else:
            st.warning("No suitable mentor found")

    # -------------------------
    # SESSION
    # -------------------------
    if st.session_state.stage == 3:
        st.header("Learning Session")
        st.text_area("Chat")
        if st.button("End Session"):
            st.session_state.stage = 4
            st.rerun()

    # -------------------------
    # RATING
    # -------------------------
    if st.session_state.stage == 4:
        st.header("Rate Session")
        rating = st.slider("Rating", 1, 5)

        if st.button("Submit Rating"):
            cursor.execute(
                "INSERT INTO ratings (mentor, rating) VALUES (?, ?)",
                (st.session_state.current_match["mentor"], rating)
            )
            conn.commit()
            st.success("Rating saved")
            st.session_state.stage = 1
            st.rerun()

# =========================
# LEARNING MATERIALS
# =========================
elif page == "Learning Materials":
    materials_page()

# =========================
# PRACTICE
# =========================
elif page == "Practice":
    if not st.session_state.user_profile:
        st.warning("Create a profile first.")
    else:
        practice_page()
