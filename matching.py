import streamlit as st
import time
from database import cursor, conn
from ai_helper import ask_ai

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
        "just_matched": False,
        "partner_joined": False,
        "chat_log": [],
        "proposed_match": None,
        "proposed_score": None,
        "show_quiz": False,
        "quiz_raw": "",
        "quiz_answers": {},
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

def normalize_match(m):
    if not m:
        return None
    if isinstance(m, dict):
        return m
    if isinstance(m, (tuple, list)) and len(m) >= 5:
        return {
            "user_id": m[0],
            "name": m[1],
            "role": m[2],
            "grade": m[3],
            "time": m[4],
            "strong": (m[7] if len(m) > 7 else "").split(","),
            "weak": (m[6] if len(m) > 6 else "").split(","),
        }
    return None

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
          AND p.match_id IS NULL
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
def generate_summary(chat):
    prompt = "Summarize this study session in 5 bullet points:\n" + "\n".join(chat[-20:])
    return ask_ai(prompt)

def generate_quiz(chat):
    prompt = f"""
Create exactly 4 MCQ questions from this discussion.
FORMAT STRICTLY AS:
Q1: question
A) option
B) option
C) option
D) option
Answer: A
"""
    return ask_ai(prompt + "\n" + "\n".join(chat[-30:]))

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    init_state()
    update_last_seen()

    # ✅ ENSURE USER IS AVAILABLE FOR MATCHING
    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE user_id=? AND status!='matched'
    """, (st.session_state.user_id,))
    conn.commit()

    st.title("🤝 Study Matchmaking")

    # 🎈 MATCH CONFIRMATION BALLOONS
    if st.session_state.just_matched:
        st.balloons()
        st.session_state.just_matched = False

    # =====================================================
    # ACTIVE SESSION
    # =====================================================
    if st.session_state.current_match_id and not st.session_state.session_ended:
        st.success("✅ Session Active")

        # 🔔 Partner joined notification
        if not st.session_state.partner_joined:
            st.toast("🎉 Your study partner has joined!", icon="🔔")
            st.session_state.partner_joined = True

        st.subheader("💬 Study Chat")
        msg = st.text_input("Type a message")
        if st.button("Send") and msg:
            st.session_state.chat_log.append(msg)
            cursor.execute(
                "INSERT INTO messages(match_id, sender, message) VALUES (?,?,?)",
                (st.session_state.current_match_id, st.session_state.user_name, msg)
            )
            conn.commit()
            st.success("Message sent")

        st.divider()

        # 🛑 END SESSION
        if st.button("🛑 End Session", use_container_width=True):
            cursor.execute("""
                UPDATE profiles
                SET status='waiting', match_id=NULL
                WHERE match_id=?
            """, (st.session_state.current_match_id,))
            conn.commit()

            st.session_state.session_ended = True
            st.session_state.current_match_id = None
            st.rerun()
        return

    # =====================================================
    # POST SESSION
    # =====================================================
    if st.session_state.session_ended:
        st.subheader("📊 Session Summary")
        with st.spinner("Generating summary..."):
            summary = generate_summary(st.session_state.chat_log)
            st.info(summary)

        st.subheader("⭐ Rate Your Partner")
        rating = st.slider("Rating", 1, 5, 3)
        if st.button("Submit Rating"):
            cursor.execute(
                "INSERT INTO session_ratings(match_id, rater_id, rater_name, rating) VALUES (?,?,?,?)",
                (None, st.session_state.user_id, st.session_state.user_name, rating)
            )
            conn.commit()
            st.success("Thanks for rating! ⭐")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧠 Take AI Quiz"):
                st.session_state.quiz_raw = generate_quiz(st.session_state.chat_log)
                st.session_state.show_quiz = True

        with col2:
            if st.button("🔁 Back to Matchmaking"):
                st.session_state.session_ended = False
                st.session_state.chat_log.clear()
                st.session_state.show_quiz = False
                st.rerun()

        # ================= QUIZ =================
        if st.session_state.show_quiz:
            st.subheader("📝 AI Quiz")

            lines = st.session_state.quiz_raw.splitlines()
            correct_answers = {}
            q_no = 0

            for line in lines:
                if line.startswith("Answer"):
                    correct_answers[q_no] = line.split(":")[1].strip()

            q_no = 0
            for i, line in enumerate(lines):
                if line.startswith("Q"):
                    q_no += 1
                    st.markdown(f"**{line}**")
                    choice = st.radio(
                        f"Answer for Q{q_no}",
                        ["A", "B", "C", "D"],
                        key=f"quiz_{q_no}"
                    )
                    st.session_state.quiz_answers[q_no] = choice

            if st.button("Submit Quiz"):
                score = sum(
                    1 for q, a in st.session_state.quiz_answers.items()
                    if a == correct_answers.get(q)
                )

                if score == len(correct_answers):
                    st.balloons()
                    st.success("🎉 All answers correct!")
                else:
                    st.error("❌ Some answers were wrong. Try again!")

        return

    # =====================================================
    # MATCHMAKING
    # =====================================================
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

    if st.session_state.proposed_match:
        m = normalize_match(st.session_state.proposed_match)
        if not m:
            st.warning("Invalid match data. Please retry.")
            st.session_state.proposed_match = None
            return

        st.info(
            f"""
            **Name:** {m['name']}  
            **Role:** {m['role']}  
            **Grade:** {m['grade']}  
            **Compatibility:** {st.session_state.proposed_score}
            """
        )

        if st.button("✅ Confirm Match", use_container_width=True):
            sid = f"{min(int(user['user_id']), int(m['user_id']))}-{max(int(user['user_id']), int(m['user_id']))}-{now()}"

            cursor.execute("""
                UPDATE profiles
                SET status='matched', match_id=?
                WHERE user_id IN (?,?)
            """, (sid, user["user_id"], m["user_id"]))
            conn.commit()

            st.session_state.current_match_id = sid
            st.session_state.just_matched = True
            st.session_state.proposed_match = None
            st.rerun()
