import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import time

# =========================================================
# CONFIGURATION & SETUP
# =========================================================
st.set_page_config(page_title="Sahay: Live Peer Learning", layout="wide")

# 1. SETUP SUPABASE
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"❌ Supabase Connection Failed. Check Secrets. Error: {e}")
    st.stop()

# 2. SETUP AI (Using Stable Model)
ai_available = False
if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        ai_available = True
    except Exception as e:
        st.warning(f"AI Key found but configuration failed: {e}")
else:
    st.warning("⚠️ GOOGLE_API_KEY missing in Secrets. AI features disabled.")

# =========================================================
# INTELLIGENT MATCHING ALGORITHM
# =========================================================
def find_smart_match(role, time_slot, my_subjects):
    """
    Finds the best match based on:
    1. Time Availability (Must match)
    2. Role (Must be opposite)
    3. Subject Overlap (Bonus Points!)
    """
    opposite_role = "Teacher" if role == "Student" else "Student"
    
    # 1. Fetch all waiting candidates
    response = supabase.table("profiles").select("*")\
        .eq("role", opposite_role)\
        .eq("time_slot", time_slot)\
        .eq("status", "waiting")\
        .execute()
    
    candidates = response.data
    if not candidates:
        return None

    # 2. Score Candidates
    best_candidate = None
    highest_score = -1

    for person in candidates:
        score = 0
        person_subjects = person.get("subjects", "").split(", ")
        
        # Check for Subject Overlap (+50 Points)
        overlap = set(my_subjects).intersection(set(person_subjects))
        if overlap:
            score += 50
        
        # Select this person if they have a higher score
        if score > highest_score:
            highest_score = score
            best_candidate = person

    return best_candidate

# =========================================================
# DATABASE ACTIONS
# =========================================================
def save_profile(data):
    data['subjects'] = ", ".join(data['subjects']) # Convert list to string
    try:
        supabase.table("profiles").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

def create_match_record(mentor, mentee):
    match_id = f"{mentor}-{mentee}"
    try:
        # Check existing to prevent errors
        check = supabase.table("matches").select("*").eq("match_id", match_id).execute()
        if not check.data:
            supabase.table("matches").insert({
                "match_id": match_id, "mentor": mentor, "mentee": mentee
            }).execute()
            
            # Update status to 'matched'
            supabase.table("profiles").update({"status": "matched"}).eq("name", mentor).execute()
            supabase.table("profiles").update({"status": "matched"}).eq("name", mentee).execute()
    except Exception as e:
        st.error(f"Match Record Error: {e}")
    return match_id

def upload_file(file_obj, match_id):
    try:
        # Unique path: match_id/timestamp_filename
        file_path = f"{match_id}/{int(time.time())}_{file_obj.name}"
        bucket = "chat-files"
        
        # Upload
        supabase.storage.from_(bucket).upload(
            file_path, 
            file_obj.getvalue(),
            {"content-type": file_obj.type}
        )
        # Get URL
        return supabase.storage.from_(bucket).get_public_url(file_path)
    except Exception as e:
        st.error(f"Upload Failed: {e}")
        return None

# =========================================================
# APP UI
# =========================================================
if "stage" not in st.session_state: st.session_state.stage = 1
if "user_name" not in st.session_state: st.session_state.user_name = ""

st.title("Sahay: Smart Peer Learning 🧠")

# ---------------------------------------------------------
# STAGE 1: LOGIN & PROFILE
# ---------------------------------------------------------
if st.session_state.stage == 1:
    st.header("Step 1: Join Session")
    
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("I am a:", ["Student", "Teacher"])
        name = st.text_input("My Name")
    with col2:
        grade = st.selectbox("Grade", ["Grade 8", "Grade 9", "Grade 10"])
        time_slot = st.selectbox("Time Slot", ["4-5 PM", "5-6 PM"])
        
    subjects = st.multiselect("Subjects", ["Math", "Science", "English", "History"])

    if st.button("Go Live", type="primary"):
        if name and subjects:
            profile = {
                "role": role, "name": name, "grade": grade, 
                "time_slot": time_slot, "subjects": subjects, "status": "waiting"
            }
            if save_profile(profile):
                st.session_state.profile = profile
                st.session_state.user_name = name
                st.session_state.stage = 2
                st.rerun()
        else:
            st.warning("Please fill in Name and Subjects.")

# ---------------------------------------------------------
# STAGE 2: SMART MATCHING
# ---------------------------------------------------------
elif st.session_state.stage == 2:
    st.header("Step 2: Finding Best Match...")
    st.info(f"Looking for experts in: {', '.join(st.session_state.profile['subjects'])}")
    
    if st.button("🔄 Search for Partner"):
        match = find_smart_match(
            st.session_state.profile['role'],
            st.session_state.profile['time_slot'],
            st.session_state.profile['subjects']
        )
        
        if match:
            # Determine Names
            p1 = st.session_state.user_name
            p2 = match['name']
            
            st.success(f"🎉 Match Found! You are connected with **{p2}**")
            st.caption(f"Matched based on shared subjects: {match['subjects']}")
            
            # Create Match ID
            if st.session_state.profile['role'] == "Teacher":
                m_id = create_match_record(p1, p2)
            else:
                m_id = create_match_record(p2, p1)
                
            st.session_state.match_id = m_id
            st.session_state.partner_name = p2
            time.sleep(1)
            st.session_state.stage = 3
            st.rerun()
        else:
            st.warning("No perfect match yet. Waiting for more users...")

# ---------------------------------------------------------
# STAGE 3: CHAT + AI + FILES
# ---------------------------------------------------------
elif st.session_state.stage == 3:
    st.header(f"Live Session: {st.session_state.user_name} & {st.session_state.partner_name}")
    
    col_chat, col_tools = st.columns([2, 1])

    # --- CHAT LOOP ---
    with col_chat:
        # Fetch Messages
        try:
            msgs = supabase.table("messages").select("*")\
                .eq("match_id", st.session_state.match_id)\
                .order("created_at", desc=False).execute().data
        except:
            msgs = []

        container = st.container(height=400)
        with container:
            if msgs:
                for m in msgs:
                    is_me = m['sender'] == st.session_state.user_name
                    with st.chat_message("user" if is_me else "assistant"):
                        if m['message']: st.write(f"**{m['sender']}:** {m['message']}")
                        if m['file_url']: 
                            if "image" in m.get('file_type', ''):
                                st.image(m['file_url']) 
                            else:
                                st.markdown(f"📎 [Download File]({m['file_url']})")
            else:
                st.info("Start the conversation!")

        with st.form("msg_form", clear_on_submit=True):
            txt = st.text_input("Message...")
            if st.form_submit_button("Send") and txt:
                supabase.table("messages").insert({
                    "match_id": st.session_state.match_id,
                    "sender": st.session_state.user_name,
                    "message": txt,
                    "file_url": None
                }).execute()
                st.rerun()
        
        if st.button("🔄 Refresh"): st.rerun()

    # --- TOOLS ---
    with col_tools:
        st.subheader("Tools")
        
        # File Upload
        up_file = st.file_uploader("Share Image/PDF", key="u")
        if up_file and st.button("Upload File"):
            url = upload_file(up_file, st.session_state.match_id)
            if url:
                supabase.table("messages").insert({
                    "match_id": st.session_state.match_id,
                    "sender": st.session_state.user_name,
                    "message": "",
                    "file_url": url,
                    "file_type": up_file.type
                }).execute()
                st.success("File Sent!")
                st.rerun()
        
        st.divider()
        
        # AI Helper
        if st.button("🤖 Ask AI Hint"):
            if not ai_available:
                st.error("AI Key missing.")
            else:
                try:
                    # Context: Last 3 messages
                    context_msgs = [m['message'] for m in msgs[-3:] if m['message']]
                    context = " ".join(context_msgs) if context_msgs else "No context yet."
                    
                    # USE STABLE MODEL HERE
                    model = genai.GenerativeModel("gemini-pro")
                    
                    resp = model.generate_content(f"Two students are discussing: '{context}'. Give a short, helpful hint.")
                    
                    # Inject AI response into chat
                    supabase.table("messages").insert({
                        "match_id": st.session_state.match_id,
                        "sender": "AI Bot",
                        "message": f"🤖 {resp.text}",
                        "file_url": None
                    }).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"AI Error: {e}")

        if st.button("End Session"):
            st.session_state.stage = 1
            st.rerun()
