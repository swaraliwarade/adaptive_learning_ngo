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
    cols = [c[1] for c in cursor.fetchall()]
    updates = {
        "status": "TEXT DEFAULT 'waiting'",
        "match_id": "TEXT",
        "interests": "TEXT DEFAULT 'General Study'",
        "bio": "TEXT DEFAULT 'Ready to learn!'"
    }
    for col, definition in updates.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} {definition}")
    
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
    conn.commit()

sync_db_schema()

# =========================================================
# THE "TOTAL EMERALD" CSS OVERRIDE
# =========================================================
st.markdown("""
    <style>
    /* 1. Global Emerald Overrides for ALL Streamlit Buttons */
    button, 
    .stButton > button, 
    button[kind="primary"], 
    button[kind="secondary"],
    .stDownloadButton > button {
        background-color: #10b981 !important;
        color: white !important;
        border: 2px solid #059669 !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

    button:hover, .stButton > button:hover {
        background-color: #059669 !important;
        border-color: #047857 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
    }

    /* 2. Fix the Sidebar specifically */
    section[data-testid="stSidebar"] button {
        background-color: #10b981 !important;
    }

    /* 3. Emerald Borders and Highlights */
    .emerald-card {
        background: white !important;
        padding: 25px !important;
        border-radius: 12px !important;
        border-top: 8px solid #10b981 !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1) !important;
        margin-bottom: 25px;
    }

    /* 4. Chat Styling */
    .chat-container {
        background: #f8fafc !important;
        border: 2px solid #e2e8f0 !important;
        border-radius: 16px !important;
        padding: 20px;
        height: 450px;
        overflow-y: auto;
    }

    .bubble-me {
        background-color: #10b981 !important;
        color: white !important;
        padding: 12px;
        border-radius: 15px 15px 0 15px;
        margin-left: auto;
        margin-bottom: 10px;
        max-width: 80%;
        text-align: right;
    }

    .bubble-peer {
        background-color: white !important;
        color: #1e293b !important;
        padding: 12px;
        border-radius: 15px 15px 15px 0;
        margin-right: auto;
        margin-bottom: 10px;
        max-width: 80%;
        border: 1px solid #e2e8f0 !important;
    }

    /* 5. Progress/Status bars */
    .stProgress > div > div > div > div {
        background-color: #10b981 !important;
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# CORE LOGIC
# =========================================================
def ensure_state():
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"
    if "ai_history" not in st.session_state: st.session_state.ai_history = []

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
    st.title("Partner Search")
    st.write("Initiate a real-time connection with a compatible study mentor or peer.")
    
    if st.button("Search Compatible Partner"):
        peer = conn.execute("""
            SELECT p.user_id, a.name, p.bio, p.interests 
            FROM profiles p JOIN auth_users a ON a.id=p.user_id 
            WHERE p.status='waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()
        
        if peer:
            st.session_state.peer_info = {"id": peer[0], "name": peer[1], "bio": peer[2], "ints": peer[3]}
            st.session_state.current_match_id = f"session_{int(time.time())}"
            st.session_state.session_step = "confirmation"
            st.rerun()
        else:
            st.info("System: Matching queue active. Waiting for peers to join.")
            conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    p = st.session_state.peer_info
    st.subheader(f"Matching Profile: {p['name']}")
    st.write(f"Background: {p['bio']}")
    st.write(f"Focus Areas: {p['ints']}")
    st.write("---")
    
    col1, col2 = st.columns(2)
    if col1.button("Confirm Connection"):
        st.balloons()
        time.sleep(1)
        st.session_state.session_step = "live"
        st.rerun()
    if col2.button("Request New Match"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def live_chat_fragment():
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                         (st.session_state.current_match_id,)).fetchall()
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for sender, message, file_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cl = "bubble-me" if is_me else "bubble-peer"
        
        if message:
            st.markdown(f'<div class="{cl}"><b>{sender}</b><br>{message}</div>', unsafe_allow_html=True)
        if file_path:
            file_name = os.path.basename(file_path)
            st.markdown(f'<div class="{cl}">System: File shared ({file_name})</div>', unsafe_allow_html=True)
            with open(file_path, "rb") as f:
                st.download_button(label=f"Open {file_name}", data=f, file_name=file_name, key=f"dl_{file_name}_{time.time()}")
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.markdown(f"### Live Session: {st.session_state.peer_info['name']}")
    
    live_chat_fragment()

    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            txt = st.text_input("Message", placeholder="Input study notes...", label_visibility="collapsed", key="chat_in")
        with c2:
            file = st.file_uploader("Document", label_visibility="collapsed", key="file_up")
        with c3:
            if st.button("Submit"):
                path = None
                if file:
                    path = os.path.join(UPLOAD_DIR, file.name)
                    with open(path, "wb") as f:
                        f.write(file.getbuffer())
                
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
    st.title("Session Analysis")
    if not st.session_state.get("summary"):
        history = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
        st.session_state.summary = ask_ai(f"Provide a summary of these learning notes: {' '.join([m[0] for m in history if m[0]])}")
    
    st.write(st.session_state.summary)
    st.write("---")
    st.write("Rate Partner Proficiency:")
    st.feedback("stars")
    
    if st.button("Generate Assessment Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    if st.button("Return to Dashboard"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Assessment")
    # Quiz Logic...
    if st.button("Finalize Quiz"): 
        reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def matchmaking_page():
    ensure_state()
    with st.sidebar:
        st.title("AI Systems")
        q = st.text_area("Request AI Consultation")
        if st.button("Process Query"):
            st.write(ask_ai(q))

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
