import streamlit as st
import os
import time
from database import cursor, conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads/sessions"

# =========================================================
# SAFETY: ENSURE RATINGS TABLE EXISTS
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT,
    rater_id INTEGER,
    rating INTEGER,
    created_at INTEGER
)
""")
conn.commit()

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def online_status(last_seen):
    if not last_seen:
        return "🔴 Not joined yet"
    diff = now() - last_seen
    if diff < 60:
        return "🟢 Online"
    if diff < 300:
        return "🟡 Recently active"
    return "🔴 Offline"

# =========================================================
# PRESENCE
# =========================================================
def update_last_seen():
    cursor.execute(
        "UPDATE profiles SET last_seen=? WHERE user_id=?",
        (now(), st.session_state.user_id)
    )
    conn.commit()

# =========================================================
# CHAT
# =========================================================
def load_msgs(mid):
    cursor.execute(
        "SELECT sender, message FROM messages WHERE match_id=? ORDER BY id",
        (mid,))
    return cursor.fetchall()

def send_msg(mid, sender, message):
    cursor.execute(
        "INSERT INTO messages (match_id, sender, message) VALUES (?,?,?)",
        (mid, sender, message))
    conn.commit()
    update_last_seen()

# =========================================================
# FILES
# =========================================================
def save_file(mid, uploader, file):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = f"{UPLOAD_DIR}/{mid}_{file.name}"
    with open(path, "wb") as f:
        f.write(file.getbuffer())

    cursor.execute("""
        INSERT INTO session_files (match_id, uploader, filename, filepath)
        VALUES (?,?,?,?)
    """, (mid, uploader, file.name, path))
    conn.commit()

def load_files(mid):
    cursor.execute("""
        SELECT uploader, filename, filepath
        FROM session_files WHERE match_id=?
    """, (mid,))
    return cursor.fetchall()

# =========================================================
# END SESSION
# =========================================================
def end_session(match_id):
    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE match_id=?
    """, (match_id,))
    conn.commit()
    st.session_state.session_ended = True

# =========================================================
# AI QUIZ
# =========================================================
def generate_quiz_from_chat(match_id):
    msgs = load_msgs(match_id)
    discussion = "\n".join([f"{s}: {m}" for s, m in msgs])

    prompt = f"""
Create EXACTLY 3 MCQs from this discussion.
If short, make simple questions.

Discussion:
{discussion}
"""
    raw = ask_ai(prompt)

    qs = []
    for b in raw.split("Q")[1:]:
        lines = b.splitlines()
        q = lines[0].split(".", 1)[-1]
        opts, ans = {}, None
        for l in lines:
            if l[:2] in ["A)", "B)", "C)", "D)"]:
                opts[l[0]] = l[2:].strip()
            if "Answer:" in l:
                ans = l.split(":")[-1].strip()
        if len(opts) == 4 and ans:
            qs.append({"question": q, "options": opts, "answer": ans})
    return qs[:3]

def render_practice_quiz(match_id):
    st.subheader("🧠 Practice Quiz")

    if "quiz" not in st.session_state:
        st.session_state.quiz = generate_quiz_from_chat(match_id)
        st.session_state.answers = {}

    for i, q in enumerate(st.session_state.quiz):
        st.markdown(f"**Q{i+1}. {q['question']}**")
        st.session_state.answers[i] = st.radio(
            "Choose",
            list(q["options"].keys()),
            format_func=lambda x: f"{x}) {q['options'][x]}",
            key=f"q{i}"
        )

    if st.button("Submit Quiz"):
        score = sum(
            1 for i, q in enumerate(st.session_state.quiz)
            if st.session_state.answers.get(i) == q["answer"]
        )
        st.metric("Score", f"{score}/3")
        if score == 3:
            st.balloons()

# =========================================================
# SESSION SUMMARY (NEW)
# =========================================================
def render_session_summary(match_id):
    msgs = load_msgs(match_id)
    discussion = "\n".join([f"{s}: {m}" for s, m in msgs])

    prompt = f"""
Summarize this study session:
- Topics discussed
- What was learned
- Suggestions for improvement

Discussion:
{discussion}
"""
    summary = ask_ai(prompt)
    st.subheader("📝 Session Summary")
    st.write(summary)

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    update_last_seen()

    st.session_state.setdefault("current_match_id", None)
    st.session_state.setdefault("session_ended", False)
    st.session_state.setdefault("just_matched", False)

    if st.session_state.just_matched:
        st.balloons()
        st.session_state.just_matched = False

    # ================= AI CHATBOT =================
    st.markdown("### 🤖 AI Study Assistant")
    with st.form("ai"):
        q = st.text_input("Ask AI")
        if st.form_submit_button("Ask") and q:
            st.success(ask_ai(q))

    st.divider()

    # ================= LIVE SESSION =================
    if st.session_state.current_match_id and not st.session_state.session_ended:
        mid = st.session_state.current_match_id

        st.subheader("💬 Chat")
        for s, m in load_msgs(mid):
            st.markdown(f"**{s}:** {m}")

        with st.form("chat"):
            msg = st.text_input("Message")
            if st.form_submit_button("Send") and msg:
                send_msg(mid, st.session_state.user_name, msg)
                st.rerun()

        st.subheader("📁 Files")
        f = st.file_uploader("Upload")
        if f and st.button("Upload file"):
            save_file(mid, st.session_state.user_name, f)
            st.rerun()

        for u, n, p in load_files(mid):
            with open(p, "rb") as file:
                st.download_button(f"{n} ({u})", file)

        if st.button("End Session", use_container_width=True):
            end_session(mid)
        return

    # ================= POST SESSION =================
    if st.session_state.session_ended:
        st.subheader("⭐ Rate your partner")

        stars = {
            "⭐": 1,
            "⭐⭐": 2,
            "⭐⭐⭐": 3,
            "⭐⭐⭐⭐": 4,
            "⭐⭐⭐⭐⭐": 5
        }

        choice = st.radio("Your rating", list(stars.keys()), horizontal=True)

        if st.button("Submit Rating"):
            cursor.execute("""
                INSERT INTO ratings (match_id, rater_id, rating, created_at)
                VALUES (?,?,?,?)
            """, (
                st.session_state.current_match_id,
                st.session_state.user_id,
                stars[choice],
                now()
            ))
            conn.commit()
            st.success("⭐ Rating submitted")

            render_session_summary(st.session_state.current_match_id)

            if st.button("Practice on this topic"):
                render_practice_quiz(st.session_state.current_match_id)
