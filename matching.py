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
# PERMANENT STYLE GUARD (EMERALD + RIPPLE)
# =========================================================
def inject_emerald_theme():
    st.markdown("""
        <style>
        /* Force background to stay Slate/White and not Pink */
        .stApp {
            background-color: #f8fafc !important;
        }

        /* Target all buttons with high-priority Emerald */
        div.stButton > button, 
        div.stDownloadButton > button, 
        .st-emotion-cache-19rxjzo > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            padding: 12px 24px !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.2) !important;
            position: relative;
            overflow: hidden;
        }

        /* Hover & Ripple Simulation */
        div.stButton > button:hover {
            background-color: #059669 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.4) !important;
        }

        /* Active click 'Ripple' feel */
        div.stButton > button:active {
            transform: scale(0.95) !important;
            background-color: #047857 !important;
        }

        /* Emerald Dashboard Card */
        .emerald-card {
            background: #ffffff !important;
            padding: 30px !important;
            border-radius: 16px !important;
            border-top: 8px solid #10b981 !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1) !important;
            margin-bottom: 25px;
            color: #1e293b;
        }

        /* Typography */
        h1, h2, h3, h4 {
            color: #064e3b !important;
            font-weight: 800 !important;
        }
        
        /* Chat UI Emerald Theme */
        .chat-container {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px;
            padding: 20px;
            height: 400px;
            overflow-y: auto;
        }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# STATE & FLOW
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
    st.title("Partner Discovery")
    st.write("Engage with the AI matching engine to find a compatible collaborator.")
    st.write("---")
    
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
            st.info("System: Scanning network for active peers...")
            conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    p = st.session_state.peer_info
    st.subheader(f"Collaboration Match: {p['name']}")
    st.write(f"**Competencies:** {p['ints']}")
    st.write(f"**Bio:** {p['bio']}")
    st.write("---")
    
    if st.button("Establish Connection"):
        st.balloons()
        time.sleep(1)
        st.session_state.session_step = "live"
        st.rerun()
    if st.button("Request Alternative"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def live_chat_fragment():
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                         (st.session_state.current_match_id,)).fetchall()
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for sender, message, file_path in msgs:
        is_me = (sender == st.session_state.user_name)
        align = "flex-end" if is_me else "flex-start"
        bg = "#10b981" if is_me else "#f1f5f9"
        tc = "white" if is_me else "#1e293b"
        
        st.markdown(f"""
            <div style="display: flex; flex-direction: column; align-items: {align}; margin-bottom: 12px;">
                <div style="background: {bg}; color: {tc}; padding: 12px 16px; border-radius: 12px; max-width: 80%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    <small><b>{sender}</b></small><br>{message if message else ""}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if file_path:
            with open(file_path, "rb") as f:
                st.download_button(f"View Resource: {os.path.basename(file_path)}", f, file_name=os.path.basename(file_path), key=f"f_{time.time()}")
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.subheader(f"Collaborating with {st.session_state.peer_info['name']}")
    live_chat_fragment()

    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            txt = st.text_input("Input", placeholder="Message partner...", label_visibility="collapsed", key="chat_in")
        with c2:
            file = st.file_uploader("File", label_visibility="collapsed", key="f_up")
        with c3:
            if st.button("Send"):
                path = None
                if file:
                    path = os.path.join(UPLOAD_DIR, file.name)
                    with open(path, "wb") as f: f.write(file.getbuffer())
                if txt or file:
                    conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, txt, path, int(time.time())))
                    conn.commit()
                    st.rerun()
    
    if st.button("Exit Session"):
        st.session_state.session_step = "summary"
        st.rerun()

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Performance Summary")
    st.write("System: Synthesizing session data for review...")
    if st.button("Initiate Assessment"):
        st.session_state.session_step = "quiz"
        st.rerun()
    if st.button("Back to Hub"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("System Assessment")
    if st.button("Finalize and Exit"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN ENTRY POINT
# =========================================================
def matchmaking_page():
    # THE FIX: Inject CSS immediately at the start of every rerun
    inject_emerald_theme()
    ensure_state()
    
    with st.sidebar:
        st.title("AI Consultation")
        q = st.text_area("Request Support")
        if st.button("Run Process"):
            st.write(ask_ai(q))

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
