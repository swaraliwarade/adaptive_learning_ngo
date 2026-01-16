import streamlit as st
import time
import os
import json
from database import conn
from ai_helper import ask_ai
from streamlit_lottie import st_lottie
import requests

# Ensure upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# ASSETS & UI
# =========================================================
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Lottie Assets
LOTTIE_SCAN = "https://assets5.lottiefiles.com/packages/lf20_6p8ov98e.json" # Scanning
LOTTIE_SUCCESS = "https://assets10.lottiefiles.com/packages/lf20_pqnfmone.json" # Success/Match

def inject_emerald_theme():
    st.markdown("""
        <style>
        .stApp { background-color: #f0fdf4; }
        .emerald-card {
            background: white !important;
            padding: 30px !important;
            border-radius: 20px !important;
            border-top: 10px solid #059669 !important;
            box-shadow: 0 10px 25px rgba(5, 150, 105, 0.1) !important;
            margin-bottom: 25px;
            color: #064e3b;
        }
        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            height: 3em;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #059669 !important;
            transform: scale(1.02);
        }
        .chat-scroll { background: #ecfdf5 !important; border: 1px solid #d1fae5 !important; border-radius: 12px; padding: 15px; height: 350px; overflow-y: auto; margin-bottom: 20px; }
        .bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 10px; max-width: 80%; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #064e3b; border: 1px solid #d1fae5; border-bottom-left-radius: 2px; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# CORE LOGIC
# =========================================================
def get_user_status(uid):
    res = conn.execute("SELECT status, accepted, match_id FROM profiles WHERE user_id=?", (uid,)).fetchone()
    if res: return res
    conn.execute("INSERT INTO profiles (user_id, status, accepted) VALUES (?, 'active', 0)", (uid,))
    conn.commit()
    return ('active', 0, None)

def generate_session_quiz():
    msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                       (st.session_state.current_match_id,)).fetchall()
    chat_transcript = "\n".join([f"{m[0]}: {m[1]}" for m in msgs])
    
    prompt = f"""
    Create a 3-question MCQ quiz based on this study session:
    {chat_transcript}
    Return ONLY a JSON array of objects:
    [{"question": "...", "options": ["A", "B", "C"], "answer": "A"}]
    """
    try:
        response = ask_ai(prompt)
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        return json.loads(response[json_start:json_end])
    except:
        return [{"question": "Did you discuss the lesson?", "options": ["Yes", "No"], "answer": "Yes"}]

# =========================================================
# PAGE MODULES
# =========================================================

def show_discovery():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Network Discovery")
    
    lottie_scan = load_lottieurl(LOTTIE_SCAN)
    if lottie_scan: st_lottie(lottie_scan, height=200)

    st.write("Scan the emerald network for compatible learning nodes.")
    
    if st.button("Initiate Scan"):
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
            st.info("System: Scanning... No active peers detected.")
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Link Request")
    
    lottie_success = load_lottieurl(LOTTIE_SUCCESS)
    if lottie_success: st_lottie(lottie_success, height=150)
    
    st.write(f"Establish a secure connection with **{st.session_state.peer_info['name']}**?")
    
    _, my_acc, _ = get_user_status(st.session_state.user_id)
    _, peer_acc, _ = get_user_status(st.session_state.peer_info['id'])

    if my_acc == 1 and peer_acc == 1:
        st.session_state.session_step = "live"
        st.rerun()
    elif my_acc == 1:
        st.info(f"Synchronizing... Waiting for {st.session_state.peer_info['name']}.")
        time.sleep(2)
        st.rerun()
    else:
        if st.button("Confirm Connection"):
            conn.execute("UPDATE profiles SET accepted=1 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.rerun()
        if st.button("Abort"):
            conn.execute("UPDATE profiles SET status='waiting', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.session_state.session_step = "discovery"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_live_session():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Live Node: {st.session_state.peer_info['name']}")
    
    msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                       (st.session_state.current_match_id,)).fetchall()
    
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for sender, msg in msgs:
        cls = "bubble-me" if sender == st.session_state.user_name else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    msg = st.text_input("Input Data", placeholder="Enter message...", key="chat_input", label_visibility="collapsed")
    if st.button("Transmit Data"):
        if msg:
            conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                        (st.session_state.current_match_id, st.session_state.user_name, msg, int(time.time())))
            conn.commit()
            st.rerun()

    st.divider()
    if st.button("Terminate Session"):
        st.session_state.session_step = "rating"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_rating():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Evaluation")
    st.write(f"Rate the collaboration quality of {st.session_state.peer_info['name']}")
    
    rating = st.select_slider("Performance Rating", options=[1, 2, 3, 4, 5], value=5)
    feedback = st.text_area("Observations")
    
    if st.button("Submit Report"):
        conn.execute("INSERT INTO session_ratings (match_id, rater_id, rating, feedback) VALUES (?,?,?,?)",
                    (st.session_state.current_match_id, st.session_state.user_id, rating, feedback))
        conn.commit()
        with st.spinner("Compiling Knowledge Check..."):
            st.session_state.quiz_data = generate_session_quiz()
        st.session_state.session_step = "quiz"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Verification")
    
    quiz = st.session_state.get('quiz_data', [])
    
    with st.form("quiz_form"):
        user_answers = []
        for i, q in enumerate(quiz):
            st.write(f"**Question {i+1}: {q['question']}**")
            ans = st.radio("Options", q['options'], key=f"q_{i}", label_visibility="collapsed")
            user_answers.append(ans)
        
        if st.form_submit_button("Submit Verification"):
            score = sum(1 for i, q in enumerate(quiz) if user_answers[i] == q['answer'])
            st.success(f"Verification Score: {score}/{len(quiz)}")
            st.session_state.quiz_done = True

    if st.session_state.get('quiz_done'):
        if st.button("Re-enter Discovery Mode"):
            conn.execute("UPDATE profiles SET status='active', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.session_state.session_step = "discovery"
            del st.session_state.quiz_done
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN ROUTER
# =========================================================
def matchmaking_page():
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"
    
    # Background Listener logic integrated
    uid = st.session_state.user_id
    db_status, _, db_match_id = get_user_status(uid)
    if db_status == 'confirming' and st.session_state.session_step == "discovery":
        peer = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id = p.user_id WHERE p.match_id=? AND p.user_id!=?", (db_match_id, uid)).fetchone()
        if peer:
            st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
            st.session_state.current_match_id = db_match_id
            st.session_state.session_step = "confirmation"
            st.rerun()

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "rating": show_rating()
    elif step == "quiz": show_quiz()
