import streamlit as st
import os
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
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("user_name", "")
    st.session_state.setdefault("current_match_id", None)
    st.session_state.setdefault("session_ended", False)
    st.session_state.setdefault("last_session_id", None)
    st.session_state.setdefault("selected_rating", 0)
    st.session_state.setdefault("just_matched", False)

def update_last_seen():
    if not st.session_state.user_id:
        return
    cursor.execute(
        "UPDATE profiles SET last_seen=? WHERE user_id=?",
        (now(), st.session_state.user_id)
    )
    conn.commit()

def normalize_match(m):
    """
    Defensive normalization:
    - dict -> return as-is
    - tuple -> map safely if length allows
    - anything else -> None
    """
    if not m:
        return None

    if isinstance(m, dict):
        return m

    if isinstance(m, (list, tuple)):
        if len(m) < 5:
            return None  # not enough data
        return {
            "user_id": m[0],
            "name": m[1],
            "role": m[2],
            "grade": m[3],
            "time": m[4],
            "strong": (m[7] if len(m) > 7 else m[5] if len(m) > 5 else "").split(","),
            "weak": (m[6] if len(m) > 6 else "").split(","),
        }

    return None

# =========================================================
# MATCHING
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
# MAIN PAGE
# =========================================================
def matchmaking_page():
    init_state()
    update_last_seen()

    # 🎈 BALLOONS (FIXED)
    if st.session_state.just_matched:
        st.balloons()
        st.session_state.just_matched = False

    # ================= 🤖 AI CHATBOT =================
    st.markdown("### 🤖 AI Study Assistant")
    with st.form("ai_bot"):
        q = st.text_input("Ask the AI anything")
        if st.form_submit_button("Ask") and q:
            st.success(ask_ai(q))

    st.divider()

    # ================= MATCHMAKING =================
    if not st.session_state.current_match_id and not st.session_state.session_ended:
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
            if m:
                st.session_state.proposed_match = m
                st.session_state.proposed_score = s
            else:
                st.info("No suitable match right now.")

        if "proposed_match" in st.session_state:
            m = normalize_match(st.session_state.proposed_match)

            if not m:
                st.warning("Match data is invalid. Please search again.")
                st.session_state.pop("proposed_match", None)
                return

            st.subheader("👤 Suggested Partner")
            st.info(
                f"**Name:** {m['name']}\n\n"
                f"**Role:** {m['role']}\n\n"
                f"**Grade:** {m['grade']}\n\n"
                f"**Strong:** {', '.join(m['strong'])}\n\n"
                f"**Weak:** {', '.join(m['weak'])}\n\n"
                f"**Compatibility:** {st.session_state.proposed_score}"
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
