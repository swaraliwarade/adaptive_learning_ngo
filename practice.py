import streamlit as st
import re
import time
import requests
from practice_data import PRACTICE_DATA
from database import cursor
from streak import init_streak, update_streak
from streamlit_lottie import st_lottie

# ---------------------------------------------------------
# ANIMATION & THEME HELPERS
# ---------------------------------------------------------
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def inject_emerald_practice_styles():
    st.markdown("""
        <style>
        .stApp { background-color: #f0fdf4; }
        
        .practice-card {
            background: white;
            padding: 25px;
            border-radius: 20px;
            border-top: 5px solid #10b981;
            box-shadow: 0 10px 25px rgba(5, 150, 105, 0.05);
            margin-bottom: 20px;
            color: #064e3b;
        }

        .main-header {
            color: #065f46;
            font-weight: 900;
            font-size: 2.5rem;
            letter-spacing: -0.5px;
        }

        /* Progress Bar Styling */
        .stProgress > div > div > div > div {
            background-color: #10b981;
        }

        /* Ripple-style Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 0.8rem 2rem !important;
            font-weight: 700 !important;
            width: 100%;
            transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1) !important;
            box-shadow: 0 6px 12px rgba(5, 150, 105, 0.15) !important;
        }

        div.stButton > button:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 20px rgba(5, 150, 105, 0.25) !important;
            filter: brightness(1.1);
        }

        div.stButton > button:active {
            transform: scale(0.97);
        }
        </style>
    """, unsafe_allow_html=True)

def get_normalized_class_level(user_id):
    cursor.execute("SELECT class_level, grade FROM profiles WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row: return None
    class_level_raw, grade_str = row
    if class_level_raw is not None and str(class_level_raw).isdigit():
        return int(class_level_raw)
    if grade_str:
        nums = re.findall(r'\d+', str(grade_str))
        if nums: return int(nums[0])
    return None

# ---------------------------------------------------------
# MAIN PAGE FUNCTION
# ---------------------------------------------------------
def practice_page():
    inject_emerald_practice_styles()
    init_streak()

    # Load Animations
    anim_book = load_lottieurl("https://assets3.lottiefiles.com/packages/lf20_1a8dx7zj.json")
    anim_success = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_7WUn4S.json")
    anim_warning = load_lottieurl("https://assets9.lottiefiles.com/private_files/lf30_rj76p65u.json")

    if not st.session_state.get("user_id"):
        if anim_warning: st_lottie(anim_warning, height=150)
        st.warning("Please log in to access practice.")
        return

    class_level = get_normalized_class_level(st.session_state.user_id)
    cursor.execute("SELECT role FROM profiles WHERE user_id = ?", (st.session_state.user_id,))
    role_row = cursor.fetchone()
    role = role_row[0] if role_row else "Student"

    if class_level is None and role == "Student":
        st.markdown("<div class='practice-card'>", unsafe_allow_html=True)
        if anim_warning: st_lottie(anim_warning, height=120)
        st.write("### Profile Incomplete")
        st.write("Please synchronize your Grade in the Dashboard.")
        if st.button("Go to Dashboard"):
            st.session_state.page = "Dashboard"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Header with Animation
    col_h1, col_h2 = st.columns([0.8, 0.2])
    with col_h1:
        st.markdown("<div class='main-header'>Practice Zone</div>", unsafe_allow_html=True)
        st.caption("Adaptive Learning Nodes | Curriculum Synchronization")
    with col_h2:
        if anim_book: st_lottie(anim_book, height=80)

    st.write("")

    # Selection Logic
    with st.container():
        if role == "Student":
            st.info(f"Node Status: Active for Grade {class_level}")
        else:
            available_classes = sorted(PRACTICE_DATA.keys())
            class_level = st.selectbox(
                "Simulate Grade Level", available_classes,
                index=available_classes.index(class_level) if class_level in available_classes else 0
            )

        if class_level not in PRACTICE_DATA:
            st.error(f"Data Missing for Grade {class_level}")
            return

        c1, c2 = st.columns(2)
        with c1:
            subject = st.selectbox("Subject Module", list(PRACTICE_DATA[class_level].keys()))
        with c2:
            topic = st.selectbox("Focus Topic", list(PRACTICE_DATA[class_level][subject].keys()))

    questions = PRACTICE_DATA[class_level][subject][topic]
    
    # Progress Tracker
    if "answers_given" not in st.session_state:
        st.session_state.answers_given = {}

    answered_count = len([k for k in st.session_state.answers_given.keys() if f"q_{class_level}_{subject}" in k])
    progress = min(answered_count / len(questions), 1.0)
    st.write(f"Completion: {int(progress*100)}%")
    st.progress(progress)

    st.divider()

    # Question Rendering
    user_answers = []
    for i, q in enumerate(questions):
        st.markdown(f"""
            <div class='practice-card'>
                <small style='color:#10b981; font-weight:bold;'>QUESTION {i+1} OF {len(questions)}</small>
                <p style='font-size: 1.15rem; font-weight: 600; margin-top:5px;'>{q['q']}</p>
            </div>
        """, unsafe_allow_html=True)
        
        q_key = f"q_{class_level}_{subject}_{topic}_{i}"
        ans = st.radio(
            f"Label_{i}", q["options"], 
            key=q_key, 
            label_visibility="collapsed",
            on_change=lambda: st.session_state.answers_given.update({q_key: True})
        )
        user_answers.append(ans)
        st.write("")

    # Submit with Results Animation
    if st.button("Submit & Finalize Session"):
        score = sum(1 for i, q in enumerate(questions) if user_answers[i] == q["answer"])
        
        st.markdown("---")
        if score == len(questions):
            if anim_success: st_lottie(anim_success, height=200)
            st.success(f"Perfect Synchronization: {score}/{len(questions)}")
            st.balloons()
        else:
            st.success(f"Session Complete: {score}/{len(questions)} Correct")

        update_streak()
        st.info("Emerald Streak Updated")

    if st.button("Return to Dashboard"):
        st.session_state.page = "Dashboard"
        st.rerun()
