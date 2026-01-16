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
# DEFENSIVE DATA FETCHING
# =========================================================
def get_user_status(uid):
    """Safely fetch user status and acceptance state"""
    res = conn.execute("SELECT status, accepted, match_id FROM profiles WHERE user_id=?", (uid,)).fetchone()
    if res:
        return res
    # If no profile exists, create one on the fly to prevent TypeErrors
    conn.execute("INSERT INTO profiles (user_id, status, accepted) VALUES (?, 'active', 0)", (uid,))
    conn.commit()
    return ('active', 0, None)

# =========================================================
# PERMANENT EMERALD UI
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        .emerald-card {
            background: white !important;
            padding: 30px !important;
            border-radius: 20px !important;
            border-top: 10px solid #10b981 !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important;
            margin-bottom: 25px;
        }
        .emerald-card h1, .emerald-card h2, .emerald-card h3 { color: #064e3b !important; font-weight: 800 !important; margin-top: 0px !important; }
        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            padding: 12px !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            width: 100% !important;
        }
        .chat-scroll { background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 12px; padding: 15px; height: 350px; overflow-y: auto; margin-bottom: 20px; }
        .bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 10px; max-width: 80%; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 2px; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# BACKGROUND LISTENER
# =========================================================
@st.fragment(run_every=3)
def match_listener():
    uid = st.session_state.user_id
    db_status, db_accepted, db_match_id = get_user_status(uid)
    
    if db_status == 'confirming' and st.session_state.session_step == "discovery":
        peer = conn.execute("""
            SELECT p.user_id, a.name FROM profiles p 
            JOIN auth_users a ON a.id = p.user_id 
            WHERE p.match_id = ? AND p.user_id != ?
        """, (db_match_id, uid)).fetchone()
        
        if peer:
            st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
            st.session_state.current_match_id = db_match_id
            st.session_state.session_step = "confirmation"
            st.rerun()

# =========================================================
# UI MODULES
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Discovery")
    st.write("Scan the network for a compatible peer.")
    
    # Set status to waiting safely
    conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()

    if st.button("Search Compatible Partner"):
        peer = conn.execute("""
            SELECT p.user_id, a.name FROM profiles p 
            JOIN auth_users a ON a.id = p.user_id 
            WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()
        
        if peer:
            m_id = f"sess_{int(time.time())}"
            st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
            st.session_state.current_match_id = m_id
            
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, st.session_state.user_id))
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, peer[0]))
            conn.commit()
            st.session_state.session_step = "confirmation"
            st.rerun()
        else:
            st.info("System: Scanning active nodes... No peers found yet.")

    match_listener()
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Incoming Request")
    st.write(f"Do you want to start a session with **{st.session_state.peer_info['name']}**?")
    
    # Safe Fetching to prevent fetchone()[0] TypeError
    _, my_acc, _ = get_user_status(st.session_state.user_id)
    _, peer_acc, _ = get_user_status(st.session_state.peer_info['id'])

    if my_acc == 1 and peer_acc == 1:
        st.session_state.session_step = "live"
        st.rerun()
    elif my_acc == 1:
        st.warning(f"Waiting for {st.session_state.peer_info['name']} to accept...")
        time.sleep(2)
        st.rerun()
    else:
        if st.button("Accept & Connect"):
            conn.execute("UPDATE profiles SET accepted=1 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.rerun()
        
        if st.button("Decline"):
            conn.execute("UPDATE profiles SET status='waiting', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.session_state.session_step = "discovery"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def render_live_chat():
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                       (st.session_state.current_match_id,)).fetchall()
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for sender, msg, f_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cls = "bubble-me" if is_me else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg if msg else ""}</div>', unsafe_allow_html=True)
        if f_path:
            with open(f_path, "rb") as f:
                st.download_button("Download File", f, file_name=os.path.basename(f_path), key=f"dl_{f_path}")
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Collaborating: {st.session_state.peer_info['name']}")
    render_live_chat()
    
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        msg = st.text_input("Message", label_visibility="collapsed", placeholder="Type...", key="chat_input")
    with c2:
        up = st.file_uploader("File", label_visibility="collapsed", key="file_up")
    with c3:
        if st.button("Send"):
            path = None
            if up:
                path = os.path.join(UPLOAD_DIR, up.name)
                with open(path, "wb") as f: f.write(up.getbuffer())
            if msg or up:
                conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                            (st.session_state.current_match_id, st.session_state.user_name, msg, path, int(time.time())))
                conn.commit()
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
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    else: 
        st.session_state.session_step = "discovery"
        st.rerun()
