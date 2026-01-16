import streamlit as st
import time
import os
import random
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def init_state():
    defaults = {
        "current_match_id": None,
        "session_start_time": None,
        "session_ended": False,
        "confirmed": False,
        "chat_log": [],
        "last_msg_ts": 0,
        "ai_chat": [],
        "summary": None,
        "quiz": None,
        "show_quiz": False,
        "refresh_key": 0,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def require_login():
    if not st.session_state.user_id:
        st.warning("Please log in to use matchmaking.")
        st.stop()

def update_presence():
    conn.execute("""
        UPDATE profiles
        SET last_seen=?, status='waiting', match_id=NULL
        WHERE user_id=?
    """, (now(), st.session_state.user_id))
    conn.commit()

def reset_matchmaking():
    update_presence()

    for k in [
        "current_match_id",
        "session_start_time",
        "session_ended",
        "confirmed",
        "summary",
        "quiz",
        "show_quiz"
    ]:
        st.session_state[k] = None if k in ["current_match_id", "summary", "quiz"] else False

    st.session_state.chat_log = []
    st.session_state.last_msg_ts = 0
    st.rerun()

# =========================================================
# MATCHING LOGIC
# =========================================================
def load_waiting_profiles():
    rows = conn.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects,
               COALESCE(p.last_seen, ?)
        FROM profiles p
        JOIN auth_users a ON a.id=p.user_id
        WHERE p.user_id!=?
          AND p.status='waiting'
          AND p.match_id IS NULL
    """, (now(), st.session_state.user_id)).fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r[0],
            "name": r[1],
            "role": r[2],
            "grade": r[3],
            "time": r[4],
            "strong": (r[5] or "").split(","),
            "weak": (r[6] or "").split(","),
            "last_seen": r[7]
        })
    return users

def compatibility_score(a, b):
    s = 0
    s += len(set(a["weak"]) & set(b["strong"])) * 25
    s += len(set(b["weak"]) & set(a["strong"])) * 25
    if a["grade"] == b["grade"]:
        s += 10
    if a["time"] == b["time"]:
        s += 10
    return s

def weighted_score(current, candidate):
    base = compatibility_score(current, candidate)
    activity_bonus = max(0, 10 - (now() - candidate["last_seen"]) // 30)
    random_bonus = random.randint(0, 5)
    return base + activity_bonus + random_bonus

def find_best_match(current):
    best, best_score = None, -1
    for u in load_waiting_profiles():
        sc = weighted_score(current, u)
        if sc > best_score:
            best, best_score = u, sc
    return best, best_score

# =========================================================
# LIVE CHAT
# =========================================================
def fetch_new_messages(match_id):
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
# AI
# =========================================================
def ai_chat_ui():
    st.subheader("🤖 AI Assistant")
    q = st.text_input("Ask AI", key="ai_input")
    if st.button("Ask", key="ai_btn") and q:
        st.session_state.ai_chat.append((q, ask_ai(q)))

    for q, a in st.session_state.ai_chat[-4:]:
        st.markdown(f"**You:** {q}")
        st.markdown(f"**AI:** {a}")

def generate_summary(chat):
    return ask_ai(
        "Summarize this study session in 5 bullet points:\n" +
        "\n".join([m for _, m in chat][-25:])
    )

def generate_quiz(chat):
    return ask_ai(
        "Create 3 MCQs from this discussion with answers:\n" +
        "\n".join([m for _, m in chat][-25:])
    )

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    init_state()
    require_login()
    update_presence()

    st.title("🤝 Study Matchmaking")
    ai_chat_ui()
    st.divider()

    # ================= MATCHING =================
    if not st.session_state.confirmed:
        r = conn.execute("""
            SELECT role, grade, time, strong_subjects, weak_subjects
            FROM profiles WHERE user_id=?
        """, (st.session_state.user_id,)).fetchone()

        current = {
            "user_id": st.session_state.user_id,
            "role": r[0],
            "grade": r[1],
            "time": r[2],
            "strong": (r[3] or "").split(","),
            "weak": (r[4] or "").split(","),
        }

        if st.button("🔄 Check Compatible Users"):
            st.session_state.refresh_key += 1
            st.rerun()

        best, sc = find_best_match(current)

        if best and sc > 0:
            st.subheader("✨ Suggested Match")
            st.write(f"**Name:** {best['name']}")
            st.write(f"**Compatibility:** {sc}")

            if st.button("Confirm Match"):
                match_id = f"{st.session_state.user_id}_{best['user_id']}_{now()}"

                conn.execute("""
                    UPDATE profiles
                    SET status='matched', match_id=?
                    WHERE user_id IN (?,?)
                """, (match_id, st.session_state.user_id, best["user_id"]))

                conn.execute("""
                    INSERT INTO sessions(match_id, user1_id, user2_id, started_at)
                    VALUES (?,?,?,?)
                """, (match_id, st.session_state.user_id, best["user_id"], now()))

                conn.commit()
                st.session_state.current_match_id = match_id
                st.session_state.confirmed = True
                st.balloons()
                st.rerun()
        else:
            st.info("No compatible users right now.")

        return

    # ================= ACTIVE SESSION =================
    fetch_new_messages(st.session_state.current_match_id)

    st.subheader("💬 Live Chat")
    for s, m in st.session_state.chat_log[-40:]:
        st.markdown(f"**{s}:** {m}")

    msg = st.text_input("Message")
    if st.button("Send") and msg:
        conn.execute(
            "INSERT INTO messages(match_id, sender, message, created_ts) VALUES (?,?,?,?)",
            (st.session_state.current_match_id, st.session_state.user_name, msg, now())
        )
        conn.commit()
        st.rerun()

    if st.button("End Session"):
        conn.execute("""
            UPDATE sessions SET ended_at=? WHERE match_id=?
        """, (now(), st.session_state.current_match_id))
        conn.commit()

        st.session_state.session_ended = True
        st.session_state.summary = generate_summary(st.session_state.chat_log)
        st.rerun()

    # ================= POST SESSION =================
    if st.session_state.session_ended:
        st.subheader("📝 Session Summary")
        st.write(st.session_state.summary)

        rating = st.slider("⭐ Rate mentor", 1, 5)
        if st.button("Submit Rating"):
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
            st.success("Rating saved")

        if st.button("Back to Matchmaking"):
            reset_matchmaking()
