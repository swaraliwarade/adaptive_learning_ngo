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
    res = conn.execute("SELECT status, accepted, match_id FROM profiles WHERE user_id=?", (uid,)).fetchone()
    if res: return res
    conn.execute("INSERT INTO profiles (user_id, status, accepted) VALUES (?, 'active', 0)", (uid,))
    conn.commit()
    return ('active', 0, None)

# =========================================================
# UI STYLES
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
        .chat-scroll {
            background: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px;
            padding: 15px;
            height: 400px;
            overflow-y: auto;
            margin-bottom: 20px;
            display: flex;
            flex-direction: column;
        }
        .bubble { padding: 12px; border-radius: 15px; margin-bottom: 10px; max-width: 80%; font-size: 0.9rem; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 2px; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# REFINED CHAT FRAGMENT
# =========================================================
@st.fragment(run_every=2)
def render_live_chat():
    """Fragment only refreshes the message history, not the inputs."""
    m_id = st.session_state.get("current_match_id")
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", (m_id,)).fetchall()
    
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for sender, msg, f_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cls = "bubble-me" if is_me else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg if msg else ""}</div>', unsafe_allow_html=True)
        if f_path:
             st.info(f"📄 Attached: {os.path.basename(f_path)}")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# UI PAGES
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Discovery")
    st.write("Find a peer to start a collaborative study session.")
    
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
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Confirm Match")
    st.write(f"Connect with **{st.session_state.peer_info['name']}**?")
    
    _, my_acc, _ = get_user_status(st.session_state.user_id)
    _, peer_acc, _ = get_user_status(st.session_state.peer_info['id'])

    if my_acc == 1 and peer_acc == 1:
        st.session_state.session_step = "live"
        st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Accept Session"):
            conn.execute("UPDATE profiles SET accepted=1 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.rerun()
    with col2:
        if st.button("Decline"):
            conn.execute("UPDATE profiles SET status='active', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.session_state.session_step = "discovery"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_live_session():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Live Session: {st.session_state.peer_info['name']}")
    
    # 1. Chat History (Refreshing Fragment)
    render_live_chat()
    
    # 2. Input Section (Static - won't clear while typing)
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        msg = c1.text_input("Message", placeholder="Discuss your topics here...", label_visibility="collapsed")
        up = c2.file_uploader("Upload", label_visibility="collapsed")
        if st.form_submit_button("Send Message"):
            path = None
            if up:
                path = os.path.join(UPLOAD_DIR, up.name)
                with open(path, "wb") as f: f.write(up.getbuffer())
            if msg or up:
                conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                            (st.session_state.current_match_id, st.session_state.user_name, msg, path, int(time.time())))
                conn.commit()
                st.rerun()

    st.divider()
    if st.button("End Session & Get AI Summary", type="secondary"):
        st.session_state.session_step = "summary"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Session Summary")
    
    # AI Chatbot summary logic
    if "ai_summary" not in st.session_state:
        with st.spinner("AI is analyzing your conversation..."):
            msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
            chat_context = "\n".join([f"{m[0]}: {m[1]}" for m in msgs if m[1]])
            try:
                st.session_state.ai_summary = ask_ai(f"Summarize the key learning points from this peer-to-peer discussion: {chat_context}")
            except:
                st.session_state.ai_summary = "Session ended. Great job collaborating!"

    st.info(st.session_state.ai_summary)
    
    st.subheader("Rate your partner")
    st.feedback("stars", key="session_feedback")
    
    if st.button("Generate Practice Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("AI Practice Quiz")
    st.write("Test what you just learned!")
    # Quiz Logic goes here...
    if st.button("Finish & Exit"):
        conn.execute("UPDATE profiles SET status='active', accepted=0, match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
        conn.commit()
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
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()
