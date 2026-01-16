import streamlit as st
import requests
from datetime import date
from database import cursor, conn
from streamlit_lottie import st_lottie

# -----------------------------------------------------
# ANIMATION & THEME HELPERS
# -----------------------------------------------------
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def inject_emerald_streak_styles():
    st.markdown("""
        <style>
        .streak-container {
            background: white;
            padding: 25px;
            border-radius: 20px;
            border: 1px solid #d1fae5;
            box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.05);
            text-align: center;
        }
        .streak-number {
            font-size: 3rem;
            font-weight: 900;
            color: #059669;
            line-height: 1;
            margin: 10px 0;
        }
        .streak-label {
            color: #064e3b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.8rem;
        }
        .stProgress > div > div > div > div {
            background-image: linear-gradient(to right, #34d399, #10b981);
        }
        </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------
# CORE LOGIC
# -----------------------------------------------------
def init_streak():
    if "streak" not in st.session_state:
        st.session_state.streak = 0
    if "last_active" not in st.session_state:
        st.session_state.last_active = None

    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    cursor.execute(
        "SELECT streak, last_active FROM user_streaks WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()

    if row:
        st.session_state.streak = row[0]
        st.session_state.last_active = (
            date.fromisoformat(row[1]) if row[1] else None
        )
    else:
        cursor.execute(
            "INSERT INTO user_streaks (user_id, streak, last_active) VALUES (?, 0, NULL)",
            (user_id,)
        )
        conn.commit()

def update_streak():
    init_streak()
    today = date.today()
    last = st.session_state.last_active

    if last != today:
        if last is None:
            st.session_state.streak = 1
        else:
            delta = (today - last).days
            st.session_state.streak = (
                st.session_state.streak + 1 if delta == 1 else 1
            )

        st.session_state.last_active = today
        cursor.execute("""
            UPDATE user_streaks SET streak=?, last_active=? WHERE user_id=?
        """, (st.session_state.streak, today.isoformat(), st.session_state.user_id))
        conn.commit()
        return True
    return False

# -----------------------------------------------------
# UI RENDERING (ANIMATED)
# -----------------------------------------------------
STREAK_LEVELS = [
    (0, "Initiating Growth", "https://assets3.lottiefiles.com/packages/lf20_7msh8sn0.json"), # Sprout
    (3, "Vibrant Learner", "https://assets1.lottiefiles.com/private_files/lf30_8ez6ny.json"), # Growing Plant
    (7, "Study Master", "https://assets1.lottiefiles.com/packages/lf20_08m9ayre.json"), # Big Tree
    (14, "Emerald Legend", "https://assets10.lottiefiles.com/packages/lf20_touohxv0.json") # Trophy/Success
]

def render_streak_ui():
    init_streak()
    inject_emerald_streak_styles()
    
    streak = st.session_state.streak
    
    # Select appropriate animation based on streak level
    current_level_name = "Beginner"
    active_anim_url = STREAK_LEVELS[0][2]
    
    for days, name, url in STREAK_LEVELS:
        if streak >= days:
            current_level_name = name
            active_anim_url = url

    anim_data = load_lottieurl(active_anim_url)

    st.markdown("<div class='streak-container'>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([0.4, 0.6])
    
    with col1:
        if anim_data:
            st_lottie(anim_data, height=180, key="streak_anim_main")
            
    with col2:
        st.markdown(f"<div class='streak-label'>Current Momentum</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='streak-number'>{streak}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color: #10b981; font-weight: 700;'>{current_level_name}</div>", unsafe_allow_html=True)
        
        st.write("")
        # Weekly progress calculation
        progress_val = (streak % 7) / 7.0 if (streak % 7 != 0) else 1.0
        st.progress(progress_val)
        st.caption(f"Syncing Node Progress: {int(progress_val*100)}%")

    st.markdown("</div>", unsafe_allow_html=True)

    # Emotional motivation message (No emojis)
    if streak == 0:
        st.info("The best time to start was yesterday. The second best time is now.")
    elif streak < 3:
        st.success("Foundation established. Keep the momentum going.")
    else:
        st.success("Maximum consistency detected. Your learning node is thriving.")
