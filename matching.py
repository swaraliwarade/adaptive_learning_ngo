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
# DATABASE SYNC (REPAIRED)
# =========================================================
def sync_db_schema():
    cursor = conn.cursor()
    # Ensure all tables exist with correct columns
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
# UNIFIED EMERALD UI (FIXED ENCAPSULATION)
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

        .emerald-card h1, .emerald-card h2, .emerald-card h3 {
            color: #064e3b !important;
            margin-top: 0px !important;
            font-weight: 800 !important;
        }

        /* High-Priority Emerald Button with Ripple */
        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            padding: 14px !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            width: 100% !important;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.2) !important;
        }
        div.stButton > button:hover {
            background-color: #059669 !important;
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4) !important;
            transform: translateY(-1px);
        }
        div.stButton > button:active {
            transform: scale(0.98);
        }

        .chat-scroll-area {
            background: #f9fafb !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px;
            padding: 15px;
            height: 400px;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# LOGIC HELPERS
# =========================================================
def perform_matchmaking():
    """Logic to find a partner and update database status"""
    # 1. Clear any old waiting status for this user to avoid ghosting
    conn.execute("UPDATE profiles SET status='active' WHERE user_id=?", (st.session_state.user_id,))
    
    # 2. Find a peer who is currently waiting
    peer = conn.execute("""
        SELECT p.user_id, a.name 
        FROM profiles p 
        JOIN auth_users a ON a.id = p.user_id 
        WHERE p.status = 'waiting' AND p.user_id != ? 
        LIMIT 1
    """, (st.session_state.user_id,)).fetchone()
    
    if peer:
        match_id = f"session_{int(time.time())}"
        st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
        st.session_state.current_match_id = match_id
        
        # 3. Update both users in DB
        conn.execute("UPDATE profiles SET status='busy', match_id=? WHERE user_id=?", (match_id, st.session_state.user_id))
        conn.execute("UPDATE profiles SET status='busy', match_id=? WHERE user_id=?", (match_id, peer[0]))
        conn.commit()
        return True
    
    # 4. If no peer found, set user to waiting
    conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    return False

# =========================================================
# UI PAGES (STRICT CARD ENCAPSULATION)
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Discovery")
    st.write("Scan the network to find a study partner and start a live session.")
    
    if st.button("Search Compatible Partner"):
        with st.spinner("Establishing secure connection..."):
            success = perform_matchmaking()
            if success:
                st.session_state.session_step = "live"
                st.rerun()
            else:
                st.info("System Notification: You are now in the queue. Waiting for a partner to join...")
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def render_live_chat():
    msgs = conn.execute(
        "SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
        (st.session_state.current_match_id,)
    ).fetchall()
    
    st.markdown('<div class="chat-scroll-area">', unsafe_allow_html=True)
    for sender, message in msgs:
        is_me = (sender == st.session_state.user_name)
        align = "right" if is_me else "left"
        bg = "#10b981" if is_me else "#e2e8f0"
        color = "white" if is_me else "#1e293b"
        st.markdown(f"""
            <div style='text-align: {align}; margin-bottom: 10px;'>
                <div style='display: inline-block; background: {bg}; color: {color}; padding: 10px; border-radius: 10px; max-width: 80%;'>
                    <b>{sender}</b><br>{message}
                </div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Collaborating with {st.session_state.peer_info['name']}")
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
    
    if st.button("Finish Session"):
        st.session_state.session_step = "summary"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Session Analysis")
    st.info("AI is synthesizing your results...")
    
    # Rating Section
    st.subheader("Partner Rating")
    rating = st.feedback("stars", key="stars")
    
    if st.button("Start AI Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Assessment")
    st.write("Generating your custom quiz based on the chat history...")
    if st.button("Complete & Exit"):
        st.session_state.session_step = "discovery"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# ENTRY POINT
# =========================================================
def matchmaking_page():
    inject_ui()
    if "session_step" not in st.session_state: 
        st.session_state.session_step = "discovery"

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
