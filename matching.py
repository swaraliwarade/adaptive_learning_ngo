import streamlit as st
import os
from datetime import datetime, timedelta
from database import cursor, conn
from ai_helper import ask_ai

MATCH_THRESHOLD = 30
SESSION_TIMEOUT_MIN = 60
UPLOAD_DIR = "uploads/sessions"

# =========================================================
# CLEANUP STALE USERS
# =========================================================
def cleanup_stale_profiles():
    expiry = (datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MIN)) \
        .strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        DELETE FROM profiles
        WHERE status='waiting'
        AND datetime(created_at) < datetime(?)
    """, (expiry,))
    conn.commit()

# =========================================================
# LOAD WAITING USERS
# =========================================================
def load_profiles():
    cursor.execute("""
        SELECT 
            a.id,
            a.name,
            p.role,
            p.grade,
            p.time,
            p.strong_subjects,
            p.weak_subjects,
            p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id = p.user_id
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

# =========================================================
# MATCH SCORING
# =========================================================
def calculate_match_score(user1, user2):
    score = 0

    if user1["role"] == "Student" and user2["role"] == "Student":
        for s in user1["weak"]:
            if s and s in user2["strong"]:
                score += 25
        for s in user2["weak"]:
            if s and s in user1["strong"]:
                score += 25
    else:
        mentor = user1 if user1["role"] == "Teacher" else user2
        mentee = user2 if mentor == user1 else user1
        for s in mentee["weak"]:
            if s and s in mentor["strong"]:
                score += 30

    if user1["grade"] == user2["grade"]:
        score += 10
    if user1["time"] == user2["time"]:
        score += 10

    return score

# =========================================================
# FIND MATCH
# =========================================================
def find_best_match(current_user, all_users):
    cleanup_stale_profiles()
    best, best_score = None, 0

    for other in all_users:
        if other["user_id"] == current_user["user_id"]:
            continue
        if current_user["role"] == "Teacher" and other["role"] == "Teacher":
            continue

        score = calculate_match_score(current_user, other)
        if score > best_score:
            best, best_score = other, score

    if best_score >= MATCH_THRESHOLD:
        return best, best_score
    return None, 0

# =========================================================
# CHAT HELPERS
# =========================================================
def load_messages(match_id):
    cursor.execute("""
        SELECT sender, message
        FROM messages
        WHERE match_id=?
        ORDER BY created_at
    """, (match_id,))
    return cursor.fetchall()

def send_message(match_id, sender, message):
    cursor.execute("""
        INSERT INTO messages (match_id, sender, message)
        VALUES (?, ?, ?)
    """, (match_id, sender, message))
    conn.commit()

# =========================================================
# FILE HELPERS (NEW)
# =========================================================
def save_file(match_id, uploader, uploaded_file):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    safe_name = f"{match_id}_{uploaded_file.name}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    cursor.execute("""
        INSERT INTO session_files (match_id, uploader, filename, filepath)
        VALUES (?, ?, ?, ?)
    """, (match_id, uploader, uploaded_file.name, file_path))
    conn.commit()

def load_session_files(match_id):
    cursor.execute("""
        SELECT uploader, filename, filepath, uploaded_at
        FROM session_files
        WHERE match_id=?
        ORDER BY uploaded_at DESC
    """, (match_id,))
    return cursor.fetchall()

# =========================================================
# MATCHMAKING PAGE
# =========================================================
def matchmaking_page():

    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches, match_id
        FROM profiles
        WHERE user_id=?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    if not profile:
        st.warning("Please complete your profile first.")
        return

    role, grade, time_val, strong, weak, teaches, match_id = profile

    current_user = {
        "user_id": st.session_state.user_id,
        "name": st.session_state.user_name,
        "role": role,
        "grade": grade,
        "time": time_val,
        "strong": (teaches or strong or "").split(","),
        "weak": (weak or "").split(",")
    }

    # ================= PEER CHAT =================
    if match_id:
        st.subheader("Live Learning Room")

        chat_box = st.container(height=300)
        with chat_box:
            for sender, msg in load_messages(match_id):
                st.markdown(f"**{sender}:** {msg}")

        with st.form("chat_form", clear_on_submit=True):
            msg = st.text_input("Message")
            send = st.form_submit_button("Send")
            if send and msg.strip():
                send_message(match_id, current_user["name"], msg)
                st.rerun()

        # ================= AI CHATBOT =================
        st.divider()
        st.subheader("AI Tutor")

        with st.form("ai_form", clear_on_submit=True):
            ai_q = st.text_input("Ask AI")
            ask = st.form_submit_button("Ask")
            if ask and ai_q.strip():
                st.success(ask_ai(ai_q))

        # ================= FILE SHARING =================
        st.divider()
        st.subheader("Shared Files")

        with st.form("file_form", clear_on_submit=True):
            file = st.file_uploader(
                "Upload file",
                type=["pdf", "png", "jpg", "jpeg", "txt", "docx"]
            )
            upload = st.form_submit_button("Upload")

            if upload and file:
                save_file(match_id, current_user["name"], file)
                st.success("File uploaded")
                st.rerun()

        files = load_session_files(match_id)
        for uploader, fname, path, _ in files:
            with open(path, "rb") as f:
                st.download_button(
                    label=f"{fname} (by {uploader})",
                    data=f,
                    file_name=fname
                )

    # ================= FIND MATCH =================
    if st.button("Find Best Match", use_container_width=True):
        all_users = load_profiles()
        match, score = find_best_match(current_user, all_users)

        if match:
            match_id = f"{current_user['user_id']}-{match['user_id']}"
            cursor.execute("""
                UPDATE profiles
                SET status='matched', match_id=?
                WHERE user_id IN (?, ?)
            """, (match_id, current_user["user_id"], match["user_id"]))
            conn.commit()
            st.success(f"Matched with {match['name']} (Score {score})")
            st.rerun()
        else:
            st.warning("No match found.")
