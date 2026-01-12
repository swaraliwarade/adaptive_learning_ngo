import streamlit as st
import os
from database import cursor, conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads/sessions"
MATCH_THRESHOLD = 30

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

def score(u1, u2):
    s = 0
    s += len(set(u1["weak"]) & set(u2["strong"])) * 25
    s += len(set(u2["weak"]) & set(u1["strong"])) * 25
    if u1["grade"] == u2["grade"]: s += 10
    if u1["time"] == u2["time"]: s += 10
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

def load_msgs(mid):
    cursor.execute("SELECT sender, message FROM messages WHERE match_id=?", (mid,))
    return cursor.fetchall()

def send_msg(mid, s, m):
    cursor.execute(
        "INSERT INTO messages(match_id, sender, message) VALUES (?, ?, ?)",
        (mid, s, m)
    )
    conn.commit()

def save_file(mid, u, f):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = f"{UPLOAD_DIR}/{mid}_{f.name}"
    with open(path, "wb") as out:
        out.write(f.getbuffer())
    cursor.execute("""
        INSERT INTO session_files(match_id, uploader, filename, filepath)
        VALUES (?, ?, ?, ?)
    """, (mid, u, f.name, path))
    conn.commit()

def load_files(mid):
    cursor.execute(
        "SELECT uploader, filename, filepath FROM session_files WHERE match_id=?",
        (mid,)
    )
    return cursor.fetchall()

def matchmaking_page():

    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches, match_id
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))

    row = cursor.fetchone()
    if not row:
        st.warning("Please complete your profile first.")
        return

    role, grade, time_slot, strong, weak, teaches, match_id = row

    user = {
        "user_id": st.session_state.user_id,
        "name": st.session_state.user_name,
        "role": role,
        "grade": grade,
        "time": time_slot,
        "strong": (teaches or strong or "").split(","),
        "weak": (weak or "").split(",")
    }

    st.markdown("### 🧠 AI Tutor")
    with st.form("ai"):
        q = st.text_input("Ask your doubt")
        if st.form_submit_button("Ask") and q:
            st.success(ask_ai(q))

    st.divider()

    if not match_id:
        if st.button("🔍 Find Best Match"):
            m, s = find_best(user, load_profiles())
            if m:
                st.session_state.proposed_match = m
                st.session_state.proposed_score = s

        if st.session_state.get("proposed_match"):
            m = st.session_state.proposed_match
            st.markdown(f"""
            <div class="card">
                <h3>🤝 Match Found</h3>
                <b>{m['name']}</b><br>
                Role: {m['role']}<br>
                Grade: {m['grade']}<br>
                Time: {m['time']}<br>
                Score: {st.session_state.proposed_score}
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            if c1.button("Confirm"):
                mid = f"{user['user_id']}-{m['user_id']}"
                cursor.execute("""
                    UPDATE profiles
                    SET status='matched', match_id=?
                    WHERE user_id IN (?, ?)
                """, (mid, user["user_id"], m["user_id"]))
                conn.commit()
                st.session_state.proposed_match = None
                st.rerun()

            if c2.button("Cancel"):
                st.session_state.proposed_match = None
        return

    st.markdown("""
    <div class="card" style="background:linear-gradient(135deg,#6366f1,#4f46e5);color:white">
        <h2>🎓 Live Learning Room</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 💬 Chat")
    for s, m in load_msgs(match_id):
        st.markdown(f"**{s}:** {m}")

    with st.form("chat"):
        msg = st.text_input("Message")
        if st.form_submit_button("Send") and msg:
            send_msg(match_id, user["name"], msg)
            st.rerun()

    st.markdown("### 📁 Shared Files")
    with st.form("files"):
        f = st.file_uploader("Upload file")
        if st.form_submit_button("Upload") and f:
            save_file(match_id, user["name"], f)
            st.rerun()

    for u, n, p in load_files(match_id):
        with open(p, "rb") as file:
            st.download_button(f"📄 {n} (by {u})", file, file_name=n)
