import streamlit as st
from datetime import date

# ---- IMPORT PAGES ----
from materials import materials_page
from practice import practice_page
from admin import admin_page
from auth import auth_page
from dashboard import dashboard_page

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
# SESSION STATE INIT
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "user_name" not in st.session_state:
    st.session_state.user_name = ""

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "stage" not in st.session_state:
    st.session_state.stage = 1

if "profile" not in st.session_state:
    st.session_state.profile = {}

if "current_match" not in st.session_state:
    st.session_state.current_match = None

SUBJECTS = ["Mathematics", "English", "Science"]

# =========================================================
# AUTH GATE
# =========================================================
if not st.session_state.logged_in:
    auth_page()
    st.stop()


# =========================================================
# SIDEBAR (ONLY AFTER LOGIN)
# =========================================================
st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Matchmaking", "Learning Materials", "Practice", "Admin"],
    key="nav_radio"
)

st.sidebar.divider()

if st.sidebar.button("Logout", key="logout_btn"):
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.page = "Dashboard"
    st.session_state.stage = 1
    st.session_state.profile = {}
    st.session_state.current_match = None
    st.rerun()



# =========================================================
# DATABASE LOADERS
# =========================================================
def load_users():
    cursor.execute("""
        SELECT 
            a.name,
            p.role,
            p.grade,
            p.class,
            p.time,
            p.strong_subjects,
            p.weak_subjects,
            p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id = p.user_id
    """)
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
# DASHBOARD
# =========================
if page == "Dashboard":
    dashboard_page()

# =========================
# MATCHMAKING
# =========================
elif page == "Matchmaking":

    st.title("Sahay - Peer Learning Matchmaking System")
    mentors, mentees = load_users()

    # -------------------------
    # PROFILE CREATION
    # -------------------------
    if st.session_state.stage == 1:
        st.header("Create Your Profile")

        role = st.radio("Role", ["Student", "Teacher"])
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
                "role": role,
                "grade": grade,
                "class": int(grade.split()[-1]),
                "time": time_slot,
                "strong_subjects": strong,
                "weak_subjects": weak,
                "teaches": teaches
            }

            cursor.execute("""
                INSERT INTO profiles
                (user_id, role, grade, class, time, strong_subjects, weak_subjects, teaches)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state.user_id,
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
            st.session_state.stage = 2
            st.rerun()

    # -------------------------
    # MATCH RESULTS
    # -------------------------
    elif st.session_state.stage == 2:
        mentee = {
            "name": st.session_state.user_name,
            **st.session_state.profile
        }

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
    elif st.session_state.stage == 3:
        st.header("Learning Session")
        st.text_area("Chat")
        if st.button("End Session"):
            st.session_state.stage = 4
            st.rerun()

    # -------------------------
    # RATING + DATE (CRITICAL)
    # -------------------------
    elif st.session_state.stage == 4:
        st.header("Rate Session")
        rating = st.slider("Rating", 1, 5)

        if st.button("Submit Rating"):
            cursor.execute("""
                INSERT INTO ratings (mentor, mentee, rating, session_date)
                VALUES (?, ?, ?, ?)
            """, (
                st.session_state.current_match["mentor"],
                st.session_state.current_match["mentee"],
                rating,
                date.today()
            ))
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
    practice_page()

# =========================
# ADMIN
# =========================
elif page == "Admin":
    admin_key = st.sidebar.text_input("Admin Access Key", type="password")
    if admin_key != "ngo-admin-123":
        st.warning("Unauthorized access")
    else:
        admin_page()

# =========================================================
# LOGOUT BUTTON
# =========================================================
st.sidebar.divider()

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.page = "Dashboard"
    st.session_state.stage = 1
    st.session_state.profile = {}
    st.session_state.current_match = None
    st.rerun()

