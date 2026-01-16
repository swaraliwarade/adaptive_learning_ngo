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
# DATABASE SCHEMA AUTO-FIX
# =========================================================
def sync_db_schema():
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(profiles)")
    p_cols = [c[1] for c in cursor.fetchall()]
    p_updates = {
        "status": "TEXT DEFAULT 'waiting'",
        "match_id": "TEXT",
        "interests": "TEXT DEFAULT 'General Study'",
        "bio": "TEXT DEFAULT 'Ready to learn!'"
    }
    for col, definition in p_updates.items():
        if col not in p_cols:
            conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} {definition}")
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            sender TEXT,
            message TEXT,
            created_ts INTEGER
        )
    """)
    
    cursor.execute("PRAGMA table_info(messages)")
    m_cols = [c[1] for c in cursor.fetchall()]
    if "file_path" not in m_cols:
        conn.execute("ALTER TABLE messages ADD COLUMN file_path TEXT")
        
    conn.commit()

sync_db_schema()

# =========================================================
# EMERALD THEME + RIPPLE ANIMATION CSS
# =========================================================
st.markdown("""
    <style>
    /* Force Background */
    .stApp { background-color: #f9fafb !important; }

    /* ALL BUTTONS: Emerald + Ripple Effect */
    button, 
    .stButton > button, 
    .stDownloadButton > button,
    button[kind="primary"],
    button[kind="secondary"] {
        background-color: #10b981 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 700 !important;
        width: 100% !important;
        position: relative !important;
        overflow: hidden !important;
        transition: background 0.4s !important;
        background-position: center !important;
    }

    /* Ripple Animation on Click/Hover */
    button:hover, .stButton > button:hover {
        background: #059669 radial-gradient(circle, transparent 1%, #059669 1%) center/15000% !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4) !important;
    }

    button:active, .stButton > button:active {
        background-color: #34d399 !important;
        background-size: 100% !important;
        transition: background 0s !important;
    }

    /* Emerald Cards */
    .emerald-card {
        background: #ffffff !important;
        padding: 25px !important;
        border-radius: 12px !important;
        border-left: 6px solid #10b981 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        margin-bottom: 20px;
    }

    /* Chat Bubbles */
    .chat-container {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 12px !important;
        padding: 15px;
        height: 400px;
        overflow-y: auto;
    }

    .msg-me { background: #10b981 !important; color: white !important; padding: 10px; border-radius: 10px; margin-bottom: 8px; margin-left: 20%; text-align: right; }
    .msg-peer { background: #f3f4f6 !important; color: #111827 !important; padding: 10px; border-radius: 10px; margin-bottom: 8px; margin-right: 20%; border: 1px solid #e5e7eb; }

    /* Hide Decorations */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# =========================================================
# STATE & HELPERS
# =========================================================
def ensure_state():
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

def reset_matchmaking():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    st.session_state.session_step = "discovery"
    st.rerun()

# =========================================================
# UI PAGES
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Peer Matchmaking")
    st.write("Find a compatible study partner using our AI matching system.")
    if st.button("Search Compatible Partner"):
        peer = conn.execute("""
            SELECT p.user_id, a.name, p.bio, p.interests 
            FROM profiles p JOIN auth_users a ON a.id=p.user_id 
            WHERE p.status='waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()
        
        if peer:
            st.session_state.peer_info = {"id": peer[0], "name": peer[1], "bio": peer[2], "ints": peer[3]}
            st.session_state.current_match_id = f"sess_{int(time.time())}"
            st.session_state.session_step = "confirmation"
            st.rerun()
        else:
            st.info("System: Currently scanning for available peers. You have been added to the queue.")
            conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    p = st.session_state.peer_info
    st.subheader(f"Matching Profile Found: {p['name']}")
    st.write(f"Learning Focus: {p['ints']}")
    st.write(f"Background: {p['bio']}")
    st.divider()
    
    if st.button("Establish Live Session"):
        st.balloons()
        time.sleep(1)
        st.session_state.session_step = "live"
        st.rerun()
    if st.button("Reject and Re-scan"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def live_chat_fragment():
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                         (st.session_state.current_match_id,)).fetchall()
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for sender, message, file_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cl = "msg-me" if is_me else "msg-peer"
        
        if message:
            st.markdown(f'<div class="{cl}"><b>{sender}</b><br>{message}</div>', unsafe_allow_html=True)
        if file_path:
            fname = os.path.basename(file_path)
            st.markdown(f'<div class="{cl}">[Attached File: {fname}]</div>', unsafe_allow_html=True)
            with open(file_path, "rb") as f:
                st.download_button(f"Open {fname}", f, file_name=fname, key=f"f_{time.time()}")
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.subheader(f"Collaboration with {st.session_state.peer_info['name']}")
    live_chat_fragment()

    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            txt = st.text_input("Note", placeholder="Type here...", label_visibility="collapsed", key="chat_in")
        with c2:
            file = st.file_uploader("Document", label_visibility="collapsed", key="f_up")
        with c3:
            if st.button("Submit"):
                path = None
                if file:
                    path = os.path.join(UPLOAD_DIR, file.name)
                    with open(path, "wb") as f: f.write(file.getbuffer())
                if txt or file:
                    conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, txt, path, int(time.time())))
                    conn.commit()
                    st.rerun()
    
    if st.button("Terminate Session"):
        st.session_state.session_step = "summary"
        st.rerun()

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Session Report")
    st.write("System: Analyzing collaboration data...")
    if st.button("Initiate Assessment Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    if st.button("Return to Dashboard"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Assessment")
    if st.button("Complete Final Step"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def matchmaking_page():
    ensure_state()
    with st.sidebar:
        st.title("AI Consultant")
        q = st.text_area("Request AI Support")
        if st.button("Process Command"):
            st.write(ask_ai(q))

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
