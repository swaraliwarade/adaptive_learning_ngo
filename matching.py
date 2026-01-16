import streamlit as st
import time
import os
import json
from database import conn
from ai_helper import ask_ai

# Ensure upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# DATABASE & SYSTEM SYNC
# =========================================================
def sync_db_schema():
    cursor = conn.cursor()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            sender TEXT,
            message TEXT,
            file_path TEXT,
            created_ts INTEGER
        )
    """)
    # Table for storing session feedback
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            user_id INTEGER,
            rating INTEGER,
            feedback_ts INTEGER
        )
    """)
    conn.commit()

sync_db_schema()

# =========================================================
# UNIFIED EMERALD UI
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        .stApp { background-color: #f8fafc !important; }
        
        /* Unified Emerald Card Container */
        .emerald-card {
            background: white !important;
            padding: 30px !important;
            border-radius: 15px !important;
            border-top: 10px solid #10b981 !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important;
            margin-bottom: 25px;
        }

        /* Headings inside cards */
        .emerald-card h1, .emerald-card h2, .emerald-card h3 {
            color: #064e3b !important;
            margin-top: 0px !important;
            font-weight: 800 !important;
        }

        /* Ripple Buttons */
        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            padding: 12px !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            width: 100% !important;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #059669 !important;
            box-shadow: 0 5px 15px rgba(16, 185, 129, 0.3) !important;
        }

        /* Chat Scroll Area */
        .chat-scroll-area {
            background: #f9fafb !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px;
            padding: 15px;
            height: 400px;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        .bubble { padding: 12px; border-radius: 12px; margin-bottom: 10px; max-width: 80%; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 2px; }
        
        /* Rating Stars Emerald Color */
        .stFeedback svg { fill: #10b981 !important; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# CHAT FRAGMENT
# =========================================================
@st.fragment(run_every=2)
def render_live_chat():
    msgs = conn.execute(
        "SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
        (st.session_state.current_match_id,)
    ).fetchall()
    
    st.markdown('<div class="chat-scroll-area">', unsafe_allow_html=True)
    for sender, message, file_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cls = "bubble-me" if is_me else "bubble-peer"
        if message:
            st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{message}</div>', unsafe_allow_html=True)
        if file_path:
            st.caption(f"Resource Attached: {os.path.basename(file_path)}")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# APPLICATION STEPS
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Discovery")
    st.write("Find a compatible collaborator to start a learning session.")
    if st.button("Search Compatible Partner"):
        peer = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.user_id != ? LIMIT 1", (st.session_state.user_id,)).fetchone()
        if peer:
            st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
            st.session_state.current_match_id = f"session_{int(time.time())}"
            st.session_state.session_step = "live"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_live_session():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Active: {st.session_state.peer_info['name']}")
    render_live_chat()
    
    c1, c2 = st.columns([4, 1])
    with c1:
        txt = st.text_input("Message", placeholder="Share thoughts...", label_visibility="collapsed", key="msg")
    with c2:
        if st.button("Send"):
            if txt:
                conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                            (st.session_state.current_match_id, st.session_state.user_name, txt, int(time.time())))
                conn.commit()
                st.rerun()
    
    if st.button("End Collaboration"):
        st.session_state.session_step = "summary"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Session Analysis")
    
    # 1. AI Summary
    if "final_summary" not in st.session_state:
        with st.spinner("AI analyzing key takeaways..."):
            msgs = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
            chat_text = " ".join([m[0] for m in msgs if m[0]])
            st.session_state.final_summary = ask_ai(f"Summarize this study session: {chat_text}")
    
    st.info(st.session_state.final_summary)
    st.write("---")
    
    # 2. Rating System
    st.subheader("Rate Peer Proficiency")
    rating = st.feedback("stars", key="session_stars")
    if rating is not None:
        conn.execute("INSERT INTO session_ratings (match_id, user_id, rating, feedback_ts) VALUES (?,?,?,?)",
                    (st.session_state.current_match_id, st.session_state.user_id, rating + 1, int(time.time())))
        conn.commit()
        st.toast("Rating submitted successfully.")
    
    if st.button("Generate Assessment Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Assessment")
    
    if "quiz_data" not in st.session_state:
        with st.spinner("Creating custom quiz..."):
            msgs = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
            chat_text = " ".join([m[0] for m in msgs if m[0]])
            prompt = f"From this chat: {chat_text}. Create 1 hard MCQ. Return ONLY JSON: {{'q':'...','options':['...','...'],'correct':'...'}}"
            res = ask_ai(prompt)
            st.session_state.quiz_data = json.loads(res)

    q = st.session_state.quiz_data
    st.write(f"**Question:** {q['q']}")
    choice = st.radio("Choose the correct answer:", q['options'], label_visibility="collapsed")
    
    if st.button("Submit Assessment"):
        if choice == q['correct']:
            st.balloons()
            st.success("Correct! Exceptional retention.")
        else:
            st.error(f"Incorrect. The correct answer was: {q['correct']}")
    
    if st.button("Finish & Exit"):
        # Clear specific session states
        for key in ["final_summary", "quiz_data", "current_match_id", "peer_info"]:
            if key in st.session_state: del st.session_state[key]
        st.session_state.session_step = "discovery"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN ROUTER
# =========================================================
def matchmaking_page():
    inject_ui()
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
