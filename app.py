import streamlit as st
from groq import Groq
from supabase import create_client, Client
import time
from datetime import datetime

# =========================================================
# 1. APP CONFIGURATION & STYLING
# =========================================================
st.set_page_config(
    page_title="Sahay: Peer Learning Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (DARK MODE PROOF) ---
st.markdown("""
<style>
    /* Force Light Theme Colors globally */
    [data-testid="stAppViewContainer"] {
        background-color: #f8f9fa;
        color: #31333F;
    }
    
    /* Input Fields & Dropdowns (Fix for Dark Mode systems) */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #31333F !important;
        border: 1px solid #d1d5db;
    }
    
    /* Input Labels */
    .stMarkdown label, .stTextInput label, .stSelectbox label {
        color: #31333F !important;
        font-weight: 600;
    }

    /* Header Styling */
    h1, h2, h3 {
        color: #1e293b !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Buttons */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* Chat Bubbles */
    .chat-bubble-me {
        background-color: #dcf8c6;
        color: #000000;
        padding: 12px 18px;
        border-radius: 15px 15px 0 15px;
        margin: 5px 0 5px auto;
        max-width: 70%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        display: block;
        border: 1px solid #ccebc4;
    }
    
    .chat-bubble-partner {
        background-color: #ffffff;
        color: #000000;
        padding: 12px 18px;
        border-radius: 15px 15px 15px 0;
        margin: 5px 0;
        max-width: 70%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        display: block;
        border: 1px solid #e5e7eb;
    }
    
    .chat-bubble-ai {
        background-color: #e0e7ff;
        border: 1px solid #6366f1;
        color: #312e81;
        padding: 12px 18px;
        border-radius: 15px;
        margin: 10px 0;
        max-width: 85%;
        display: block;
    }
    
    /* Top Bar for Chat */
    .chat-header {
        background: #ffffff;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. BACKEND CONNECTIONS
# =========================================================
try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("❌ Database Connection Failed. Please check Streamlit Secrets.")
    st.stop()

ai_client = None
if "GROQ_API_KEY" in st.secrets:
    try:
        ai_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except: pass

# =========================================================
# 3. HELPER FUNCTIONS
# =========================================================

def upload_file(file_obj, match_id):
    try:
        clean_name = file_obj.name.replace(" ", "_")
        file_path = f"{match_id}/{int(time.time())}_{clean_name}"
        bucket = "chat-files"
        supabase.storage.from_(bucket).upload(file_path, file_obj.getvalue(), {"content-type": file_obj.type})
        return supabase.storage.from_(bucket).get_public_url(file_path)
    except Exception as e:
        st.toast(f"Upload Failed: {str(e)}")
        return None

def calculate_match_score(me, candidate):
    score = 0
    # Data Cleaning
    my_lang = set(x.strip() for x in (me.get('languages') or "").split(',') if x.strip())
    their_lang = set(x.strip() for x in (candidate.get('languages') or "").split(',') if x.strip())
    
    if not my_lang.intersection(their_lang): return 0
    score += 20 

    my_subs = set(x.strip() for x in (me.get('subjects') or "").split(',') if x.strip())
    their_subs = set(x.strip() for x in (candidate.get('subjects') or "").split(',') if x.strip())
    if my_subs.intersection(their_subs): score += 40
    else: return 0

    try:
        my_g = int(me['grade'].split(" ")[1])
        their_g = int(candidate['grade'].split(" ")[1])
        diff = their_g - my_g
        if me['role'] == "Student":
            if diff > 0: score += 30
            elif diff == 0: score += 15
        else:
            if diff < 0: score += 30
    except: pass 

    my_topic = (me.get('specific_topics') or "").lower()
    their_topic = (candidate.get('specific_topics') or "").lower()
    if my_topic and their_topic and (my_topic in their_topic or their_topic in my_topic):
        score += 25

    return score

def find_best_match(my_profile):
    opposite = "Teacher" if my_profile['role'] == "Student" else "Student"
    response = supabase.table("profiles").select("*").eq("role", opposite).eq("time_slot", my_profile['time_slot']).eq("status", "waiting").execute()
    candidates = response.data
    if not candidates: return None

    best = None
    high_score = 0
    for p in candidates:
        s = calculate_match_score(my_profile, p)
        if s > high_score:
            high_score = s
            best = p
    return best

def save_profile(data):
    data['subjects'] = ", ".join(data['subjects'])
    data['languages'] = ",".join(data['languages'])
    try:
        supabase.table("profiles").insert(data).execute()
        return True
    except: return False

def create_match_record(p1, p2):
    names = sorted([p1, p2])
    m_id = f"{names[0]}-{names[1]}"
    try:
        check = supabase.table("matches").select("*").eq("match_id", m_id).execute()
        if not check.data:
            supabase.table("matches").insert({ "match_id": m_id, "mentor": p1, "mentee": p2 }).execute()
            supabase.table("profiles").update({"status": "matched"}).eq("name", p1).execute()
            supabase.table("profiles").update({"status": "matched"}).eq("name", p2).execute()
    except: pass
    return m_id

# =========================================================
# 4. MAIN APP LOGIC
# =========================================================
if "stage" not in st.session_state: st.session_state.stage = 1
if "user_name" not in st.session_state: st.session_state.user_name = ""

st.markdown("<h1>🎓 Sahay <span style='font-size: 20px; color: #666;'>| Peer Learning Ecosystem</span></h1>", unsafe_allow_html=True)

# --- STAGE 1: PROFILE ---
if st.session_state.stage == 1:
    with st.container():
        st.markdown("### 👋 Join a Session")
        st.write("Connect with a peer or mentor who speaks your language.")
        
        with st.form("profile_form"):
            col1, col2 = st.columns(2)
            with col1:
                role = st.radio("I want to:", ["Learn (Student)", "Teach (Mentor)"], horizontal=True)
                role_str = "Student" if "Learn" in role else "Teacher"
                name = st.text_input("My Full Name", placeholder="e.g. Rahul Sharma")
                languages = st.multiselect("Languages I speak", ["English", "Hindi", "Marathi", "Tamil", "Bengali", "Telugu"])
            with col2:
                grade = st.selectbox("Current Grade", [f"Grade {i}" for i in range(5, 13)])
                time_slot = st.selectbox("Preferred Time", ["4-5 PM", "5-6 PM", "6-7 PM"])
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                subjects = st.multiselect("Subjects", ["Mathematics", "Science", "English", "History", "Physics", "Chemistry"])
            with c2:
                topics = st.text_input("Specific Topic Focus", placeholder="e.g. Algebra, Thermodynamics, Grammar")

            if st.form_submit_button("Find My Match 🚀", type="primary", use_container_width=True):
                if name and subjects and languages:
                    profile = {
                        "role": role_str, "name": name, "grade": grade, 
                        "time_slot": time_slot, "subjects": subjects,
                        "languages": languages, "specific_topics": topics, 
                        "status": "waiting"
                    }
                    if save_profile(profile):
                        st.session_state.profile = profile
                        st.session_state.user_name = name
                        st.session_state.stage = 2
                        st.rerun()
                else:
                    st.error("⚠️ Please fill in Name, Languages, and Subjects.")

# --- STAGE 2: MATCHING ---
elif st.session_state.stage == 2:
    st.markdown("### 🔍 Analyzing Peers...")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info(f"Looking for match for **{st.session_state.user_name}** ({st.session_state.profile['time_slot']})...")
        if st.button("🔄 Click to Search Now", type="primary", use_container_width=True):
            with st.spinner("Calculating compatibility scores..."):
                time.sleep(1)
                match = find_best_match(st.session_state.profile)
            
            if match:
                st.balloons()
                st.success(f"🎉 Match Found! Connected with **{match['name']}**")
                m_id = create_match_record(st.session_state.user_name, match['name'])
                st.session_state.match_id = m_id
                st.session_state.partner_name = match['name']
                time.sleep(1.5)
                st.session_state.stage = 3
                st.rerun()
            else:
                st.warning("⏳ No perfect match yet. Waiting for more users...")

# --- STAGE 3: CHAT ---
elif st.session_state.stage == 3:
    st.markdown(f"""
    <div class='chat-header'>
        <h3 style='margin:0; color:#333;'>🔴 Live: {st.session_state.user_name} & {st.session_state.partner_name}</h3>
        <span style='background: #dcf8c6; padding: 5px 12px; border-radius: 20px; font-size: 0.9em; color: #1e7e34; font-weight:bold;'>Connected</span>
    </div>
    """, unsafe_allow_html=True)
    
    col_chat, col_tools = st.columns([3, 1])
    
    with col_chat:
        try:
            msgs = supabase.table("messages").select("*").eq("match_id", st.session_state.match_id).order("created_at").execute().data
        except: msgs = []

        with st.container(height=500, border=True):
            if not msgs: st.caption("Start the conversation! 👋")
            for m in msgs:
                if m['sender'] == st.session_state.user_name:
                    st.markdown(f"<div class='chat-bubble-me'>{m['message']}</div>", unsafe_allow_html=True)
                    if m.get('file_url'): st.markdown(f"<div style='float:right; clear:both; margin-bottom:10px;'><a href='{m['file_url']}' target='_blank'>📎 View File</a></div>", unsafe_allow_html=True)
                elif m['sender'] == "AI Bot":
                    st.markdown(f"<div class='chat-bubble-ai'>🤖 <b>Sahay AI:</b> {m['message'].replace('🤖 ', '')}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-bubble-partner'><b>{m['sender']}:</b> {m['message']}</div>", unsafe_allow_html=True)
                    if m.get('file_url'): st.markdown(f"<div style='float:left; clear:both; margin-bottom:10px;'><a href='{m['file_url']}' target='_blank'>📎 View File</a></div>", unsafe_allow_html=True)

        with st.form("chat_input", clear_on_submit=True):
            c1, c2 = st.columns([5, 1])
            with c1: txt = st.text_input("Msg", label_visibility="collapsed", placeholder="Type here...")
            with c2: sent = st.form_submit_button("Send ➤")
            if sent and txt:
                supabase.table("messages").insert({ "match_id": st.session_state.match_id, "sender": st.session_state.user_name, "message": txt }).execute()
                st.rerun()

    with col_tools:
        with st.container(border=True):
            st.markdown("#### 🛠️ Tools")
            if st.button("🔄 Refresh", use_container_width=True): st.rerun()
            
            st.markdown("---")
            st.write("📂 **Share File**")
            up_file = st.file_uploader("Upload", key="u", label_visibility="collapsed")
            if up_file and st.button("Send File", use_container_width=True):
                with st.spinner("Sending..."):
                    url = upload_file(up_file, st.session_state.match_id)
                    if url:
                        supabase.table("messages").insert({ "match_id": st.session_state.match_id, "sender": st.session_state.user_name, "message": "📄 *Sent a file*", "file_url": url, "file_type": up_file.type }).execute()
                        st.rerun()

            st.markdown("---")
            st.write("🤖 **AI Tutor**")
            if st.button("✨ Ask Hint", type="primary", use_container_width=True):
                if ai_client:
                    try:
                        ctx = " ".join([m['message'] for m in msgs[-3:] if m['message'] and "Sent a file" not in m['message']]) or "No context."
                        reply = ai_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "system", "content": "Helpful tutor. Short hint."}, {"role": "user", "content": f"Context: {ctx}"}],
                            temperature=0.7, max_tokens=100
                        ).choices[0].message.content
                        supabase.table("messages").insert({ "match_id": st.session_state.match_id, "sender": "AI Bot", "message": f"🤖 {reply}" }).execute()
                        st.rerun()
                    except Exception as e: st.error(f"AI Error: {e}")
            
            st.markdown("---")
            if st.button("🛑 End", type="secondary", use_container_width=True):
                st.session_state.stage = 1
                st.rerun()
