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
# FORCED EMERALD THEME + RIPPLE ANIMATION
# =========================================================
st.markdown("""
    <style>
    /* 1. Global emerald override for all Streamlit buttons */
    /* This targets the specific class seen in your screenshot */
    div.stButton > button, div.stDownloadButton > button {
        background-color: #10b981 !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        width: 100% !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.3s ease !important;
        position: relative;
        overflow: hidden;
    }

    /* 2. Ripple effect animation using a radial gradient background */
    div.stButton > button:active::after {
        content: "";
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        background-image: radial-gradient(circle, #fff 10%, transparent 10.01%);
        background-repeat: no-repeat;
        background-position: 50%;
        transform: scale(10, 10);
        opacity: 0;
        transition: transform .5s, opacity 1s;
    }

    div.stButton > button:active {
        background-color: #059669 !important;
        transform: scale(0.98) !important;
    }

    div.stButton > button:hover {
        background-color: #059669 !important;
        box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.4) !important;
        border-color: #10b981 !important;
    }

    /* 3. Aesthetic Emerald Card for the interface */
    .emerald-card {
        background: #ffffff !important;
        padding: 30px !important;
        border-radius: 16px !important;
        border: 1px solid #d1fae5 !important;
        border-top: 10px solid #10b981 !important;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05) !important;
        margin-bottom: 25px;
    }

    h1, h2, h3 {
        color: #064e3b !important;
    }
    
    .chat-container {
        background: #f0fdf4 !important;
        border-radius: 12px;
        padding: 15px;
        height: 400px;
        overflow-y: auto;
        border: 1px solid #b91c1c00;
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
# MATCHMAKING COMPONENTS
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Peer Matchmaking")
    st.write("Find a compatible study partner using our AI matching system.")
    st.write("---")
    
    # This button will now be Emerald with a ripple effect
    if st.button("Search Compatible Partner", type="primary"):
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
            st.info("System Notification: Searching for active partners...")
            conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    p = st.session_state.peer_info
    st.subheader(f"System Match: {p['name']}")
    st.write(f"**Focus:** {p['ints']}")
    st.write(f"**Bio:** {p['bio']}")
    st.divider()
    
    if st.button("Accept and Connect"):
        st.balloons()
        time.sleep(1)
        st.session_state.session_step = "live"
        st.rerun()
    if st.button("Decline Match"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def live_chat_fragment():
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                         (st.session_state.current_match_id,)).fetchall()
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for sender, message, file_path in msgs:
        is_me = (sender == st.session_state.user_name)
        color = "#10b981" if is_me else "#ffffff"
        txt_color = "white" if is_me else "#1f2937"
        align = "flex-end" if is_me else "flex-start"
        
        st.markdown(f"""
            <div style="display: flex; flex-direction: column; align-items: {align}; margin-bottom: 10px;">
                <div style="background: {color}; color: {txt_color}; padding: 10px 15px; border-radius: 12px; max-width: 80%; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <b>{sender}</b><br>{message if message else ""}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if file_path:
            st.download_button(f"Shared Document: {os.path.basename(file_path)}", open(file_path, "rb"), file_name=os.path.basename(file_path), key=f"f_{time.time()}")
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.subheader(f"Active Session with {st.session_state.peer_info['name']}")
    live_chat_fragment()

    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            txt = st.text_input("Message", placeholder="Communicate here...", label_visibility="collapsed", key="chat_in")
        with c2:
            file = st.file_uploader("Upload", label_visibility="collapsed", key="f_up")
        with c3:
            if st.button("Send Message"):
                path = None
                if file:
                    path = os.path.join(UPLOAD_DIR, file.name)
                    with open(path, "wb") as f: f.write(file.getbuffer())
                if txt or file:
                    conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, txt, path, int(time.time())))
                    conn.commit()
                    st.rerun()
    
    if st.button("Close Room"):
        st.session_state.session_step = "summary"
        st.rerun()

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Learning Summary")
    st.write("System generating session analysis...")
    if st.button("Start Knowledge Check"):
        st.session_state.session_step = "quiz"
        st.rerun()
    if st.button("Back to Hub"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("AI Assessment")
    if st.button("Submit and Exit"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def matchmaking_page():
    ensure_state()
    with st.sidebar:
        st.title("AI Systems")
        q = st.text_area("Request AI Consultation")
        if st.button("Execute Process"):
            st.write(ask_ai(q))

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
