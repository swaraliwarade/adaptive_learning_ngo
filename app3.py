import time
import streamlit as st

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Peer Learning Matchmaking System",
    page_icon="🎓",
    layout="wide"
)

# =========================================================
# CUSTOM THEME + ANIMATIONS (SAFE CSS)
# =========================================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #e8f5ff, #e8fff3);
}

/* Headings */
h1, h2, h3 {
    color: #0b5394;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(90deg, #1abc9c, #3498db);
    color: white;
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

/* Card Layout */
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

/* Metric Cards */
[data-testid="stMetric"] {
    background: #f4fbff;
    padding: 12px;
    border-radius: 12px;
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
# HELPER FUNCTIONS (UNCHANGED)
# =========================================================
def show_rating_ui():
    st.session_state.rating = st.slider(
        "⭐ Rate your mentor",
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
    <h1>🎓 Peer Learning Matchmaking System</h1>
    <p>🤝 Connecting students to learn, grow, and succeed together</p>
</div>
""", unsafe_allow_html=True)

# =========================================================
# STAGE 1: PROFILE SETUP
# =========================================================
if st.session_state.stage == 1:
    st.markdown("""
    <div class="card">
        <h2>🧑‍🎓 Step 1: Create Your Profile</h2>
        <p>Tell us about your strengths and learning needs 📘</p>
    </div>
    """, unsafe_allow_html=True)

    role = st.radio("👤 Role", ["Student", "Teacher"])
    name = st.text_input("✍️ Full Name")

    grade = st.selectbox("🏫 Grade", [f"Grade {i}" for i in range(1, 11)])
    time_slot = st.selectbox("⏰ Time Slot", ["4-5 PM", "5-6 PM", "6-7 PM"])

    strong_subjects, weak_subjects, teaches = [], [], []

    if role == "Student":
        st.subheader("📚 Subjects")
        col1, col2 = st.columns(2)
        with col1:
            strong_subjects = st.multiselect("💪 Strong Subjects", SUBJECTS)
        with col2:
            weak_subjects = st.multiselect("🧩 Weak Subjects", SUBJECTS)
    else:
        teaches = st.multiselect("📘 Subjects You Teach", SUBJECTS)

    if role == "Student" and set(strong_subjects) & set(weak_subjects):
        st.warning("⚠️ A subject cannot be both strong and weak")

    if st.button("🚀 Submit Profile & Find Match", type="primary"):
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

# =========================================================
# STAGE 2: MATCH RESULTS
# =========================================================
if st.session_state.stage == 2:
    st.markdown("""
    <div class="card">
        <h2>🔍 Step 2: Match Results</h2>
        <p>Finding the best mentor for you 🧠</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Analyzing profiles..."):
        time.sleep(1)
        best_mentor, score, reasons = find_best_mentor(
            st.session_state.profile,
            st.session_state.mentors
        )

    if best_mentor:
        st.success(f"🎉 Match Found! Score: {score}")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("🧑‍🏫 Mentor", best_mentor["name"])
        with col2:
            st.metric("📊 Compatibility", score)

        st.info("📌 Reasons: " + ", ".join(reasons))

        if st.button("▶️ Start Learning Session", type="primary"):
            st.session_state.current_match = {
                "Mentor": best_mentor["name"],
                "Mentee": st.session_state.profile["name"],
                "Score": score,
                "Mentor_Role": best_mentor["role"]
            }
            st.session_state.stage = 3
            st.rerun()
    else:
        st.warning("No suitable match found")
        if st.button("🔙 Back"):
            st.session_state.stage = 1
            st.rerun()

# =========================================================
# STAGE 3: LEARNING SESSION
# =========================================================
if st.session_state.stage == 3:
    st.markdown("""
    <div class="card">
        <h2>🧑‍🏫 Learning Session</h2>
        <p>Ask questions, share resources, and learn together 🚀</p>
    </div>
    """, unsafe_allow_html=True)

    message = st.text_area("💬 Your Message")
    if st.button("📨 Send Message"):
        st.success("Message sent!")

    files = st.file_uploader("📎 Upload Resources", accept_multiple_files=True)
    if files:
        for f in files:
            st.success(f"Uploaded: {f.name}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🤖 AI Help"):
            st.info("Break problems into steps 🧩")
    with col2:
        if st.button("📊 Share Progress"):
            st.success("Progress shared 🎯")
    with col3:
        if st.button("❌ End Session"):
            st.session_state.stage = 4
            st.rerun()

# =========================================================
# STAGE 4: RATING
# =========================================================
if st.session_state.stage == 4:
    st.markdown("""
    <div class="card">
        <h2>⭐ Rate the Session</h2>
        <p>Your feedback improves learning quality 🌱</p>
    </div>
    """, unsafe_allow_html=True)

    show_rating_ui()

    if st.button("✅ Submit Rating"):
        mentor = st.session_state.current_match["Mentor"]
        st.session_state.leaderboard[mentor] = (
            st.session_state.leaderboard.get(mentor, 0) + st.session_state.rating * 20
        )
        st.success("Thank you for your feedback 🙌")

    st.subheader("🏆 Leaderboard")
    for i, (name, score) in enumerate(
        sorted(st.session_state.leaderboard.items(), key=lambda x: x[1], reverse=True), 1
    ):
        st.write(f"{i}. {name} — {score} pts")

    if st.button("🔁 New Session"):
        st.session_state.clear()
        st.rerun()
