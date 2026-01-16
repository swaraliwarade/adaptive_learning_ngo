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
        /* Container with improved visibility and contrast */
        .streak-container {
            background: #ffffff;
            padding: 30px;
            border-radius: 24px;
            border: 2px solid #ecfdf5;
            box-shadow: 0 20px 25px -5px rgba(16, 185, 129, 0.1), 0 10px 10px -5px rgba(16, 185, 129, 0.04);
            text-align: center;
            margin-bottom: 20px;
        }
        
        /* Large, highly visible streak number */
        .streak-number {
            font-size: 4.5rem;
            font-weight: 900;
            color: #047857; /* Deep Emerald for visibility */
            line-height: 1;
            margin: 5px 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.05);
        }
        
        /* Label styling with better letter spacing */
        .streak-label {
            color: #064e3b;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 0.9rem;
            margin-bottom: 0px;
        }

        /* Level Name text */
        .level-name {
            color: #10b981;
            font-weight: 700;
            font-size: 1.2rem;
            margin-bottom: 15px;
        }
        
        /* Customizing the Progress Bar color to Emerald Gradient */
        .stProgress > div > div > div > div {
            background-image: linear-gradient(to right, #6ee7b7, #10b981) !important;
        }

        /* Caption visibility fix */
        .streak-caption {
            color: #374151;
            font-weight: 500;
            font-size: 0.85rem;
            margin-top: 5px;
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
# UI RENDERING (ENHANCED ANIMATED)
# -----------------------------------------------------
STREAK_LEVELS = [
    (0, "Initiating Growth", "https://assets3.lottiefiles.com/packages/lf20_7msh8sn0.json"), 
    (3, "Vibrant Learner", "https://assets1.lottiefiles.com/private_files/lf30_8ez6ny.json"), 
    (7, "Study Master", "https://assets1.lottiefiles.com/packages/lf20_08m9ayre.json"), 
    (14, "Emerald Legend", "https://lottie.host/81a9673d-907a-426c-850d-851f5056804d/5vK5oXpL5I.json") 
]

def render_streak_ui():
    init_streak()
    inject_emerald_streak_styles()
    
    streak = st.session_state.streak
    
    # Logic to select level and animation
    current_level_name = "Seedling"
    active_anim_url = STREAK_LEVELS[0][2]
    
    for days, name, url in STREAK_LEVELS:
        if streak >= days:
            current_level_name = name
            active_anim_url = url

    anim_data = load_lottieurl(active_anim_url)

    # Container Start
    st.markdown("<div class='streak-container'>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([0.45, 0.55])
    
    with col1:
        if anim_data:
            st_lottie(anim_data, height=220, key="streak_anim_enhanced", speed=1)
            
    with col2:
        st.markdown(f"<div class='streak-label'>Current Momentum</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='streak-number'>{streak}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='level-name'>{current_level_name}</div>", unsafe_allow_html=True)
        
        # Weekly progress calculation logic
        # If streak is 0, progress 0. If streak > 0, show remainder of week
        weekly_step = streak % 7
        if streak > 0 and weekly_step == 0:
            progress_val = 1.0
        else:
            progress_val = weekly_step / 7.0
            
        st.progress(max(progress_val, 0.05)) # Small bar even at 0 for visual interest
        st.markdown(f"<div class='streak-caption'>Syncing Node Progress: {int(progress_val*100)}%</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Status Notification Styling
    if streak == 0:
        st.info("Your learning sequence is ready to begin. Complete a session to activate growth.")
    elif streak < 3:
        st.success("Consistency bridge established. Maintain activity to evolve your node.")
    else:
        st.success("High-frequency learning detected. Your Emerald status is currently peak.")
