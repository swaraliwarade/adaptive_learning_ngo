import streamlit as st
import time
import os
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

POLL_INTERVAL = 3

# =========================================================
# HELPERS & STATE
# =========================================================
def now():
    return int(time.time())

def init_state():
    defaults = {
        "current_match_id": None,
        "confirmed": False,
        "session_ended": False,
        "chat_log": [],
        "last_msg_ts": 0,
        "last_poll": 0,
        "summary": None,
        "quiz": None,
        "rating_given": False,
        "ai_chat": [],
        "proposed_match": None,
        "proposed_score": None,
        "quiz_score": 0
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def reset_matchmaking():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for k in ["current_match_id", "confirmed", "session_ended", "chat_log", "last_msg_ts", 
              "summary", "quiz", "rating_given", "proposed_match"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

# =========================================================
# UI STYLING
# =========================================================
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .chat-bubble-user { background-color: #e9ecef; padding: 10px; border-radius: 10px; margin-bottom: 5px; }
    .chat-bubble-match { background-color: #007bff; color: white; padding: 10px; border-radius: 10px; margin-bottom: 5px; }
    .ai-box { border-left: 5px solid #6c757d; padding: 15px; background-color: #ffffff; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# COMPONENTS
# =========================================================
def ai_assistant_panel():
    with st.sidebar:
        st.markdown("### AI Study Assistant")
        with st.container():
            q = st.text_input("Ask assistant anything...", key="ai_input", placeholder="Explain a concept...")
            if st.button("Query AI") and q:
                ans = ask_ai(q)
                st.session_state.ai_chat.insert(0, (q, ans))
            
            for q_h, a_h in st.session_state.ai_chat[:3]:
                st.markdown(f"**Q:** {q_h}")
                st.markdown(f"**A:** {a_h}")
                st.divider()

def live_chat_component(match_id):
    # Polling Logic
    if now() - st.session_state.last_poll > POLL_INTERVAL:
        rows = conn.execute("""
            SELECT sender, message, created_ts FROM messages 
            WHERE match_id=? AND created_ts > ? ORDER BY created_ts
        """, (match_id, st.session_state.last_msg_ts)).fetchall()
        if rows:
            for s, m, ts in rows:
                st.session_state.chat_log.append((s, m))
                st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)
            st.session_state.last_poll = now()
            st.rerun()

    # Chat UI
    st.markdown("### Session Chat")
    chat_box = st.container(height=400)
    for sender, msg in st.session_state.chat_log:
        if sender == st.session_state.user_name:
            chat_box.markdown(f"<div class='chat-bubble-user'><b>You:</b> {msg}</div>", unsafe_allow_html=True)
        else:
            chat_box.markdown(f"<div class='chat-bubble-match'><b>{sender}:</b> {msg}</div>", unsafe_allow_html=True)

    with st.form("chat_input", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        msg = col1.text_input("Message", label_visibility="collapsed")
        if col2.form_submit_button("Send") and msg:
            conn.execute("INSERT INTO messages(match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                         (match_id, st.session_state.user_name, msg, now()))
            conn.commit()
            st.rerun()

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    if not st.session_state.get("user_id"):
        st.error("Authentication required.")
        st.stop()
    
    init_state()
    ai_assistant_panel()

    # PHASE 1: FINDING A MATCH
    if not st.session_state.current_match_id:
        st.header("Matchmaking Lobby")
        
        # Logic to fetch user profile for matching (Assuming helper logic from original)
        r = conn.execute("SELECT grade, strong_subjects, weak_subjects FROM profiles WHERE user_id=?", 
                         (st.session_state.user_id,)).fetchone()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.info("System is ready to find compatible partners based on your profile.")
            if st.button("Initialize Search"):
                # Simplified matching trigger for code structure
                best, score = find_best_match_logic(r) # logic from original script
                if best:
                    st.session_state.proposed_match = best
                    st.session_state.proposed_score = score
                else:
                    st.warning("No compatible peers found at this time.")

        if st.session_state.proposed_match:
            st.divider()
            u = st.session_state.proposed_match
            with st.container(border=True):
                st.subheader(f"Proposed Match: {u['name']}")
                st.write(f"Match Confidence: {st.session_state.proposed_score}")
                st.write(f"Grade: {u['grade']}")
                if st.button("Confirm Match and Start Session"):
                    mid = f"match_{st.session_state.user_id}_{u['user_id']}_{now()}"
                    conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id IN (?,?)",
                                 (mid, st.session_state.user_id, u["user_id"]))
                    conn.execute("INSERT INTO sessions(match_id, user1_id, user2_id, started_at) VALUES (?,?,?,?)",
                                 (mid, st.session_state.user_id, u["user_id"], now()))
                    conn.commit()
                    st.session_state.current_match_id = mid
                    st.balloons()
                    st.rerun()

    # PHASE 2: LIVE SESSION
    elif st.session_state.current_match_id and not st.session_state.session_ended:
        st.header("Active Study Session")
        
        tab1, tab2 = st.tabs(["Collaboration Hub", "Resource Management"])
        
        with tab1:
            live_chat_component(st.session_state.current_match_id)
        
        with tab2:
            st.write("### File Sharing")
            uploaded_file = st.file_uploader("Upload study materials", label_visibility="collapsed")
            if uploaded_file:
                path = os.path.join(UPLOAD_DIR, f"{st.session_state.current_match_id}_{uploaded_file.name}")
                with open(path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("File synchronized with partner.")
            
            st.divider()
            if st.button("Finalize and End Session", type="secondary"):
                chat_text = "\n".join([m for _, m in st.session_state.chat_log])
                st.session_state.summary = ask_ai("Summarize session in 5 bullets: " + chat_text)
                st.session_state.quiz = ask_ai("Create 3 MCQ's from this text. Format: Q, A, B, C. " + chat_text)
                conn.execute("UPDATE sessions SET ended_at=? WHERE match_id=?", (now(), st.session_state.current_match_id))
                conn.commit()
                st.session_state.session_ended = True
                st.rerun()

    # PHASE 3: POST-SESSION & QUIZ
    else:
        st.header("Session Summary & Assessment")
        
        with st.expander("View AI Summary", expanded=True):
            st.write(st.session_state.summary)

        if not st.session_state.rating_given:
            st.write("### Rate Mentor Performance")
            rating = st.feedback("stars") # Streamlit native star rating (v1.30+)
            if rating is not None:
                conn.execute("INSERT INTO session_ratings(match_id, rater_id, rating) VALUES (?,?,?)",
                             (st.session_state.current_match_id, st.session_state.user_id, rating + 1))
                conn.commit()
                st.session_state.rating_given = True
                st.success("Feedback submitted.")

        st.divider()
        st.write("### AI-Generated Knowledge Check")
        st.text_area("Questions", st.session_state.quiz, height=200, disabled=True)
        
        ans = st.number_input("How many questions did you answer correctly?", min_value=0, max_value=3, step=1)
        if st.button("Submit Quiz Results"):
            if ans == 3:
                st.balloons()
                st.success("Perfect Score! Mastery achieved.")
            else:
                st.info(f"You got {ans}/3 correct. Keep studying!")

        if st.button("Return to Matchmaking"):
            reset_matchmaking()

# Place-holder for the match logic within the new UI structure
def find_best_match_logic(current_r):
    # Logic from your original compatibility/find_best_match function
    rows = conn.execute("SELECT a.id, a.name, p.grade, p.strong_subjects, p.weak_subjects FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.user_id != ? AND p.status='waiting'", (st.session_state.user_id,)).fetchall()
    # Simplified return for brevity - keep your existing compatibility logic here
    if rows:
        r = rows[0]
        return {"user_id": r[0], "name": r[1], "grade": r[2]}, 95
    return None, 0

matchmaking_page()
