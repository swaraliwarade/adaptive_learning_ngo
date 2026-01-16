import streamlit as st
import time
from database import cursor, conn
from ai_helper import ask_ai

SESSION_TIMEOUT_SEC = 60 * 60
POLL_INTERVAL_SEC = 3

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
        "session_start_time": None,
        "session_ended": False,
        "chat_log": [],
        "last_msg_ts": 0,
        "last_poll": 0,
        "proposal": None,
        "confirmed": False,
        "ai_chat": [],
        "summary": None,
        "show_quiz": False,
        "quiz": None,
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

# =========================================================
# MATCHING
# =========================================================
def load_waiting_profiles():
    cursor.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects
        FROM profiles p
        JOIN auth_users a ON a.id=p.user_id
        WHERE p.status='waiting'
          AND p.match_id IS NULL
          AND p.user_id!=?
    """, (st.session_state.user_id,))
    rows = cursor.fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r[0],
            "name": r[1],
            "role": r[2],
            "grade": r[3],
            "time": r[4],
            "strong": (r[5] or "").split(","),
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
        sc = score(current, u)
        if sc > best_score:
            best, best_score = u, sc
    return best, best_score

# =========================================================
# LIVE CHAT
# =========================================================
def fetch_new_messages(match_id):
    cursor.execute("""
        SELECT sender, message, created_ts
        FROM messages
        WHERE match_id=?
          AND created_ts>?
        ORDER BY created_ts
    """, (match_id, st.session_state.last_msg_ts))
    rows = cursor.fetchall()

    for s, m, ts in rows:
        st.session_state.chat_log.append((s, m))
        st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)

# =========================================================
# AI HELPERS
# =========================================================
def ai_chat_ui():
    st.subheader("🤖 AI Study Assistant")
    q = st.text_input("Ask anything")
    if st.button("Ask AI") and q:
        ans = ask_ai(q)
        st.session_state.ai_chat.append((q, ans))

    for q, a in st.session_state.ai_chat[-5:]:
        st.markdown(f"**You:** {q}")
        st.markdown(f"**AI:** {a}")

def generate_summary(chat):
    return ask_ai(
        "Summarize this study session in 5 bullet points:\n" +
        "\n".join([m for _, m in chat][-30:])
    )

def generate_quiz(chat):
    return ask_ai("""
Create exactly 3 MCQ questions from this discussion.
FORMAT STRICTLY:
Q1: question
A) option
B) option
C) option
D) option
Answer: A
""" + "\n" + "\n".join([m for _, m in chat][-30:]))

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    init_state()
    update_last_seen()

    st.title("🤝 Study Matchmaking")

    ai_chat_ui()

    # -----------------------------------------------------
    # FIND MATCH
    # -----------------------------------------------------
    if not st.session_state.confirmed:
        cursor.execute("""
            SELECT role, grade, time, strong_subjects, weak_subjects
            FROM profiles WHERE user_id=?
        """, (st.session_state.user_id,))
        r = cursor.fetchone()
        current = {
            "user_id": st.session_state.user_id,
            "role": r[0],
            "grade": r[1],
            "time": r[2],
            "strong": (r[3] or "").split(","),
            "weak": (r[4] or "").split(","),
        }

        best, sc = find_best_match(current)

        if best:
            st.subheader("✨ Suggested Match")
            st.write(f"**Name:** {best['name']}")
            st.write(f"**Role:** {best['role']}")
            st.write(f"**Grade:** {best['grade']}")
            st.write(f"**Compatibility:** {sc}%")

            if st.button("Confirm Match"):
                match_id = f"{st.session_state.user_id}_{best['user_id']}_{now()}"

                cursor.execute("""
                    UPDATE profiles
                    SET status='matched', match_id=?
                    WHERE user_id IN (?,?)
                """, (match_id, st.session_state.user_id, best["user_id"]))

                cursor.execute("""
                    INSERT INTO sessions(match_id, user1_id, user2_id, started_at)
                    VALUES (?,?,?,?)
                """, (match_id, st.session_state.user_id, best["user_id"], now()))

                conn.commit()
                st.session_state.current_match_id = match_id
                st.session_state.session_start_time = now()
                st.session_state.confirmed = True
                st.balloons()
                st.rerun()

        else:
            st.info("Waiting for compatible users...")

        return

    # -----------------------------------------------------
    # ACTIVE SESSION
    # -----------------------------------------------------
    fetch_new_messages(st.session_state.current_match_id)

    st.subheader("💬 Live Study Chat")
    for s, m in st.session_state.chat_log[-50:]:
        st.markdown(f"**{s}:** {m}")

    msg = st.text_input("Message")
    if st.button("Send") and msg:
        cursor.execute(
            "INSERT INTO messages(match_id, sender, message, created_ts) VALUES (?,?,?,?)",
            (st.session_state.current_match_id, st.session_state.user_name, msg, now())
        )
        conn.commit()
        st.rerun()

    # -----------------------------------------------------
    # FILE UPLOAD
    # -----------------------------------------------------
    st.subheader("📎 Share Files")
    f = st.file_uploader("Upload")
    if f:
        path = f"uploads/{st.session_state.current_match_id}_{f.name}"
        with open(path, "wb") as out:
            out.write(f.read())

        cursor.execute("""
            INSERT INTO session_files(match_id, uploader, filename, filepath)
            VALUES (?,?,?,?)
        """, (st.session_state.current_match_id, st.session_state.user_name, f.name, path))
        conn.commit()
        st.success("File uploaded")

    # -----------------------------------------------------
    # END SESSION
    # -----------------------------------------------------
    if st.button("End Session"):
        cursor.execute("""
            UPDATE sessions
            SET ended_at=?
            WHERE match_id=?
        """, (now(), st.session_state.current_match_id))
        conn.commit()

        st.session_state.session_ended = True
        st.session_state.summary = generate_summary(st.session_state.chat_log)
        st.rerun()

    # -----------------------------------------------------
    # POST SESSION
    # -----------------------------------------------------
    if st.session_state.session_ended:
        st.subheader("📝 Session Summary")
        st.write(st.session_state.summary)

        rating = st.slider("⭐ Rate your mentor", 1, 5)
        if st.button("Submit Rating"):
            cursor.execute("""
                INSERT INTO session_ratings(match_id, rater_id, rater_name, rating)
                VALUES (?,?,?,?)
            """, (
                st.session_state.current_match_id,
                st.session_state.user_id,
                st.session_state.user_name,
                rating
            ))
            conn.commit()
            st.success("Rating saved")

        if st.button("Take Quiz"):
            st.session_state.quiz = generate_quiz(st.session_state.chat_log)
            st.session_state.show_quiz = True
            st.rerun()

        if st.session_state.show_quiz:
            st.subheader("🧠 Quiz")
            st.text(st.session_state.quiz)
            if st.button("Finish Quiz"):
                st.balloons()
