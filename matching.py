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
# CSS & UI STYLING
# =========================================================
st.markdown("""
    <style>
    /* Emerald Theme Overrides */
    .stButton > button { 
        border-radius: 8px; 
        font-weight: 600; 
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    /* Chat Container */
    .chat-stage {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        height: 400px;
        overflow-y: auto;
        padding: 20px;
        margin-bottom: 15px;
        display: flex;
        flex-direction: column;
    }
    .msg-box { 
        padding: 10px 15px; 
        border-radius: 15px; 
        margin-bottom: 10px; 
        max-width: 75%; 
        font-size: 0.95rem;
    }
    .my-msg { 
        background-color: #10b981; 
        color: white; 
        align-self: flex-end; 
        border-bottom-right-radius: 2px; 
    }
    .peer-msg { 
        background-color: #f3f4f6; 
        color: #1f2937; 
        align-self: flex-start; 
        border-bottom-left-radius: 2px;
        border: 1px solid #e5e7eb;
    }
    /* Info Cards */
    .profile-card {
        background: #f9fafb;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #10b981;
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# SESSION STATE MANAGEMENT
# =========================================================
def ensure_state():
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"
    if "current_match_id" not in st.session_state: st.session_state.current_match_id = None
    if "peer_info" not in st.session_state: st.session_state.peer_info = None
    if "ai_history" not in st.session_state: st.session_state.ai_history = []
    if "quiz_data" not in st.session_state: st.session_state.quiz_data = None
    if "summary" not in st.session_state: st.session_state.summary = ""

def reset_matchmaking():
    # Cleanup database status
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    # Reset local state
    st.session_state.session_step = "discovery"
    st.session_state.current_match_id = None
    st.session_state.peer_info = None
    st.session_state.quiz_data = None
    st.session_state.summary = ""
    st.rerun()

# =========================================================
# AI ASSISTANT (SIDEBAR)
# =========================================================
def sidebar_ai():
    with st.sidebar:
        st.title("🤖 AI Tutor")
        st.caption("Available at all times for help.")
        query = st.text_area("Ask AI...", placeholder="Explain the last topic...", key="side_ai_task", height=80)
        if st.button("Get Help", use_container_width=True):
            if query:
                with st.spinner("AI is typing..."):
                    ans = ask_ai(query)
                    st.session_state.ai_history.append({"q": query, "a": ans})
        
        for item in reversed(st.session_state.ai_history[-3:]):
            with st.expander(f"Q: {item['q'][:20]}...", expanded=False):
                st.write(item['a'])

# =========================================================
# MAIN APP PAGES
# =========================================================

def show_discovery():
    st.header("Find a Study Partner")
    st.write("Connect with someone whose interests align with yours.")
    
    if st.button("Search for Compatible Matches", type="primary"):
        with st.spinner("Matching based on compatibility..."):
            # Real-time search for someone 'waiting'
            peer = conn.execute("""
                SELECT p.user_id, a.name, p.bio, p.interests 
                FROM profiles p JOIN auth_users a ON a.id=p.user_id 
                WHERE p.status='waiting' AND p.user_id != ? LIMIT 1
            """, (st.session_state.user_id,)).fetchone()

            if peer:
                st.session_state.peer_info = {"id": peer[0], "name": peer[1], "bio": peer[2], "ints": peer[3]}
                st.session_state.current_match_id = f"match_{min(st.session_state.user_id, peer[0])}_{max(st.session_state.user_id, peer[0])}"
                st.session_state.session_step = "confirmation"
                st.rerun()
            else:
                st.warning("No partners online right now. We've marked you as 'Waiting' so others can find you.")
                conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
                conn.commit()

def show_confirmation():
    st.subheader("Match Found! 🤝")
    
    # Compatibility calculation (Mocked at 85% or logic based on interests)
    score = 88 
    
    st.markdown(f"""
    <div class="profile-card">
        <h3>{st.session_state.peer_info['name']}</h3>
        <p><b>Compatibility Score:</b> <span style="color:#10b981;">{score}%</span></p>
        <p><b>Interests:</b> {st.session_state.peer_info['ints']}</p>
        <p><i>"{st.session_state.peer_info['bio']}"</i></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("---")
    col1, col2 = st.columns(2)
    if col1.button("Accept & Start", type="primary", use_container_width=True):
        st.balloons()
        time.sleep(1.5)
        st.session_state.session_step = "live"
        st.rerun()
    if col2.button("Decline", use_container_width=True):
        reset_matchmaking()

@st.fragment(run_every=3)
def live_chat_ui():
    msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                         (st.session_state.current_match_id,)).fetchall()
    
    st.markdown('<div class="chat-stage">', unsafe_allow_html=True)
    for sender, msg in msgs:
        is_me = (sender == st.session_state.user_name)
        css = "my-msg" if is_me else "peer-msg"
        st.markdown(f'<div class="msg-box {css}"><b>{sender}</b><br>{msg}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.title("Live Study Session")
    
    col_end, _ = st.columns([1, 3])
    if col_end.button("End Session", type="secondary"):
        st.session_state.session_step = "summary"
        st.rerun()

    live_chat_ui()

    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            msg_input = st.text_input("Type message...", label_visibility="collapsed", key="chat_in")
        with c2:
            st.file_uploader("Upload", label_visibility="collapsed")
        with c3:
            if st.button("Send", type="primary", use_container_width=True):
                if msg_input:
                    conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, msg_input, int(time.time())))
                    conn.commit()
                    st.rerun()

def show_summary():
    st.header("Session Summary")
    if not st.session_state.summary:
        with st.spinner("AI generating summary..."):
            history = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
            chat_blob = " ".join([m[0] for m in history])
            st.session_state.summary = ask_ai(f"Summarize the key learning points from this chat: {chat_blob}")
    
    st.info(st.session_state.summary)
    
    st.subheader("Rate your Partner")
    stars = st.feedback("stars", key="rating_stars")
    if st.button("Submit Rating"):
        st.success("Rating saved!")
        # Add DB code to save rating if required

    st.divider()
    if st.button("Take AI-Generated Quiz", type="primary"):
        st.session_state.session_step = "quiz"
        st.rerun()
    if st.button("Return to Dashboard"):
        reset_matchmaking()

def show_quiz():
    st.header("Quick Quiz")
    
    if not st.session_state.quiz_data:
        with st.spinner("Generating quiz based on your session..."):
            history = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
            chat_blob = " ".join([m[0] for m in history])
            prompt = f"Create a 3-question MCQ based on: {chat_blob}. Return ONLY JSON: [{{'q': '..', 'options': ['..','..'], 'correct': '..'}}, ...]"
            raw = ask_ai(prompt)
            try:
                st.session_state.quiz_data = json.loads(raw.replace("```json", "").replace("```", ""))
            except:
                st.error("Could not generate quiz. Try again.")
                if st.button("Retry"): st.rerun()
                return

    score = 0
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            choice = st.radio(f"Question {i+1}: {q['q']}", q['options'])
            if choice == q['correct']: score += 1
        
        if st.form_submit_button("Check Results"):
            if score == 3:
                st.balloons()
                st.success("Perfect! 3/3 correct.")
            else:
                st.info(f"You got {score}/3 correct.")
            
    if st.button("Exit Quiz"):
        reset_matchmaking()

# =========================================================
# THE BRIDGE FUNCTION (MUST BE CALLED matchmaking_page)
# =========================================================
def matchmaking_page():
    ensure_state()
    sidebar_ai() # AI Sidebar persists across all steps
    
    step = st.session_state.session_step
    
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

# For direct testing
if __name__ == "__main__":
    matchmaking_page()
