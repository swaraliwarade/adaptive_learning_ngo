import streamlit as st
import time
import os
import random
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

POLL_INTERVAL = 3  # seconds

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def require_login():
    if not st.session_state.get("user_id"):
        st.stop()

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
        "refresh_key": 0,
        "proposed_match": None,
        "proposed_score": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def should_poll():
    return now() - st.session_state.last_poll >= POLL_INTERVAL

def poll():
    st.session_state.last_poll = now()
    st.rerun()

def reset_matchmaking():
    conn.execute(
        "UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?",
        (st.session_state.user_id,)
    )
    conn.commit()

    for k in list(st.session_state.keys()):
        if k not in ["user_id", "user_name", "logged_in", "page"]:
            del st.session_state[k]

    st.rerun()

# =========================================================
# AI CHATBOT
# =========================================================
def ai_chat_ui():
    st.subheader("AI Assistant")
    q = st.text_input("Ask the assistant", key="ai_q")
    if st.button("Send to AI") and q:
        st.session_state.ai_chat.append((q, ask_ai(q)))

    for q, a in st.session_state.ai_chat[-5:]:
        st.markdown(f"**You:** {q}")
        st.markdown(f"**AI:** {a}")

# =========================================================
# MATCHING
# =========================================================
def load_waiting_profiles():
    rows = conn.execute("""
        SELECT a.id, a.name, p.grade, p.time,
               p.strong_subjects, p.weak_subjects
        FROM profiles p
        JOIN auth_users a ON a.id=p.user_id
        WHERE p.user_id!=?
          AND p.status='waiting'
          AND p.match_id IS NULL
    """, (st.session_state.user_id,)).fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r[0],
            "name": r[1],
            "grade": r[2],
            "time": r[3],
            "strong": (r[4] or "").split(","),
            "weak": (r[5] or "").split(","),
        })
    return users

def compatibility(a, b):
    s = 0
    s += len(set(a["weak"]) & set(b["strong"])) * 25
    s += len(set(b["weak"]) & set(a["strong"])) * 25
    if a["grade"] == b["grade"]:
        s += 10
    if a["time"] == b["time"]:
        s += 10
    s += random.randint(0, 5)
    return s

def find_best_match(current):
    best, best_score = None, -1
    for u in load_waiting_profiles():
        sc = compatibility(current, u)
        if sc > best_score:
            best, best_score = u, sc
    return best, best_score

# =========================================================
# CHAT
# =========================================================
def fetch_messages(match_id):
    rows = conn.execute("""
        SELECT sender, message, COALESCE(created_ts,0)
        FROM messages
        WHERE match_id=? AND COALESCE(created_ts,0) > ?
        ORDER BY created_ts
    """, (match_id, st.session_state.last_msg_ts)).fetchall()

    for s, m, ts in rows:
        st.session_state.chat_log.append((s, m))
        st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)

# =========================================================
# STAR RATING
# =========================================================
def star_rating():
    st.write("Rate your mentor")
    cols = st.columns(5)
    for i in range(5):
        if cols[i].button("★", key=f"star_{i}"):
            return i + 1
    return None

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    require_login()
    init_state()

    st.markdown("## Study Matchmaking")

    ai_chat_ui()
    st.divider()

    # ================= MATCH SEARCH =================
    if not st.session_state.confirmed and not st.session_state.proposed_match:
        r = conn.execute("""
            SELECT grade, time, strong_subjects, weak_subjects
            FROM profiles WHERE user_id=?
        """, (st.session_state.user_id,)).fetchone()

        current = {
            "grade": r[0],
            "time": r[1],
            "strong": (r[2] or "").split(","),
            "weak": (r[3] or "").split(","),
        }

        if st.button("Check compatible users"):
            best, score = find_best_match(current)
            if best:
                st.session_state.proposed_match = best
                st.session_state.proposed_score = score
                st.rerun()

        st.info("Click “Check compatible users” to find a match.")
        return

    # ================= CONFIRMATION PAGE =================
    if st.session_state.proposed_match and not st.session_state.confirmed:
        u = st.session_state.proposed_match

        st.subheader("Confirm your study partner")

        with st.container():
            st.markdown(f"""
            <div style="border:1px solid #e5e7eb;
                        border-radius:12px;
                        padding:16px;
                        background:#ffffff">
                <h4>{u['name']}</h4>
                <p><b>Grade:</b> {u['grade']}</p>
                <p><b>Time slot:</b> {u['time']}</p>
                <p><b>Strong subjects:</b> {", ".join(u['strong'])}</p>
                <p><b>Weak subjects:</b> {", ".join(u['weak'])}</p>
                <p><b>Compatibility score:</b> {st.session_state.proposed_score}</p>
            </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm match"):
                match_id = f"{st.session_state.user_id}_{u['user_id']}_{now()}"

                conn.execute("""
                    UPDATE profiles SET status='matched', match_id=?
                    WHERE user_id IN (?,?)
                """, (match_id, st.session_state.user_id, u["user_id"]))

                conn.execute("""
                    INSERT INTO sessions(match_id, user1_id, user2_id, started_at)
                    VALUES (?,?,?,?)
                """, (match_id, st.session_state.user_id, u["user_id"], now()))

                conn.commit()

                st.session_state.current_match_id = match_id
                st.session_state.confirmed = True
                st.session_state.proposed_match = None
                st.balloons()
                st.rerun()

        with col2:
            if st.button("Find another match"):
                st.session_state.proposed_match = None
                st.session_state.proposed_score = None
                st.rerun()

        return

    # ================= LIVE SESSION =================
    if should_poll():
        fetch_messages(st.session_state.current_match_id)
        poll()

    st.subheader("Live chat")
    for s, m in st.session_state.chat_log[-50:]:
        st.write(f"{s}: {m}")

    msg = st.text_input("Message")
    if st.button("Send") and msg:
        conn.execute("""
            INSERT INTO messages(match_id, sender, message, created_ts)
            VALUES (?,?,?,?)
        """, (st.session_state.current_match_id, st.session_state.user_name, msg, now()))
        conn.commit()
        st.rerun()

    f = st.file_uploader("Upload file")
    if f:
        path = f"{UPLOAD_DIR}/{st.session_state.current_match_id}_{f.name}"
        with open(path, "wb") as out:
            out.write(f.read())

        conn.execute("""
            INSERT INTO session_files(match_id, uploader, filename, filepath)
            VALUES (?,?,?,?)
        """, (st.session_state.current_match_id, st.session_state.user_name, f.name, path))
        conn.commit()
        st.success("File uploaded")

    if st.button("End session"):
        conn.execute(
            "UPDATE sessions SET ended_at=? WHERE match_id=?",
            (now(), st.session_state.current_match_id)
        )
        conn.commit()

        chat_text = "\n".join([m for _, m in st.session_state.chat_log])
        st.session_state.summary = ask_ai(
            "Summarize this study session in 5 bullet points:\n" + chat_text
        )
        st.session_state.quiz = ask_ai(
            "Create 3 MCQ questions based on this study session:\n" + chat_text
        )

        st.session_state.session_ended = True
        st.rerun()

    # ================= POST SESSION =================
    if st.session_state.session_ended:
        st.subheader("Session summary")
        st.write(st.session_state.summary)

        if not st.session_state.rating_given:
            rating = star_rating()
            if rating:
                conn.execute("""
                    INSERT INTO session_ratings(match_id, rater_id, rater_name, rating)
                    VALUES (?,?,?,?)
                """, (
                    st.session_state.current_match_id,
                    st.session_state.user_id,
                    st.session_state.user_name,
                    rating
                ))
                conn.commit()
                st.session_state.rating_given = True
                st.success("Rating saved")

        st.subheader("Session quiz")
        st.text(st.session_state.quiz)

        if st.button("Back to matchmaking"):
            reset_matchmaking()
