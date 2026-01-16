import streamlit as st
import time
import os
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
POLL_INTERVAL = 3

# =========================================================
# SYSTEM & STATE
# =========================================================
def now(): return int(time.time())

def init_state():
    defaults = {
        "current_match_id": None, 
        "session_ended": False, 
        "chat_log": [],
        "last_msg_ts": 0, 
        "last_poll": 0, 
        "summary": None, 
        "quiz": None,
        "rating_given": False, 
        "ai_chat": [], 
        "proposed_match": None,
        "history_loaded": False
    }
    for k, v in defaults.items(): st.session_state.setdefault(k, v)

def reset_matchmaking():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for k in list(st.session_state.keys()):
        if k not in ["user_id", "user_name", "logged_in", "page"]: del st.session_state[k]
    st.rerun()

# =========================================================
# EMERALD MINIMALIST STYLING
# =========================================================
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    
    /* Emerald Button with Smooth Transition */
    div.stButton > button {
        background-color: #10b981;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease-in-out;
        font-weight: 500;
    }
    div.stButton > button:hover {
        background-color: #059669;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
    }

    /* Modern Chat Bubbles */
    .msg-container { display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; }
    .bubble { 
        padding: 12px 16px; 
        border-radius: 14px; 
        max-width: 80%; 
        font-size: 0.95rem; 
        line-height: 1.4;
    }
    .user { 
        align-self: flex-end; 
        background-color: #f1f5f9; 
        color: #1e293b; 
        border-bottom-right-radius: 2px;
        border-left: 3px solid #cbd5e1;
    }
    .partner { 
        align-self: flex-start; 
        background-color: #ecfdf5; 
        color: #065f46; 
        border-bottom-left-radius: 2px;
        border-left: 3px solid #10b981;
    }
    .sender-name { font-size: 0.75rem; font-weight: 700; margin-bottom: 4px; text-transform: uppercase; opacity: 0.7; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# LOGIC COMPONENTS
# =========================================================
def load_full_history(match_id):
    """Fetches all messages for this session from the database."""
    rows = conn.execute("""
        SELECT sender, message, created_ts FROM messages 
        WHERE match_id=? ORDER BY created_ts ASC
    """, (match_id,)).fetchall()
    
    st.session_state.chat_log = []
    for s, m, ts in rows:
        st.session_state.chat_log.append((s, m))
        st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)
    st.session_state.history_loaded = True

def poll_new_messages(match_id):
    """Only fetches messages newer than the last one displayed."""
    if now() - st.session_state.last_poll > POLL_INTERVAL:
        rows = conn.execute("""
            SELECT sender, message, created_ts FROM messages 
            WHERE match_id=? AND created_ts > ? ORDER BY created_ts ASC
        """, (match_id, st.session_state.last_msg_ts)).fetchall()
        
        if rows:
            for s, m, ts in rows:
                st.session_state.chat_log.append((s, m))
                st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)
            st.session_state.last_poll = now()
            st.rerun()
        st.session_state.last_poll = now()

# =========================================================
# MAIN APP
# =========================================================
def matchmaking_page():
    if not st.session_state.get("user_id"): st.stop()
    init_state()

    # AI Sidebar
    with st.sidebar:
        st.markdown("### Assistant")
        q = st.text_input("Ask AI...", key="ai_q", label_visibility="collapsed")
        if st.button("Query") and q:
            st.session_state.ai_chat.insert(0, (q, ask_ai(q)))
        for q_h, a_h in st.session_state.ai_chat[:2]:
            st.caption(f"Q: {q_h}")
            st.write(a_h)
            st.divider()

    # --- PHASE 1: DISCOVERY ---
    if not st.session_state.current_match_id:
        st.markdown("## Matchmaking")
        
        # Check for incoming match sync
        incoming = conn.execute("SELECT match_id FROM profiles WHERE user_id=? AND status='matched'", (st.session_state.user_id,)).fetchone()
        if incoming:
            st.session_state.current_match_id = incoming[0]
            st.rerun()

        if not st.session_state.proposed_match:
            if st.button("Start Searching"):
                res = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.status='waiting' AND p.user_id!=?", (st.session_state.user_id,)).fetchone()
                if res:
                    st.session_state.proposed_match = {"id": res[0], "name": res[1]}
                    st.rerun()
                else: st.toast("Looking for peers...")
        else:
            with st.container(border=True):
                st.markdown(f"### Connect with {st.session_state.proposed_match['name']}?")
                c1, c2 = st.columns(2)
                if c1.button("Confirm Match"):
                    mid = f"sync_{min(st.session_state.user_id, st.session_state.proposed_match['id'])}_{now()}"
                    conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id IN (?,?)", (mid, st.session_state.user_id, st.session_state.proposed_match['id']))
                    conn.commit()
                    st.session_state.current_match_id = mid
                    st.balloons()
                    st.rerun()
                if c2.button("Skip", type="secondary"): 
                    st.session_state.proposed_match = None
                    st.rerun()

    # --- PHASE 2: LIVE PERSISTENT CHAT ---
    elif st.session_state.current_match_id and not st.session_state.session_ended:
        # Load history once, then poll
        if not st.session_state.history_loaded:
            load_full_history(st.session_state.current_match_id)
        
        poll_new_messages(st.session_state.current_match_id)
        
        st.markdown(f"### Session Hub")
        
        col_chat, col_files = st.columns([2, 1], gap="medium")
        
        with col_chat:
            # Scrollable chat area
            st.markdown('<div class="msg-container">', unsafe_allow_html=True)
            for sender, msg in st.session_state.chat_log:
                is_me = sender == st.session_state.user_name
                type_class = "user" if is_me else "partner"
                st.markdown(f"""
                    <div class="bubble {type_class}">
                        <div class="sender-name">{"You" if is_me else sender}</div>
                        {msg}
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            with st.form("chat_form", clear_on_submit=True):
                m = st.text_input("Message", placeholder="Send a message...", label_visibility="collapsed")
                if st.form_submit_button("Send"):
                    conn.execute("INSERT INTO messages(match_id, sender, message, created_ts) VALUES (?,?,?,?)", 
                                 (st.session_state.current_match_id, st.session_state.user_name, m, now()))
                    conn.commit()
                    st.rerun()

        with col_files:
            st.markdown("#### Files")
            up = st.file_uploader("Share document", label_visibility="collapsed")
            if up:
                with open(os.path.join(UPLOAD_DIR, up.name), "wb") as f: f.write(up.getbuffer())
                st.toast("File synchronized")
            
            st.divider()
            if st.button("Finish Session"):
                log = " ".join([m for _, m in st.session_state.chat_log])
                st.session_state.summary = ask_ai("Summarize: " + log)
                st.session_state.quiz = ask_ai("Create 3 MCQ quiz from: " + log)
                st.session_state.session_ended = True
                st.rerun()

    # --- PHASE 3: SUMMARY ---
    else:
        st.markdown("## Session Summary")
        st.info(st.session_state.summary)
        
        if not st.session_state.rating_given:
            stars = st.feedback("stars")
            if stars is not None:
                st.session_state.rating_given = True
                st.success("Feedback saved")

        st.divider()
        st.markdown("#### AI Generated Quiz")
        st.write(st.session_state.quiz)
        
        val = st.number_input("Score", 0, 3)
        if st.button("Verify"):
            if val == 3: 
                st.balloons()
                st.success("Mastery confirmed!")
        
        if st.button("Close Session"): reset_matchmaking()

matchmaking_page()
