import streamlit as st
import time
from database import cursor, conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads/sessions"

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def init_state():
    defaults = {
        "user_id": None,
        "user_name": "",
        "current_match_id": None,
        "session_ended": False,
        "last_session_id": None,
        "selected_rating": 0,
        "just_matched": False,
        "partner_joined": False,
        "chat_log": [],
        "quiz_data": None,
        "quiz_answers": {},
        "show_quiz": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def update_last_seen():
    if st.session_state.user_id:
        cursor.execute(
            "UPDATE profiles SET last_seen=? WHERE user_id=?",
            (now(), st.session_state.user_id)
        )
        conn.commit()

# =========================================================
# MATCHING LOGIC
# =========================================================
def load_waiting_profiles():
    cursor.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects, p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id=p.user_id
        WHERE p.status='waiting'
    """)
    rows = cursor.fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r[0],
            "name": r[1],
            "role": r[2],
            "grade": r[3],
            "time": r[4],
            "strong": (r[7] or r[5] or "").split(","),
            "weak": (r[6] or "").split(",")
        })
    return users

def score(u1, u2):
    s = 0
    s += len(set(u1["weak"]) & set(u2["strong"])) * 25
    s += len(set(u2["weak"]) & set(u1["strong"])) * 25
    if u1["grade"] == u2["grade"]:
        s += 10
    if u1["time"] == u2["time"]:
        s += 10
    return s

def find_best_match(current):
    best, best_score = None, -1
    for u in load_waiting_profiles():
        if u["user_id"] == current["user_id"]:
            continue
        sc = score(current, u)
        if sc > best_score:
            best, best_score = u, sc
    return best, best_score

# =========================================================
# AI FEATURES
# =========================================================
def generate_session_summary():
    chat = "\n".join(st.session_state.chat_log[-20:])
    prompt = f"Summarize this study session in 5 bullet points:\n{chat}"
    return ask_ai(prompt)

def generate_quiz():
    chat = "\n".join(st.session_state.chat_log[-30:])
    prompt = f"""
    Create a 4-question MCQ quiz based on this discussion.
    Format EXACTLY like:
    Q1: question
    A) option
    B) option
    C) option
    D) option
    Answer: B
    """
    return ask_ai(prompt)

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    init_state()
    update_last_seen()

    # 🎈 MATCH CONFIRMATION BALLOONS
    if st.session_state.just_matched:
        st.balloons()
        st.session_state.just_matched = False

    st.title("🤝 Study Matchmaking")

    # ================= ACTIVE SESSION =================
    if st.session_state.current_match_id and not st.session_state.session_ended:
        st.success("✅ Session Active")

        # 🔔 Partner joined notification
        if not st.session_state.partner_joined:
            st.toast("🎉 Your study partner has joined!", icon="🔔")
            st.session_state.partner_joined = True

        st.markdown("### 💬 Study Chat")
        msg = st.text_input("Type message")
        if st.button("Send") and msg:
            st.session_state.chat_log.append(msg)
            st.success("Message sent")

        st.divider()

        # 🔴 END SESSION
        if st.button("🛑 End Session", use_container_width=True):
            st.session_state.session_ended = True
            st.session_state.last_session_id = st.session_state.current_match_id
            st.session_state.current_match_id = None
            st.rerun()

        return

    # ================= POST SESSION =================
    if st.session_state.session_ended:
        st.subheader("📊 Session Summary")
        with st.spinner("Generating summary..."):
            st.info(generate_session_summary())

        st.subheader("⭐ Rate Your Partner")
        rating = st.slider("Rating", 1, 5, 3)
        if st.button("Submit Rating"):
            st.success("Thanks for your feedback! ⭐")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Take AI Quiz"):
                st.session_state.quiz_data = generate_quiz()
                st.session_state.show_quiz = True

        with col2:
            if st.button("🔁 Back to Matchmaking"):
                st.session_state.session_ended = False
                st.session_state.chat_log = []
                st.rerun()

        # ================= QUIZ =================
        if st.session_state.show_quiz and st.session_state.quiz_data:
            st.subheader("🧠 AI Quiz")
            raw = st.session_state.quiz_data.split("\n")
            correct = 0
            q_no = 0
            correct_answers = {}

            for line in raw:
                if line.startswith("Answer"):
                    correct_answers[q_no] = line.split(":")[-1].strip()

            q_no = 0
            for i, line in enumerate(raw):
                if line.startswith("Q"):
                    q_no += 1
                    st.markdown(f"**{line}**")
                    opts = raw[i+1:i+5]
                    choice = st.radio(
                        f"Q{q_no}",
                        ["A", "B", "C", "D"],
                        key=f"q{q_no}"
                    )
                    st.session_state.quiz_answers[q_no] = choice

            if st.button("Submit Quiz"):
                for q, ans in st.session_state.quiz_answers.items():
                    if ans == correct_answers.get(q):
                        correct += 1

                if correct == len(correct_answers):
                    st.balloons()
                    st.success("🎉 All answers correct!")
                else:
                    st.error("❌ Some answers were incorrect. Try again!")

        return

    # ================= MATCHMAKING =================
    st.subheader("🔍 Find a Study Partner")

    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles WHERE user_id=?
    """, (st.session_state.user_id,))
    row = cursor.fetchone()

    if not row:
        st.warning("Complete your profile first.")
        return

    role, grade, time_slot, strong, weak, teaches = row
    user = {
        "user_id": st.session_state.user_id,
        "name": st.session_state.user_name,
        "role": role,
        "grade": grade,
        "time": time_slot,
        "strong": (teaches or strong or "").split(","),
        "weak": (weak or "").split(",")
    }

    if st.button("🔍 Find Best Match", use_container_width=True):
        m, s = find_best_match(user)
        if not m:
            st.info("No suitable match right now.")
            return

        st.session_state.proposed_match = m
        st.session_state.proposed_score = s

    if "proposed_match" in st.session_state:
        m = st.session_state.proposed_match
        st.info(
            f"""
            **Name:** {m['name']}  
            **Role:** {m['role']}  
            **Grade:** {m['grade']}  
            **Compatibility:** {st.session_state.proposed_score}
            """
        )

        if st.button("✅ Confirm Match", use_container_width=True):
            sid = f"{min(user['user_id'], m['user_id'])}-{max(user['user_id'], m['user_id'])}-{now()}"
            cursor.execute("""
                UPDATE profiles SET status='matched', match_id=?
                WHERE user_id IN (?,?)
            """, (sid, user["user_id"], m["user_id"]))
            conn.commit()

            st.session_state.current_match_id = sid
            st.session_state.just_matched = True
            st.rerun()
