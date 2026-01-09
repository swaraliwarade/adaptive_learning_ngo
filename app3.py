import streamlit as st
from ratings import show_rating_ui
from matching import find_matches
import time

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Peer Learning Matchmaking System",
    layout="wide"
)

# =========================================================
# CUSTOM THEME + ANIMATIONS
# =========================================================
st.markdown("""
<style>
/* =========================
   GLOBAL BACKGROUND
========================= */
.stApp {
    background: linear-gradient(135deg, #e8f5ff, #e8fff3);
}

/* =========================
   TITLES / HEADINGS
   - Black
   - Bold
   - New font
========================= */
h1, h2, h3 {
    color: black !important;
    font-weight: 700 !important;
    font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}

/* =========================
   NORMAL TEXT
========================= */
p, span, div, label {
    color: white;
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
}

/* =========================
   DROPDOWNS (SELECTBOX + MULTISELECT)
   - Selected value
   - Placeholder
   - Dropdown options
========================= */

/* Selected value */
div[data-baseweb="select"] span {
    color: white !important;
    font-weight: 500;
}

/* Dropdown menu background */
div[data-baseweb="menu"] {
    background-color: #1f2933 !important;
}

/* Dropdown options text */
div[data-baseweb="option"] {
    color: white !important;
    font-weight: 500;
}

/* Hovered option */
div[data-baseweb="option"]:hover {
    background-color: #2563eb !important;
    color: white !important;
}

/* =========================
   INPUT BOX TEXT (optional polish)
========================= */
input {
    color: white !important;
}

/* =========================
   BUTTONS
========================= */
.stButton>button {
    background: linear-gradient(90deg, #1abc9c, #3498db);
    color: white !important;
    border-radius: 10px;
    padding: 0.6em 1.2em;
    border: none;
    font-weight: 600;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stButton>button:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 18px rgba(0,0,0,0.15);
}

/* =========================
   CARD LAYOUT
========================= */
.card {
    background: white;
    padding: 22px;
    border-radius: 16px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    margin-bottom: 20px;
    animation: fadeIn 0.6s ease-in-out;
}

/* Fade animation */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# SESSION STATE INITIALIZATION
# =========================================================
if "stage" not in st.session_state:
    st.session_state.stage = 1

if "profile" not in st.session_state:
    st.session_state.profile = {}

if "mentors" not in st.session_state:
    st.session_state.mentors = []

if "mentees" not in st.session_state:
    st.session_state.mentees = []

if "leaderboard" not in st.session_state:
    st.session_state.leaderboard = {}

if "current_match" not in st.session_state:
    st.session_state.current_match = None

if "rating" not in st.session_state:
    st.session_state.rating = 0

SUBJECTS = ["Mathematics", "English", "Science"]

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def show_rating_ui():
    st.session_state.rating = st.slider(
        "Rate your mentor",
        min_value=0,
        max_value=5,
        value=0,
        step=1
    )

def calculate_match_score(mentee, mentor):
    score = 0
    reasons = []

    mentee_weak = mentee.get("weak_subjects", [])
    mentee_strong = mentee.get("strong_subjects", [])
    mentor_strong = mentor.get("strong_subjects", mentor.get("teaches", []))

    for weak in mentee_weak:
        if weak in mentor_strong:
            score += 50
            reasons.append(f"+50 {weak} help")

    if mentor["time"] == mentee["time"]:
        score += 20
        reasons.append("+20 same time")

    if mentor["grade"] == mentee["grade"]:
        score += 10
        reasons.append("+10 same grade")

    for strong in mentee_strong:
        if strong in mentor_strong:
            score += 5
            reasons.append(f"+5 {strong} practice")

    return score, reasons

def find_best_mentor(mentee, mentors):
    eligible = [m for m in mentors if m["name"] != mentee["name"]]
    best, best_score, best_reasons = None, -1, []

    for mentor in eligible:
        score, reasons = calculate_match_score(mentee, mentor)
        if score > best_score:
            best, best_score, best_reasons = mentor, score, reasons

    return best, best_score, best_reasons if best_score >= 15 else (None, 0, [])

# =========================================================
# APP TITLE
# =========================================================
st.markdown("""
<div class="card">
    <h1>Peer Learning Matchmaking System</h1>
    <p>Connecting students to learn, grow, and succeed together</p>
</div>
""", unsafe_allow_html=True)

# =========================================================
# STAGE 1: PROFILE SETUP
# =========================================================
if st.session_state.stage == 1:
    st.markdown("""
    <div class="card">
        <h2>Step 1: Create Your Profile</h2>
        <p>Tell us about your strengths and learning needs</p>
    </div>
    """, unsafe_allow_html=True)

    role = st.radio("Role", ["Student", "Teacher"])
    name = st.text_input("Full Name")

    grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])
    time_slot = st.selectbox("Time Slot", ["4-5 PM", "5-6 PM", "6-7 PM"])

    strong_subjects, weak_subjects, teaches = [], [], []

    if role == "Student":
        st.subheader("Subjects")
        col1, col2 = st.columns(2)
        with col1:
            strong_subjects = st.multiselect("Strong Subjects", SUBJECTS)
        with col2:
            weak_subjects = st.multiselect("Weak Subjects", SUBJECTS)
    else:
        teaches = st.multiselect("Subjects You Teach", SUBJECTS)

    if role == "Student" and set(strong_subjects) & set(weak_subjects):
        st.warning("A subject cannot be both strong and weak")

    if st.button("Submit Profile & Find Match", type="primary"):
        if not name.strip():
            st.error("Please enter your name")
        else:
            profile = {
                "role": role,
                "name": name.strip(),
                "grade": grade,
                "time": time_slot,
            }

            if role == "Student":
                profile["strong_subjects"] = strong_subjects
                profile["weak_subjects"] = weak_subjects
                if strong_subjects:
                    st.session_state.mentors.append(profile)
                if weak_subjects:
                    st.session_state.mentees.append(profile)
            else:
                profile["teaches"] = teaches
                st.session_state.mentors.append(profile)

            st.session_state.profile = profile
            st.session_state.stage = 2
            st.rerun()
