import streamlit as st
import time
import os
import random
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

POLL_INTERVAL = 3

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def require_login():
    if not st.session_state.get("user_id"):
        st.stop()

def init_state():
    defaults = {
        "current_match_id": None,
        "confirmed": False,
        "session_ended": False,
        "chat_log": [],
        "last_msg_ts": 0,
        "last_poll": 0,
        "summary": None,
        "quiz": None,
        "rating_given": False,
        "ai_chat": [],
        "refresh_key": 0,
        "proposed_match": None,
        "proposed_score": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def should_poll():
    return now() - st.session_state.last_poll >= POLL_INTERVAL

def poll():
    st.session_state.last_poll = now()
    st.rerun()

def reset_matchmaking():
    conn.execute(
        "UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?",
        (st.session_state.user_id,)
    )
    conn.commit()

    for k in list(st.session_state.keys()):
        if k not in ["user_id", "user_name", "logged_in", "page"]:
            del st.session_state[k]

    st.rerun()

# =========================================================
# AI CHATBOT
# =========================================================
def ai_chat_ui():
    st.subheader("AI Assistant")
    q = st.text_input("Ask the assistant", key="ai_q")
    if st.button("Send to AI") and q:
        st.session_state.ai_chat.append((q, ask_ai(q)))

    for q, a in st.session_state.ai_chat[-5:]:
        st.markdown(f"**You:** {q}")
        st.markdown(f"**AI:** {a}")

# =========================================================
# MATCHING
# =========================================================
def load_waiting_profiles():
    rows = conn.execute("""
        SELECT a.id, a.name, p.grade, p.time,
               p.strong_subjects, p.weak_subjects
        FROM profiles p
        JOIN auth_users a ON a.id=p.user_id
        WHERE p.user_id!=?
          AND p.status='waiting'
          AND p.match_id IS NULL
    """, (st.session_state.user_id,)).fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r[0],
            "name": r[1],
            "grade": r[2],
            "time": r[3],
            "strong": (r[4] or "").split(","),
            "weak": (r[5] or "").split(","),
        })
    return users

def compatibility(a, b):
    s = 0
    s += len(set(a["weak"]) & set(b["strong"])) * 25
    s += len(set(b["weak"]) & set(a["strong"])) * 25
    if a["grade"] == b["grade"]:
        s += 10
    if a["time"] == b["time"]:
        s += 10
    s += random.randint(0, 5)
    return s

def find_best_match(current):
    best, best_score = None, -1
    for u in load_waiting_profiles():
        sc = compatibility(current, u)
        if sc > best_score:
            best, best_score = u, sc
    return best, best_score

# =========================================================
# CHAT
# =========================================================
def fetch_messages(match_id):
    rows = conn.execute("""
        SELECT sender, message, COALESCE(created_ts,0)
        FROM messages
        WHERE match_id=? AND COALESCE(created_ts,0) > ?
        ORDER BY created_ts
    """, (match_id, st.session_state.last_msg_ts)).fetchall()

    for s, m, ts in rows:
        st.session_state.chat_log.append((s, m))
        st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)

# =========================================================
# STAR RATING
# =========================================================
def star_rating():
    st.write("Rate your mentor")
    cols = st.columns(5)
    for i in range(5):
        if cols[i].button("★", key=f"star_{i}"):
            return i + 1
    return None

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    require_login()
    init_state()

    # ================= UI STYLE (ONLY SESSION BUTTONS EMERALD) =================
    st.markdown("""
    <style>
    /* MAIN CONTENT BUTTONS ONLY */
    .stApp > div:not(section[data-testid="stSidebar"]) .stButton > button {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, #0f766e, #14b8a6, #22c55e);
        color: white;
        border: none;
        border-radius: 999px;
        padding: 0.55rem 1.1rem;
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        transition: transform .2s ease, box-shadow .2s ease;
        box-shadow: 0 6px 18px rgba(20,184,166,.35);
    }

    .stApp > div:not(section[data-testid="stSidebar"]) .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 28px rgba(20,184,166,.45);
        background: linear-gradient(135deg, #0d9488, #10b981);
    }

    .stApp > div:not(section[data-testid="stSidebar"]) .stButton > button::after {
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        width: 8px;
        height: 8px;
        background: rgba(255,255,255,.5);
        border-radius: 50%;
        transform: translate(-50%,-50%) scale(0);
        opacity: 0;
    }

    .stApp > div:not(section[data-testid="stSidebar"]) .stButton > button:active::after {
        animation: ripple .6s ease-out;
    }

    @keyframes ripple {
        0% { transform: translate(-50%,-50%) scale(0); opacity:.6; }
        100% { transform: translate(-50%,-50%) scale(18); opacity:0; }
    }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    st.markdown("## Study Matchmaking")
    ai_chat_ui()
    st.divider()

    # 👉 ALL LOGIC BELOW IS UNCHANGED
    # Confirmation page, balloons, live chat,
    # file upload, summary, quiz, rating, back to matchmaking
