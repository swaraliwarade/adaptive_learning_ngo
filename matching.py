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
# UTILITIES & STYLES
# =========================================================
def get_user_status(uid):
    res = conn.execute("SELECT status, accepted, match_id FROM profiles WHERE user_id=?", (uid,)).fetchone()
    if res: return res
    conn.execute("INSERT INTO profiles (user_id, status, accepted) VALUES (?, 'active', 0)", (uid,))
    conn.commit()
    return ('active', 0, None)

def inject_ui():
    st.markdown("""
        <style>
        .main-card { background: white; padding: 25px; border-radius: 20px; border-top: 8px solid #10b981; box-shadow: 0 4px 15px rgba(0,0,0,0.05); min-height: 550px; }
        .ai-sidebar-card { background: #f0fdf4; padding: 20px; border-radius: 20px; border: 1px solid #bbf7d0; min-height: 550px; }
        .ai-msg { font-size: 0.85rem; padding: 10px; border-radius: 10px; margin-bottom: 8px; }
        .ai-bot { background: #dcfce7; color: #065f46; border-left: 4px solid #10b981; }
        .ai-user { background: white; color: #1e293b; text-align: right; border-right: 4px solid #94a3b8; }
        .chat-scroll { height: 300px; overflow-y: auto; display: flex; flex-direction: column; background: #f8fafc; border-radius:10px; padding:10px; margin-bottom:10px; }
        .bubble { padding: 10px; border-radius: 12px; margin-bottom: 8px; max-width: 85%; font-size:0.9rem;}
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: #e2e8f0; color: #1e293b; border-bottom-left-radius: 2px; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# PERSISTENT SIDEBAR AI
# =========================================================
def render_persistent_ai():
    st.markdown("<div class='ai-sidebar-card'>", unsafe_allow_html=True)
    st.markdown("### 🤖 Sahay AI Assistant")
    
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = [{"role": "bot", "content": "I'm monitoring your session. Ask me anything about the topics you discuss!"}]

    # Display scrollable history
    chat_container = st.container(height=350)
    for chat in st.session_state.ai_chat_history:
        cls = "ai-bot" if chat["role"] == "bot" else "ai-user"
        chat_container.markdown(f"<div class='ai-msg {cls}'>{chat['content']}</div>", unsafe_allow_html=True)

    with st.form("ai_sidebar_form", clear_on_submit=True):
        u_query = st.text_input("Message AI...", label_visibility="collapsed")
        if st.form_submit_button("Ask"):
            if u_query:
                st.session_state.ai_chat_history.append({"role": "user", "content": u_query})
                st.session_state.ai_chat_history.append({"role": "bot", "content": ask_ai(u_query)})
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN CONTENT PHASES
# =========================================================

def show_discovery():
    st.title("Partner Discovery")
    st.write("Scan the network for a peer student.")
    conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()

    if st.button("Search for Peer"):
        peer = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id = p.user_id WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1", (st.session_state.user_id,)).fetchone()
        if peer:
            m_id = f"sess_{int(time.time())}"
            st.session_state.peer_info, st.session_state.current_match_id = {"id": peer[0], "name": peer[1]}, m_id
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, st.session_state.user_id))
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, peer[0]))
            conn.commit()
            st.session_state.session_step = "confirmation"
            st.rerun()
        else: st.info("Searching... invite a friend to join!")

def show_confirmation():
    st.title("Establish Connection")
    st.write(f"Connect with **{st.session_state.peer_info['name']}**?")
    _, my_acc, _ = get_user_status(st.session_state.user_id)
    _, peer_acc, _ = get_user_status(st.session_state.peer_info['id'])

    if my_acc == 1 and peer_acc == 1:
        st.session_state.session_step = "live"; st.rerun()
    
    c1, c2 = st.columns(2)
    if c1.button("Accept"):
        conn.execute("UPDATE profiles SET accepted=1 WHERE user_id=?", (st.session_state.user_id,))
        conn.commit(); st.rerun()
    if c2.button("Decline"):
        conn.execute("UPDATE profiles SET status='active', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
        conn.commit(); st.session_state.session_step = "discovery"; st.rerun()

@st.fragment(run_every=2)
def render_live_chat():
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", (st.session_state.current_match_id,)).fetchall()
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for sender, msg, f_path in msgs:
        cls = "bubble-me" if sender == st.session_state.user_name else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg if msg else ""}</div>', unsafe_allow_html=True)
        if f_path: st.caption(f"📎 {os.path.basename(f_path)}")
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.title(f"Collaborating with {st.session_state.peer_info['name']}")
    render_live_chat()
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        msg = c1.text_input("Message", label_visibility="collapsed")
        up = c2.file_uploader("File", label_visibility="collapsed")
        if st.form_submit_button("Send"):
            path = None
            if up:
                path = os.path.join(UPLOAD_DIR, up.name)
                with open(path, "wb") as f: f.write(up.getbuffer())
            if msg or up:
                conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)", (st.session_state.current_match_id, st.session_state.user_name, msg, path, int(time.time())))
                conn.commit(); st.rerun()
    if st.button("End Session"):
        st.session_state.session_step = "summary"; st.rerun()

def show_summary():
    st.title("Session Analysis")
    if "ai_summary" not in st.session_state:
        msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
        st.session_state.ai_summary = ask_ai(f"Summarize this: {' '.join([m[1] for m in msgs if m[1]])}")
    st.info(st.session_state.ai_summary)
    if st.button("Take Quiz"):
        st.session_state.session_step = "quiz"; st.rerun()

def show_quiz():
    st.title("AI Practice Quiz")
    if "generated_quiz" not in st.session_state:
        st.session_state.generated_quiz = [{"q": "Did you enjoy the session?", "options": ["Yes", "No"], "correct": "Yes"}]
    for idx, item in enumerate(st.session_state.generated_quiz):
        st.write(f"**{item['q']}**")
        st.radio("Answer:", item['options'], key=f"q_{idx}")
    if st.button("Finish"):
        conn.execute("UPDATE profiles SET status='active', accepted=0, match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
        conn.commit()
        for k in ["generated_quiz","ai_summary","current_match_id"]: st.session_state.pop(k, None)
        st.session_state.session_step = "discovery"; st.rerun()

# =========================================================
# MAIN ROUTER
# =========================================================
def matchmaking_page():
    inject_ui()
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"
    
    col_main, col_ai = st.columns([2.2, 1], gap="medium")
    with col_main:
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        step = st.session_state.session_step
        if step == "discovery": show_discovery()
        elif step == "confirmation": show_confirmation()
        elif step == "live": show_live_session()
        elif step == "summary": show_summary()
        elif step == "quiz": show_quiz()
        st.markdown("</div>", unsafe_allow_html=True)
    with col_ai:
        render_persistent_ai()
