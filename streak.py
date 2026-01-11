import streamlit as st
from datetime import date

# ---------- INIT STREAK STATE ----------
def init_streak():
    if "current_streak" not in st.session_state:
        st.session_state.current_streak = 0

    if "last_activity_date" not in st.session_state:
        st.session_state.last_activity_date = None


# ---------- UPDATE STREAK (CALL FROM ANY MODULE) ----------
def update_streak(source="unknown"):
    """
    Increments streak ONLY ONCE per day,
    no matter how many actions are done.
    """
    init_streak()
    today = date.today()

    if st.session_state.last_activity_date != today:
        st.session_state.current_streak += 1
        st.session_state.last_activity_date = today

        # Optional: log last source (for display/debug)
        st.session_state.last_streak_source = source


# ---------- GETTERS ----------
def get_streak():
    init_streak()
    return st.session_state.current_streak


def get_last_source():
    return st.session_state.get("last_streak_source", "—")
