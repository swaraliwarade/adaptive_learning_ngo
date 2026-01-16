import streamlit as st
import time
import os
import requests
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
        
        /* Chat Container Styling */
        .chat-scroll {
            height: 400px;
            overflow-y: auto;
            background: #f8fafc;
            border-radius: 20px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #e2e8f0;
        }
        .bubble { padding: 12px; border-radius: 15px; margin-bottom: 8px; max-width: 80%; line-height: 1.4; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 2px; }
        
        /* Sidebar AI Assistant */
        .ai-sidebar {
            background: #f0fdf4;
            border-radius: 24px;
            padding: 20px;
            border: 1px solid #bbf7d0;
            min-height: 550px;
        }
        </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_lottie_json(url):
    try:
        return requests.get(url).json()
    except: return None

# =========================================================
# LIVE CHAT COMPONENTS
# =========================================================

@st.fragment(run_every=2)
def render_chat_messages():
    """Refreshes messages every 2 seconds without reloading the whole page."""
    m_id = st.session_state.get("current_match_id")
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", (m_id,)).fetchall()
    
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for sender, msg, f_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cls = "bubble-me" if is_me else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg if msg else ""}</div>', unsafe_allow_html=True)
        if f_path:
             st.caption(f"💠 File: {os.path.basename(f_path)}")
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.markdown(f"### 💠 Collaborative Session: {st.session_state.peer_info['name']}")
    
    # 1. Live Chat History
    render_chat_messages()
    
    # 2. Input Form (Message + File)
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        msg_input = c1.text_input("Type your message...", label_visibility="collapsed")
        file_input = c2.file_uploader("Upload", label_visibility="collapsed")
        
        if st.form_submit_button("Send 💠"):
            file_path = None
            if file_input:
                file_path = os.path.join("uploads", file_input.name)
                with open(file_path, "wb") as f: f.write(file_input.getbuffer())
            
            if msg_input or file_input:
                conn.execute("""
                    INSERT INTO messages (match_id, sender, message, file_path, created_ts) 
                    VALUES (?, ?, ?, ?, ?)
                """, (st.session_state.current_match_id, st.session_state.user_name, msg_input, file_path, int(time.time())))
                conn.commit()
                st.rerun()

    st.divider()
    
    # 3. End Session Button
    if st.button("End Session & Get AI Summary", use_container_width=True):
        st.session_state.session_step = "summary"
        st.rerun()

# =========================================================
# MATCHMAKING ROUTER
# =========================================================
def matchmaking_page():
    inject_ui()
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

    col_main, col_ai = st.columns([2.2, 1], gap="medium")
    
    with col_main:
        step = st.session_state.session_step
        
        if step == "discovery":
            # Discovery logic here (Search button -> Peer Card)
            show_discovery_logic() 
            
        elif step == "celebration":
            # Celebration Phase
            lottie_json = load_lottie_json("https://assets3.lottiefiles.com/packages/lf20_pqnfmone.json")
            if LOTTIE_AVAILABLE and lottie_json:
                st_lottie(lottie_json, height=300, key="success_anim")
            st.markdown("<h2 style='text-align: center; color: #10b981;'>💠 Connection Established</h2>", unsafe_allow_html=True)
            time.sleep(2.5)
            st.session_state.session_step = "live"
            st.rerun()
            
        elif step == "live":
            show_live_session()
            
        elif step == "summary":
            st.markdown("### 💠 Session Wrap-up")
            st.info("AI Analysis: You both covered 3 main topics. Great work!")
            if st.button("Return to Dashboard"):
                st.session_state.session_step = "discovery"
                st.rerun()

    with col_ai:
        st.markdown("<div class='ai-sidebar'>", unsafe_allow_html=True)
        st.markdown("#### 💠 Sahay AI Assistant")
        st.caption("Active Monitoring Enabled")
        st.divider()
        st.write("I'm here to help you and your partner. Just ask!")
        st.markdown("</div>", unsafe_allow_html=True)

# Helper for the search logic in discovery phase
def show_discovery_logic():
    st.markdown("### 💠 Peer Matchmaking")
    if st.button("Search Compatible Partner"):
        # Peer lookup logic...
        st.session_state.found_peer = {"id": 1, "name": "Deepak", "grade": "10"} # Mock example
    
    if "found_peer" in st.session_state:
        st.markdown(f"<div class='sahay-card'>{st.session_state.found_peer['name']}</div>", unsafe_allow_html=True)
        if st.button("Accept & Connect"):
            st.session_state.session_step = "celebration"
            st.rerun()
