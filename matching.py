import streamlit as st
import time
from database import cursor, conn
from ai_helper import ask_ai

SESSION_TIMEOUT_SEC = 60 * 60
REFRESH_INTERVAL_MS = 3000  # 3 seconds

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
        "just_matched": False,
        "partner_joined": False,
        "chat_log": [],
        "proposed_match": None,
        "proposed_score": None,
        "show_quiz": False,
        "quiz_raw": "",
        "quiz_answers": {},
        "ai_chat": []
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
# REAL-TIME PARTNER DETECTION
# =========================================================
def check_partner_joined(match_id):
    cursor.execute("""
        SELECT last_seen FROM profiles
        WHERE match_id=? AND user_id!=?
    """, (match_id, st.session_state.user_id))
    row = cursor.fetchone()
    return bool(row and (now() - (row[0] or 0)) <= 10)

# =========================================================
# REAL-TIME MATCH DETECTION
# =========================================================
def check_if_matched():
    cursor.execute("""
        SELECT match_id FROM profiles
        WHERE user_id=? AND status='matched'
    """, (st.session_state.user_id,))
    row = cursor.fetchone()
    if row and not st.session_state.current_match_id:
        st.session_state.current_match_id = row[0]
        st.session_state.just_matched = True
        st.session_state.session_start_time = now()
        st.rerun()

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
    return ask_ai(
        "Summarize this study session in 5 bullet points:\n" +
        "\n".join(chat[-20:])
    )

def generate_quiz(chat):
    return ask_ai("""
Create exactly 4 MCQ questions from this discussion.
FORMAT STRICTLY AS:
Q1: question
A) option
B) option
C) option
D) option
Answer: A
""" + "\n" + "\n".join(chat[-30:]))

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    init_state()
    update_last_seen()

    # 🔁 AUTO REFRESH (REAL-TIME ENGINE)
    st.autorefresh(interval=REFRESH_INTERVAL_MS, key="match_refresh")

    # Ensure user is available
    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE user_id=? AND status!='matched'
    """, (st.session_state.user_id,))
    conn.commit()

    # 🔎 Detect if matched by other user
    check_if_matched()

    st.title("🤝 Study Matchmaking")

    # 🤖 AI CHATBOT
    st.markdown("### 🤖 AI Study Assistant")
    ai_q = st.text_input("Ask AI anything")
    if st.button("Ask AI") and ai_q:
        reply = ask_ai(ai_q)
        st.session_state.ai_chat.append((ai_q, reply))
    for q, a in st.session_state.ai_chat[-3:]:
        st.markdown(f"**You:** {q}")
        st.markdown(f"**AI:** {a}")
    st.divider()

    # 🎈 MATCH CONFIRMED
    if st.session_state.just_matched:
        st.balloons()
        st.session_state.just_matched = False

    # =====================================================
    # ACTIVE SESSION
    # =====================================================
    if st.session_state.current_match_id and not st.session_state.session_ended:
        elapsed = now() - st.session_state.session_start_time
        remaining = max(0, SESSION_TIMEOUT_SEC - elapsed)
        st.success(f"⏱️ Time left: {remaining//60}m {remaining%60}s")

        if not st.session_state.partner_joined:
            if check_partner_joined(st.session_state.current_match_id):
                st.toast("🎉 Your study partner joined!", icon="🔔")
                st.session_state.partner_joined = True

        st.subheader("💬 Study Chat")
        msg = st.text_input("Message")
        if st.button("Send") and msg:
            st.session_state.chat_log.append(msg)
            cursor.execute(
                "INSERT INTO messages(match_id, sender, message) VALUES (?,?,?)",
                (st.session_state.current_match_id, st.session_state.user_name, msg)
            )
            conn.commit()
            st.success("Sent")

        if st.button("🛑 End Session", use_container_width=True):
            cursor.execute("""
                UPDATE profiles
                SET status='waiting', match_id=NULL
                WHERE match_id=?
            """, (st.session_state.current_match_id,))
            conn.commit()

            st.session_state.session_ended = True
            st.session_state.current_match_id = None
            st.session_state.session_start_time = None
            st.rerun()
        return

    # =====================================================
    # POST SESSION (UNCHANGED)
    # =====================================================
    if st.session_state.session_ended:
        st.subheader("📊 Session Summary")
        st.info(generate_summary(st.session_state.chat_log))

        st.subheader("⭐ Rate Partner")
        rating = st.slider("Rating", 1, 5, 3)
        if st.button("Submit Rating"):
            cursor.execute("""
                INSERT INTO session_ratings
                (match_id, rater_id, rater_name, rating)
                VALUES (?,?,?,?)
            """, (None, st.session_state.user_id,
                  st.session_state.user_name, rating))
            conn.commit()
            st.success("Thanks!")

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

        if st.session_state.show_quiz:
            st.subheader("📝 AI Quiz")
            lines = st.session_state.quiz_raw.splitlines()
            correct = {}
            qn = 0
            for l in lines:
                if l.startswith("Answer"):
                    correct[qn] = l.split(":")[1].strip()
            qn = 0
            for l in lines:
                if l.startswith("Q"):
                    qn += 1
                    st.markdown(f"**{l}**")
                    st.session_state.quiz_answers[qn] = st.radio(
                        f"Q{qn}", ["A", "B", "C", "D"], key=f"q{qn}"
                    )
            if st.button("Submit Quiz"):
                score = sum(
                    1 for q, a in st.session_state.quiz_answers.items()
                    if a == correct.get(q)
                )
                if score == len(correct):
                    st.balloons()
                    st.success("🎉 Perfect!")
                else:
                    st.error("❌ Try again")
        return

    # =====================================================
    # MATCHMAKING VIEW (AUTO)
    # =====================================================
    st.subheader("🔍 Finding best study partner…")

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

    m, s = find_best_match(user)
    if not m:
        st.info("Waiting for a compatible partner…")
        return

    m = normalize_match(m)
    st.info(
        f"**Match found:** {m['name']} ({s}%)\n\n"
        f"Waiting for confirmation…"
    )

    if st.button("✅ Confirm Match", use_container_width=True):
        sid = f"{min(user['user_id'], m['user_id'])}-{max(user['user_id'], m['user_id'])}-{now()}"
        cursor.execute("""
            UPDATE profiles
            SET status='matched', match_id=?
            WHERE user_id IN (?,?)
        """, (sid, user["user_id"], m["user_id"]))
        conn.commit()
