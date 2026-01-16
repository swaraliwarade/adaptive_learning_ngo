import streamlit as st
import time
import os
import requests
from database import conn
from ai_helper import ask_ai

# Defensive Import for Animations
try:
    from streamlit_lottie import st_lottie
    LOTTIE_AVAILABLE = True
except ImportError:
    LOTTIE_AVAILABLE = False

@st.cache_data
def load_lottie_json(url):
    try: return requests.get(url).json()
    except: return None

def inject_ui():
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem !important; }
        .chat-scroll { height: 350px; overflow-y: auto; background: #f8fafc; border-radius: 15px; padding: 15px; border: 1px solid #e2e8f0; margin-bottom: 10px; }
        .bubble { padding: 10px; border-radius: 12px; margin-bottom: 8px; max-width: 80%; font-size: 0.9rem; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 2px; }
        .ai-panel { background: #f0fdf4; border-radius: 20px; padding: 20px; border: 1px solid #bbf7d0; min-height: 550px; }
        div.stButton > button { background: linear-gradient(135deg, #10b981, #059669) !important; color: white !important; border-radius: 12px !important; border: none !important; font-weight: 700 !important; height: 3rem !important; width: 100%; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# MATCHMAKING ENGINE
# =========================================================
def find_compatible_peer():
    u = conn.execute("SELECT grade, strong_subjects, weak_subjects FROM profiles WHERE user_id=?", (st.session_state.user_id,)).fetchone()
    if not u: return None
    u_grade, u_strong, u_weak = u
    u_strong_list = [s.strip().lower() for s in (u_strong.split(',') if u_strong else [])]
    u_weak_list = [w.strip().lower() for w in (u_weak.split(',') if u_weak else [])]

    peers = conn.execute("""
        SELECT p.user_id, a.name, p.strong_subjects, p.weak_subjects 
        FROM profiles p JOIN auth_users a ON a.id = p.user_id 
        WHERE p.status = 'waiting' AND p.user_id != ? AND p.grade = ?
    """, (st.session_state.user_id, u_grade)).fetchall()

    for p_id, p_name, p_strong, p_weak in peers:
        p_strong_list = [s.strip().lower() for s in (p_strong.split(',') if p_strong else [])]
        p_weak_list = [w.strip().lower() for w in (p_weak.split(',') if p_weak else [])]
        if any(s in p_weak_list for s in u_strong_list) and any(s in u_weak_list for s in p_strong_list):
            return {"id": p_id, "name": p_name, "p_strong": p_strong, "p_weak": p_weak}
    return None

# =========================================================
# LIVE CHAT & COMPONENTS
# =========================================================
@st.fragment(run_every=2)
def render_chat():
    m_id = st.session_state.get("current_match_id")
    msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", (m_id,)).fetchall()
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for sender, msg in msgs:
        cls = "bubble-me" if sender == st.session_state.user_name else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# PAGE ROUTER
# =========================================================
def matchmaking_page():
    inject_ui()
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

    col_main, col_ai = st.columns([2.2, 1], gap="medium")
    
    with col_main:
        # 1. DISCOVERY
        if st.session_state.session_step == "discovery":
            st.markdown("### 💠 Find Your Study Peer")
            if st.button("Start Real-Time Search"):
                match = find_compatible_peer()
                if match: 
                    st.session_state.found_peer = match
                    st.session_state.session_step = "joining"
                    st.rerun()
                else: st.warning("💠 No peers found. System is scanning...")

        # 2. JOINING ANIMATION
        elif st.session_state.session_step == "joining":
            lottie_json = load_lottie_json("https://assets9.lottiefiles.com/packages/lf20_ovws8adp.json") # Connecting animation
            if LOTTIE_AVAILABLE and lottie_json:
                st_lottie(lottie_json, height=300, key="join")
            st.markdown("<h4 style='text-align: center;'>💠 Establishing Secure Connection...</h4>", unsafe_allow_html=True)
            time.sleep(3)
            st.session_state.current_match_id = f"sess_{int(time.time())}"
            st.session_state.session_step = "live"
            st.rerun()

        # 3. LIVE SESSION
        elif st.session_state.session_step == "live":
            st.markdown(f"### 💠 Session with {st.session_state.found_peer['name']}")
            render_chat()
            
            with st.form("chat_input", clear_on_submit=True):
                c1, c2 = st.columns([4, 1])
                msg = c1.text_input("Message", label_visibility="collapsed")
                up = c2.file_uploader("💠", label_visibility="collapsed")
                if st.form_submit_button("Send"):
                    conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, msg, int(time.time())))
                    conn.commit(); st.rerun()

            if st.button("End Session"):
                st.session_state.session_step = "summary"
                st.rerun()

        # 4. SUMMARY & QUIZ
        elif st.session_state.session_step == "summary":
            st.markdown("### 💠 Session Analysis")
            msgs = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
            chat_text = " ".join([m[0] for m in msgs])
            
            with st.spinner("Generating AI Summary..."):
                summary = ask_ai(f"Summarize this study session: {chat_text}")
                st.write(summary)
            
            st.divider()
            st.markdown("#### 💠 Concept Check Quiz")
            with st.spinner("Generating Quiz based on your chat..."):
                quiz_q = ask_ai(f"Generate 3 multiple choice questions based on: {chat_text}. Format: Question, Options, Answer.")
                st.write(quiz_q)
            
            if st.button("Finish & Exit"):
                st.session_state.session_step = "discovery"
                del st.session_state.found_peer
                st.rerun()

    with col_ai:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("#### 💠 Sahay AI Assistant")
        st.caption("Monitoring Live Chat")
        st.divider()
        st.write("I am analyzing your discussion to prepare your summary and quiz.")
        st.markdown("</div>", unsafe_allow_html=True)
