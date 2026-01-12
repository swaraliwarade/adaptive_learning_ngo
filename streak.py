import streamlit as st
from datetime import date

# ---------- CONFIG ----------
STREAK_LEVELS = [
    (1, "Beginner 🌱"),
    (3, "Consistent Learner 🌿"),
    (6, "Study Champ 🌳"),
    (11, "Knowledge Warrior 🌲"),
    (21, "Legend 🏆")
]

UNLOCKS = {
    3: "📘 Quote unlocked: 'Small steps every day.'",
    7: "🎉 Achievement: 7-Day Learning Streak!",
    14: "🔥 Quote unlocked: 'Consistency beats talent.'",
    21: "🏆 LEGEND STATUS UNLOCKED"
}

EMOTIONAL_MESSAGES = {
    0: "Your learning journey is waiting 🌱",
    1: "Great start! Keep watering your plant 💧",
    3: "Most people quit here. You didn’t 🔥",
    5: "Your plant is growing strong 🌿",
    7: "ONE WEEK STRONG 💪",
    14: "Your discipline is inspiring 🌳",
}

# ---------- INIT ----------
def init_streak():
    if "streak" not in st.session_state:
        st.session_state.streak = 0
    if "last_active" not in st.session_state:
        st.session_state.last_active = None
    if "unlocks_seen" not in st.session_state:
        st.session_state.unlocks_seen = set()

# ---------- UPDATE ----------
def update_streak():
    today = date.today()

    if st.session_state.last_active != today:
        if st.session_state.last_active is None:
            st.session_state.streak = 1
        else:
            delta = (today - st.session_state.last_active).days
            if delta == 1:
                st.session_state.streak += 1
            else:
                st.session_state.streak = 1

        st.session_state.last_active = today
        return True  # streak updated today
    return False  # already counted today

# ---------- UI ----------
def get_streak_level(streak):
    level = "Beginner 🌱"
    for days, name in STREAK_LEVELS:
        if streak >= days:
            level = name
    return level

def get_message(streak):
    keys = sorted(EMOTIONAL_MESSAGES.keys())
    msg = EMOTIONAL_MESSAGES[keys[0]]
    for k in keys:
        if streak >= k:
            msg = EMOTIONAL_MESSAGES[k]
    return msg

def render_streak_ui():
    streak = st.session_state.streak

    st.subheader("🌱 Your Learning Plant")
    st.markdown(f"### 🔥 {streak}-Day Streak")
    st.markdown(f"**🏅 Level:** {get_streak_level(streak)}")
    st.info(get_message(streak))

    # Progress bar (weekly)
    progress = min(streak % 7 or 7, 7)
    st.progress(progress / 7)
    st.caption(f"Weekly Progress: {progress}/7 days")

    # Unlocks
    if streak in UNLOCKS and streak not in st.session_state.unlocks_seen:
        st.success(UNLOCKS[streak])
        st.session_state.unlocks_seen.add(streak)
