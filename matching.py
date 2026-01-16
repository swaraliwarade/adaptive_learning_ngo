import streamlit as st
import time
import os
import requests
import json
from database import conn

# Defensive Import for Animations
try:
    from streamlit_lottie import st_lottie
    LOTTIE_AVAILABLE = True
except ImportError:
    LOTTIE_AVAILABLE = False

# =========================================================
# THEME & VECTOR STYLING
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem !important; }
        .sahay-card {
            background: #ffffff;
            border: 2px solid #10b981;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 25px rgba(16, 185, 129, 0.1);
            margin-bottom: 20px;
        }
        .chat-scroll {
            height: 350px;
            overflow-y: auto;
            background: #f8fafc;
            border-radius: 15px;
            padding: 15px;
            border: 1px solid #e2e8f0;
        }
        .bubble { padding: 10px; border-radius: 12px; margin-bottom: 8px; max-width: 80%; font-size: 0.9rem; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 2px; }
        .ai-panel { background: #f0fdf4; border-radius: 20px; padding: 20px; border: 1px solid #bbf7d0; min-height: 550px; }
        div.stButton > button {
            background: linear-gradient(135deg, #10b981, #059669) !important;
            color: white !important;
            border-radius: 12px !important;
            border: none !important;
            font-weight: 700 !important;
            height: 3rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_lottie_json(url):
    try: return requests.get(url).json()
    except: return None

# =========================================================
# MATCHMAKING ENGINE
# =========================================================
def find_compatible_peer():
    # Fetch current user data
    u = conn.execute("SELECT grade, strong_subjects, weak_subjects FROM profiles WHERE user_id=?", (st.session_state.user_id,)).fetchone()
    if not u: return None
    
    u_grade, u_strong, u_weak = u
    u_strong_list = [s.strip().lower() for s in u_strong.split(',')]
    u_weak_list = [w.strip().lower() for w in u_weak.split(',')]

    # Search for peers in same grade who are waiting
    peers = conn.execute("""
        SELECT p.user_id, a.name, p.strong_subjects, p.weak_subjects 
        FROM profiles p 
        JOIN auth_users a ON a.id = p.user_id 
        WHERE p.status = 'waiting' AND p.user_id != ? AND p.grade = ?
    """, (st.session_state.user_id, u_grade)).fetchall()

    for p_id, p_name, p_strong, p_weak in peers:
        p_strong_list = [s.strip().lower() for s in p_strong.split(',')]
        p_weak_list = [w.strip().lower() for w in p_weak.split(',')]
        
        # LOGIC: I am strong in what you are weak in AND you are strong in what I am weak in
        can_help_peer = any(s in p_weak_list for s in u_strong_list)
        peer_can_help_me = any(s in u_weak_list for s in p_strong_list)
        
        if can_help_peer and peer_can_help_me:
            return {"id": p_id, "name": p_name, "p_strong": p_strong, "p_weak": p_weak}
    return None

# =========================================================
# LIVE CHAT FRAGMENT
# =========================================================
@st.fragment(run_every=2)
def render_chat():
    m_id = st.session_state.get("current_match_id")
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", (m_id,)).fetchall()
    
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for sender, msg, f_path in msgs:
        cls = "bubble-me" if sender == st.session_state.user_name else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg if msg else ""}</div>', unsafe_allow_html=True)
        if f_path: st.caption(f"💠 File Attached: {os.path.basename(f_path)}")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# PAGE ROUTER
# =========================================================
def matchmaking_page():
    inject_ui()
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

    col_main, col_ai = st.columns([2.2, 1], gap="medium")
    
    with col_main:
        # STEP 1: DISCOVERY
        if st.session_state.session_step == "discovery":
            st.markdown("### 💠 Peer Matchmaking")
            st.write("Match with someone whose strengths cover your weaknesses.")
            
            if st.button("Start Real-Time Search"):
                match = find_compatible_peer()
                if match: st.session_state.found_peer = match
                else: st.warning("💠 No perfectly compatible peers found yet. Scanning...")

            if "found_peer" in st.session_state:
                p = st.session_state.found_peer
                st.markdown(f"""
                    <div class='sahay-card'>
                        <h4>💠 Match Found: {p['name']}</h4>
                        <p>They excel in: <b>{p['p_strong']}</b></p>
                        <p>Compatibility: <b>High (Mutual Benefit)</b></p>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button("Accept & Connect"):
                    st.session_state.session_step = "celebration"
                    st.rerun()

        # STEP 2: CELEBRATION
        elif st.session_state.session_step == "celebration":
            lottie_data = load_lottie_json("https://assets3.lottiefiles.com/packages/lf20_pqnfmone.json")
            if LOTTIE_AVAILABLE and lottie_data:
                st_lottie(lottie_data, height=300)
            st.markdown("<h2 style='text-align: center; color: #10b981;'>💠 Connected!</h2>", unsafe_allow_html=True)
            time.sleep(2)
            st.session_state.current_match_id = f"sess_{int(time.time())}"
            st.session_state.session_step = "live"
            st.rerun()

        # STEP 3: LIVE SESSION
        elif st.session_state.session_step == "live":
            st.markdown(f"### 💠 Session: {st.session_state.found_peer['name']}")
            render_chat()
            
            with st.form("chat_input", clear_on_submit=True):
                c1, c2 = st.columns([4, 1])
                msg = c1.text_input("Message", label_visibility="collapsed")
                up = c2.file_uploader("💠", label_visibility="collapsed")
                if st.form_submit_button("Send"):
                    f_path = None
                    if up:
                        f_path = f"uploads/{up.name}"
                        with open(f_path, "wb") as f: f.write(up.getbuffer())
                    conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, msg, f_path, int(time.time())))
                    conn.commit(); st.rerun()

            if st.button("End Session"):
                st.session_state.session_step = "discovery"
                del st.session_state.found_peer
                st.rerun()

    with col_ai:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("#### 💠 Sahay AI Assistant")
        st.caption("Contextual Monitoring Active")
        st.divider()
        st.write("I am tracking your chat for key learning points.")
        st.markdown("</div>", unsafe_allow_html=True)
