import streamlit as st
import os
import time
from database import cursor, conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads/sessions"
MATCH_THRESHOLD = 30

# =========================================================
# LOAD USERS
# =========================================================
def load_profiles():
    cursor.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects, p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id = p.user_id
        WHERE p.status = 'waiting'
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

# =========================================================
# MATCH LOGIC
# =========================================================
def score(u1, u2):
    s = 0
    s += len(set(u1["weak"]) & set(u2["strong"])) * 25
    s += len(set(u2["weak"]) & set(u1["strong"])) * 25
    if u1["grade"] == u2["grade"]:
        s += 10
    if u1["time"] == u2["time"]:
        s += 10
    return s

def find_best(current, users):
    best, best_s = None, 0
    for u in users:
        if u["user_id"] == current["user_id"]:
            continue
        sc = score(current, u)
        if sc > best_s:
            best, best_s = u, sc
    return (best, best_s) if best_s >= MATCH_THRESHOLD else (None, 0)

# =========================================================
# CHAT + FILE HELPERS
# =========================================================
def load_msgs(mid):
    cursor.execute(
        "SELECT sender, message FROM messages WHERE match_id=? ORDER BY id",
        (mid,)
    )
    return cursor.fetchall()

def send_msg(mid, sender, message):
    cursor.execute(
        "INSERT INTO messages (match_id, sender, message) VALUES (?, ?, ?)",
        (mid, sender, message)
    )
    conn.commit()

def save_file(mid, uploader, file):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = f"{UPLOAD_DIR}/{mid}_{file.name}"
    with open(path, "wb") as out:
        out.write(file.getbuffer())

    cursor.execute("""
        INSERT INTO session_files (match_id, uploader, filename, filepath)
        VALUES (?, ?, ?, ?)
    """, (mid, uploader, file.name, path))
    conn.commit()

def load_files(mid):
    cursor.execute("""
        SELECT uploader, filename, filepath
        FROM session_files
        WHERE match_id=?
        ORDER BY uploaded_at
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

# =========================================================
# ⭐ RATING
# =========================================================
def show_rating_ui(match_id):

    st.subheader("⭐ Rate Your Session")

    if "rating" not in st.session_state:
        st.session_state.rating = 0

    cols = st.columns(5)
    for i in range(5):
        if cols[i].button(
            "⭐" if i < st.session_state.rating else "☆",
            key=f"rate_{i}"
        ):
            st.session_state.rating = i + 1

    if st.button("Submit Rating", use_container_width=True):
        if st.session_state.rating == 0:
            st.warning("Please select a rating.")
            return

        cursor.execute("""
            INSERT INTO session_ratings
            (match_id, rater_id, rater_name, rating)
            VALUES (?, ?, ?, ?)
        """, (
            match_id,
            st.session_state.user_id,
            st.session_state.user_name,
            st.session_state.rating
        ))
        conn.commit()

        st.session_state.show_summary = True

# =========================================================
# 🧾 SESSION SUMMARY
# =========================================================
def render_session_summary(match_id):

    messages = load_msgs(match_id)
    files = load_files(match_id)
    partner = st.session_state.partner

    duration_sec = int(time.time() - st.session_state.session_start_time)
    mins, secs = divmod(duration_sec, 60)

    st.markdown("## 🧾 Session Summary")

    c1, c2 = st.columns(2)
    c1.metric("Learning Partner", partner["name"])
    c2.metric("Compatibility Score", st.session_state.partner_score)

    st.write(f"⏱ **Duration:** {mins} min {secs} sec")
    st.write(f"💬 **Messages exchanged:** {len(messages)}")
    st.write(f"📂 **Files shared:** {len(files)}")
    st.write(f"⭐ **Your rating:** {st.session_state.rating}/5")

    st.divider()
    st.success("Would you like to practice what you learned?")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧠 Practice Now", use_container_width=True):
            st.session_state.show_practice = True

    with c2:
        if st.button("Skip for Now", use_container_width=True):
            reset_to_matchmaking()

# =========================================================
# 🧠 AI PRACTICE QUIZ
# =========================================================
def generate_quiz_from_chat(match_id):

    messages = load_msgs(match_id)
    if not messages:
        return "No discussion found to generate a quiz."

    chat_text = "\n".join([f"{s}: {m}" for s, m in messages])

    prompt = f"""
    Based on the following learning conversation, generate a short quiz
    with 3 multiple-choice questions.

    Format exactly like this:
    Q1. Question
    A) option
    B) option
    C) option
    D) option
    Answer: A

    Conversation:
    {chat_text}
    """

    return ask_ai(prompt)


def render_practice_quiz(match_id):

    st.markdown("## 🧠 Practice What You Learned")

    if not st.session_state.quiz_generated:
        st.session_state.quiz_content = generate_quiz_from_chat(match_id)
        st.session_state.quiz_generated = True

    st.markdown(st.session_state.quiz_content)

    if st.button("Finish Practice", use_container_width=True):
        reset_to_matchmaking()

# =========================================================
# 🔁 RESET
# =========================================================
def reset_to_matchmaking():
    for k in [
        "current_match_id",
        "partner",
        "partner_score",
        "session_ended",
        "celebrated",
        "rating",
        "show_summary",
        "show_practice",
        "quiz_generated",
        "quiz_content",
        "proposed_match",
        "proposed_score",
        "session_start_time"
    ]:
        st.session_state.pop(k, None)

    st.rerun()

# =========================================================
# PAGE
# =========================================================
def matchmaking_page():

    for k, v in {
        "celebrated": False,
        "session_ended": False,
        "partner": None,
        "partner_score": None,
        "current_match_id": None,
        "show_summary": False,
        "show_practice": False,
        "quiz_generated": False,
        "quiz_content": "",
        "session_start_time": None
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # -----------------------------------------------------
    # PROFILE
    # -----------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles WHERE user_id=?
    """, (st.session_state.user_id,))
    row = cursor.fetchone()

    if not row:
        st.warning("Please complete your profile first.")
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

    # =====================================================
    # 🤖 AI STUDY ASSISTANT
    # =====================================================
    st.markdown("### 🤖 AI Study Assistant")
    with st.form("ai_form"):
        q = st.text_input("Ask a concept or doubt")
        if st.form_submit_button("Ask") and q:
            st.success(ask_ai(q))

    st.divider()

    # =====================================================
    # MATCHMAKING
    # =====================================================
    if not st.session_state.current_match_id:

        if st.button("Find Best Match", use_container_width=True):
            m, s = find_best(user, load_profiles())
            if m:
                st.session_state.proposed_match = m
                st.session_state.proposed_score = s

        if st.session_state.get("proposed_match"):
            m = st.session_state.proposed_match
            st.markdown("### 🔍 Suggested Match")
            st.write(f"**Name:** {m['name']}")
            st.write(f"**Role:** {m['role']}")
            st.write(f"**Grade:** {m['grade']}")
            st.write(f"**Time Slot:** {m['time']}")
            st.write(f"**Compatibility Score:** {st.session_state.proposed_score}")

            if st.button("Confirm Match", use_container_width=True):
                session_id = f"{user['user_id']}-{m['user_id']}-{int(time.time())}"

                cursor.execute("""
                    UPDATE profiles
                    SET status='matched', match_id=?
                    WHERE user_id IN (?,?)
                """, (session_id, user["user_id"], m["user_id"]))
                conn.commit()

                st.session_state.current_match_id = session_id
                st.session_state.partner = m
                st.session_state.partner_score = st.session_state.proposed_score
                st.session_state.session_start_time = time.time()
                st.session_state.celebrated = False
                st.session_state.session_ended = False
                st.session_state.rating = 0

                st.rerun()

    else:
        match_id = st.session_state.current_match_id

        if not st.session_state.celebrated:
            st.success("🎉 You're matched! Welcome to your live session.")
            st.balloons()
            st.session_state.celebrated = True

        if not st.session_state.session_ended:
            if st.button("🔴 End Session", use_container_width=True):
                end_session(match_id)
                st.session_state.session_ended = True

        st.divider()

        # 💬 CHAT
        st.markdown("### 💬 Live Learning Room")
        for s, m in load_msgs(match_id):
            st.markdown(f"**{s}:** {m}")

        with st.form("chat_form"):
            msg = st.text_input("Type your message")
            if st.form_submit_button("Send") and msg:
                send_msg(match_id, user["name"], msg)
                st.rerun()

        # 📂 FILES
        st.divider()
        st.markdown("### 📂 Shared Resources")
        with st.form("file_form"):
            f = st.file_uploader("Upload file")
            if st.form_submit_button("Upload") and f:
                save_file(match_id, user["name"], f)
                st.rerun()

        for u, n, p in load_files(match_id):
            with open(p, "rb") as file:
                st.download_button(n, file, use_container_width=True)

        # ⭐ RATING → SUMMARY → PRACTICE
        if st.session_state.session_ended and not st.session_state.show_summary and not st.session_state.show_practice:
            show_rating_ui(match_id)

        if st.session_state.show_summary:
            render_session_summary(match_id)

        if st.session_state.show_practice:
            render_practice_quiz(match_id)
