import streamlit as st
import time
import os
import random
from database import conn
from ai_helper import ask_ai

# =========================================================
# CONFIG
# =========================================================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

CHAT_REFRESH_MS = 3000

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def require_login():
    if not st.session_state.get("user_id"):
        st.info("Please log in to continue.")
        st.stop()

def init_state():
    defaults = {
        "current_match_id": None,
        "confirmed": False,
        "session_ended": False,
        "chat_log": [],
        "last_msg_ts": 0,
        "summary": None,
        "quiz": None,
        "show_quiz": False,
        "rating_given": False,
        "refresh_key": 0
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def reset_matchmaking():
    conn.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE user_id=?
    """, (st.session_state.user_id,))
    conn.commit()

    for k in list(st.session_state.keys()):
        if k not in ["user_id", "user_name", "logged_in", "page"]:
            del st.session_state[k]

    st.rerun()

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
            "weak": (r[5] or "").split(",")
        })
    return users

def compatibility(a, b):
    score = 0
    score += len(set(a["weak"]) & set(b["strong"])) * 25
    score += len(set(b["weak"]) & set(a["strong"])) * 25
    if a["grade"] == b["grade"]:
        score += 10
    if a["time"] == b["time"]:
        score += 10
    score += random.randint(0, 5)
    return score

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
# UI COMPONENTS
# =========================================================
def star_rating_ui():
    st.write("Rate your mentor")
    cols = st.columns(5)
    for i in range(5):
        if cols[i].button("★", key=f"rate_{i}"):
            return i + 1
    return None

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    require_login()
    init_state()

    st.markdown("## Study Matchmaking")

    # ================= MATCHING =================
    if not st.session_state.confirmed:
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
            st.session_state.refresh_key += 1

        best, score = find_best_match(current)

        if best and score > 0:
            st.write(f"Suggested match: **{best['name']}**")
            st.write(f"Compatibility score: {score}")

            if st.button("Connect"):
                match_id = f"{st.session_state.user_id}_{best['user_id']}_{now()}"
                conn.execute("""
                    UPDATE profiles SET status='matched', match_id=?
                    WHERE user_id IN (?,?)
                """, (match_id, st.session_state.user_id, best["user_id"]))
                conn.execute("""
                    INSERT INTO sessions(match_id, user1_id, user2_id, started_at)
                    VALUES (?,?,?,?)
                """, (match_id, st.session_state.user_id, best["user_id"], now()))
                conn.commit()

                st.session_state.current_match_id = match_id
                st.session_state.confirmed = True
                st.rerun()
        else:
            st.info("No compatible users right now.")
        return

    # ================= LIVE SESSION =================
    st.autorefresh(interval=CHAT_REFRESH_MS, key="chat_refresh")
    fetch_messages(st.session_state.current_match_id)

    st.markdown("### Live chat")
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

    # ================= FILE UPLOAD =================
    st.markdown("### Shared files")
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

    # ================= END SESSION =================
    if st.button("End session"):
        conn.execute("""
            UPDATE sessions SET ended_at=? WHERE match_id=?
        """, (now(), st.session_state.current_match_id))
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
        st.markdown("### Session summary")
        st.write(st.session_state.summary)

        if not st.session_state.rating_given:
            rating = star_rating_ui()
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

        st.markdown("### Session quiz")
        st.text(st.session_state.quiz)

        if st.button("Back to matchmaking"):
            reset_matchmaking()
