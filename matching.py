import streamlit as st
import time
import os
import json
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# CSS & UI STYLING
# =========================================================
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 8px; font-weight: 600; }
    .chat-stage {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        height: 400px;
        overflow-y: auto;
        padding: 20px;
        margin-bottom: 10px;
    }
    .msg-box { padding: 10px 15px; border-radius: 15px; margin-bottom: 10px; max-width: 80%; }
    .my-msg { background-color: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
    .peer-msg { background-color: #e5e7eb; color: #1f2937; margin-right: auto; border-bottom-left-radius: 2px; }
    .stat-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #10b981; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# CORE LOGIC & STATE
# =========================================================
def ensure_state():
    defaults = {
        "chat_log": [], "last_ts": 0, "ai_history": [], 
        "current_match_id": None, "session_step": "discovery",
        "peer_info": None, "match_confirmed": False,
        "session_summary": "", "quiz_data": None
    }
    for key, val in defaults.items():
        if key not in st.session_state: st.session_state[key] = val

ensure_state()

def reset_to_start():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for key in ["current_match_id", "peer_info", "match_confirmed", "chat_log", "quiz_data"]:
        st.session_state[key] = None
    st.session_state.session_step = "discovery"
    st.rerun()

# =========================================================
# SIDEBAR AI ASSISTANT
# =========================================================
with st.sidebar:
    st.title("🤖 AI Study Buddy")
    st.caption("Available before, during, and after your session.")
    user_query = st.text_input("Ask AI anything...")
    if st.button("Ask Assistant"):
        if user_query:
            with st.spinner("Thinking..."):
                answer = ask_ai(f"Context: Student Study Session. Question: {user_query}")
                st.session_state.ai_history.append({"q": user_query, "a": answer})
    
    for item in reversed(st.session_state.ai_history):
        with st.expander(item['q'][:30] + "..."):
            st.write(item['a'])

# =========================================================
# STAGE 1: DISCOVERY & COMPATIBILITY
# =========================================================
def show_discovery():
    st.header("Find Your Study Partner")
    st.info("Our AI matches you based on subjects and learning goals.")
    
    if st.button("Search for Compatible Partner", type="primary"):
        # Logic: Find someone 'waiting' who isn't me
        peer = conn.execute("""
            SELECT p.user_id, a.name, p.bio, p.interests 
            FROM profiles p JOIN auth_users a ON a.id=p.user_id 
            WHERE p.status='waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()

        if peer:
            st.session_state.peer_info = {"id": peer[0], "name": peer[1], "bio": peer[2], "interests": peer[3]}
            # Generate a temporary match ID
            m_id = f"match_{min(st.session_state.user_id, peer[0])}_{max(st.session_state.user_id, peer[0])}"
            st.session_state.current_match_id = m_id
            st.session_state.session_step = "confirmation"
            st.rerun()
        else:
            st.warning("No active peers found. Waiting for someone to join...")
            conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()

# =========================================================
# STAGE 2: CONFIRMATION
# =========================================================
def show_confirmation():
    st.subheader("Match Found! 🎯")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Partner:** {st.session_state.peer_info['name']}")
        st.write(f"**Interests:** {st.session_state.peer_info['interests']}")
        st.caption(f"Bio: {st.session_state.peer_info['bio']}")
    
    with col2:
        # Mock Compatibility Score based on shared interest strings
        score = 85 # In real app, calculate via AI or string overlap
        st.markdown(f"<div class='stat-card'><h3>{score}%</h3>Compatibility Score</div>", unsafe_allow_html=True)

    if st.button("Confirm & Start Session", type="primary"):
        st.balloons()
        time.sleep(1)
        st.session_state.session_step = "live"
        st.rerun()
    
    if st.button("Decline"):
        reset_to_start()

# =========================================================
# STAGE 3: LIVE SESSION
# =========================================================
@st.fragment(run_every=3)
def live_chat_component():
    messages = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                            (st.session_state.current_match_id,)).fetchall()
    
    st.markdown('<div class="chat-stage">', unsafe_allow_html=True)
    for sender, msg in messages:
        cl = "my-msg" if sender == st.session_state.user_name else "peer-msg"
        st.markdown(f'<div class="msg-box {cl}"><b>{sender}</b><br>{msg}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.title("📖 Live Collaboration")
    
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("End Session", help="Summarize and close"):
            st.session_state.session_step = "summary"
            st.rerun()

    live_chat_component()

    with st.container():
        col_msg, col_file, col_btn = st.columns([3, 1, 1])
        with col_msg:
            txt = st.text_input("Message", label_visibility="collapsed", key="live_input")
        with col_file:
            uploaded = st.file_uploader("File", label_visibility="collapsed")
        with col_btn:
            if st.button("Send", type="primary"):
                if txt:
                    conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, txt, int(time.time())))
                    conn.commit()
                    st.rerun()

# =========================================================
# STAGE 4: SUMMARY & RATING
# =========================================================
def show_summary():
    st.header("Session Summary")
    
    # Generate AI Summary from chat history
    if not st.session_state.session_summary:
        history = conn.execute("SELECT sender, message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
        chat_text = " ".join([f"{m[0]}: {m[1]}" for m in history])
        with st.spinner("AI is summarizing your session..."):
            st.session_state.session_summary = ask_ai(f"Summarize this study session in 3 bullet points: {chat_text}")
    
    st.write(st.session_state.session_summary)
    
    st.divider()
    st.subheader("Rate your Mentor/Partner")
    rating = st.feedback("stars") # Streamlit native rating
    if st.button("Submit Rating"):
        st.success("Thank you! Rating stored.")
        # Store rating logic here (conn.execute...)

    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("Take AI Generated Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    if col2.button("Back to Matchmaking"):
        reset_to_start()

# =========================================================
# STAGE 5: AI QUIZ
# =========================================================
def show_quiz():
    st.header("Test Your Knowledge")
    
    if not st.session_state.quiz_data:
        history = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
        chat_text = " ".join([m[0] for m in history])
        prompt = f"Based on this chat: '{chat_text}', generate 3 multiple choice questions in JSON format: [{{'q': '...', 'options': ['a','b','c'], 'correct': 'a'}}, ...]"
        raw_quiz = ask_ai(prompt)
        try:
            # Simple cleaning in case AI adds markdown
            clean_json = raw_quiz.replace("```json", "").replace("```", "").strip()
            st.session_state.quiz_data = json.loads(clean_json)
        except:
            st.error("AI is having trouble generating questions. Try again!")
            if st.button("Retry"): st.rerun()
            return

    score = 0
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            ans = st.radio(f"Q{i+1}: {q['q']}", q['options'])
            if ans == q['correct']: score += 1
        
        if st.form_submit_button("Submit Answers"):
            if score == 3:
                st.balloons()
                st.success("Perfect Score! 3/3")
            else:
                st.info(f"You got {score}/3 correct.")
            
            if st.button("Finish"): reset_to_start()

# =========================================================
# MAIN ROUTER
# =========================================================
def main():
    step = st.session_state.session_step
    
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    main()
