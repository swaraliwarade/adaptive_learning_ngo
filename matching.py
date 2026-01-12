import streamlit as st
import os
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
# END SESSION (NEW)
# =========================================================
def end_session(match_id):
    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE match_id=?
    """, (match_id,))
    conn.commit()

# =========================================================
# PAGE
# =========================================================
def matchmaking_page():

    # ---------- HEADER ----------
    st.markdown("""
    <div style="
        padding:1.5rem;
        border-radius:16px;
        background:linear-gradient(135deg,#4f46e5,#6366f1);
        color:white;
        margin-bottom:1.5rem;
    ">
        <h2 style="margin:0;">Peer Learning Session</h2>
        <p style="margin:0;opacity:0.9;">
            Match, learn, and collaborate in real time
        </p>
    </div>
    """, unsafe_allow_html=True)

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

    # =====================================================
    # AI ASSISTANT
    # =====================================================
    st.markdown("### AI Study Assistant")
    with st.form("ai_form", clear_on_submit=True):
        q = st.text_input("Ask a concept, definition, or example")
        if st.form_submit_button("Get Help") and q:
            st.success(ask_ai(q))

    st.divider()

    # =====================================================
    # MATCH PREVIEW
    # =====================================================
    if not match_id:

        if st.button("Find Best Match", use_container_width=True):
            m, s = find_best(user, load_profiles())
            if m:
                st.session_state.proposed_match = m
                st.session_state.proposed_score = s

        if st.session_state.get("proposed_match"):
            m = st.session_state.proposed_match

            st.markdown(f"""
            <div style="
                padding:1.2rem;
                border-radius:14px;
                border:1px solid #e5e7eb;
                background:#ffffff;
                margin-top:1rem;
            ">
                <h4>Suggested Match</h4>
                <p><b>Name:</b> {m['name']}</p>
                <p><b>Role:</b> {m['role']}</p>
                <p><b>Grade:</b> {m['grade']}</p>
                <p><b>Time Slot:</b> {m['time']}</p>
                <p><b>Compatibility Score:</b> {st.session_state.proposed_score}</p>
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            if c1.button("Confirm Match", use_container_width=True):
                mid = f"{user['user_id']}-{m['user_id']}"
                cursor.execute("""
                    UPDATE profiles
                    SET status='matched', match_id=?
                    WHERE user_id IN (?, ?)
                """, (mid, user["user_id"], m["user_id"]))
                conn.commit()
                st.session_state.proposed_match = None
                st.rerun()

            if c2.button("Cancel", use_container_width=True):
                st.session_state.proposed_match = None

        return

    # =====================================================
    # LIVE SESSION
    # =====================================================
    st.markdown("""
    <div style="
        padding:1.2rem;
        border-radius:14px;
        background:#f8fafc;
        border:1px solid #e5e7eb;
        margin-bottom:1rem;
    ">
        <h3 style="margin:0;">Live Learning Room</h3>
    </div>
    """, unsafe_allow_html=True)

    # ---------- CHAT ----------
    st.markdown("### Session Chat")
    chat_box = st.container(height=320)
    with chat_box:
        for sender, msg in load_msgs(match_id):
            st.markdown(f"**{sender}:** {msg}")

    with st.form("chat_form", clear_on_submit=True):
        msg = st.text_input("Type your message")
        if st.form_submit_button("Send") and msg:
            send_msg(match_id, user["name"], msg)
            st.rerun()

    st.divider()

    # ---------- FILE SHARING ----------
    st.markdown("### Shared Resources")
    with st.form("file_form", clear_on_submit=True):
        f = st.file_uploader("Upload a document or image")
        if st.form_submit_button("Upload") and f:
            save_file(match_id, user["name"], f)
            st.rerun()

    for u, n, p in load_files(match_id):
        with open(p, "rb") as file:
            st.download_button(
                label=f"{n} • uploaded by {u}",
                data=file,
                file_name=n,
                use_container_width=True
            )

    st.divider()

    # ---------- END SESSION ----------
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "End Session",
            use_container_width=True,
            help="End the learning session for both participants"
        ):
            end_session(match_id)
            st.success("Session ended successfully.")
            st.rerun()
