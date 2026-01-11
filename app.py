import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from datetime import datetime
from materials import materials_page
from ratings import show_rating_ui

# =========================================================
# CONFIGURATION
# =========================================================
st.set_page_config(page_title="Sahay Live", layout="wide")

# 🔴 PASTE YOUR GOOGLE SHEET URL HERE 🔴
SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit"

# =========================================================
# GOOGLE SHEETS CONNECTION (HACKATHON MODE)
# =========================================================
# NOTE: For a real production app, use st.secrets with Service Account.
# For this demo, we assume the sheet is "Public Editor" for simplicity.
# If that fails, we fallback to local memory for safety.

def get_db_connection():
    try:
        # Authenticating anonymously for public read/write (if enabled) 
        # OR using a simplified service account if you have one.
        # FOR THIS DEMO: We will use a "Public Editor" trick or direct simple auth
        # ideally, you set up st.secrets. 
        
        # Let's try the most robust way for two users:
        # If you haven't set up API keys, this part is tricky.
        # THE SIMPLEST LIVE FIX:
        # We will use st.secrets if available, otherwise warn user.
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Check if secrets exist (The secure way)
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_url(SHEET_URL)
            return sheet
        else:
            return None
    except Exception as e:
        return None

# =========================================================
# DATABASE FUNCTIONS
# =========================================================
def save_profile_to_sheet(data):
    sheet = get_db_connection()
    if sheet:
        ws = sheet.worksheet("Profiles")
        # role, name, grade, time, subjects, status
        row = [data['role'], data['name'], data['grade'], data['time'], ", ".join(data['subjects']), "waiting"]
        ws.append_row(row)
        return True
    return False

def find_live_match(my_role, my_time, my_grade):
    sheet = get_db_connection()
    if not sheet: return None, None
    
    ws = sheet.worksheet("Profiles")
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    
    if df.empty: return None, None

    # Logic: Find someone with opposite role, same time
    opposite_role = "Teacher" if my_role == "Student" else "Student"
    
    # Filter
    candidates = df[
        (df["role"] == opposite_role) & 
        (df["time"] == my_time) & 
        (df["status"] == "waiting")
    ]
    
    if not candidates.empty:
        partner = candidates.iloc[0]
        return partner, partner["name"]
        
    return None, None

def create_match_record(mentor_name, mentee_name):
    sheet = get_db_connection()
    if sheet:
        ws = sheet.worksheet("Matches")
        match_id = f"{mentor_name}-{mentee_name}"
        ws.append_row([mentor_name, mentee_name, match_id])
        
        # Update profiles status to 'matched' (optional optimization)
        return match_id
    return f"{mentor_name}-{mentee_name}"

def send_message(match_id, sender, msg):
    sheet = get_db_connection()
    if sheet:
        ws = sheet.worksheet("Messages")
        timestamp = datetime.now().strftime("%H:%M:%S")
        ws.append_row([match_id, sender, msg, timestamp])

def get_messages(match_id):
    sheet = get_db_connection()
    if sheet:
        ws = sheet.worksheet("Messages")
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        if not df.empty:
            # Filter for this match only
            # Convert match_id to string to be safe
            df['match_id'] = df['match_id'].astype(str)
            return df[df['match_id'] == match_id]
    return pd.DataFrame()

# =========================================================
# SESSION STATE SETUP
# =========================================================
if "stage" not in st.session_state: st.session_state.stage = 1
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "match_id" not in st.session_state: st.session_state.match_id = None
if "partner_name" not in st.session_state: st.session_state.partner_name = ""

# =========================================================
# APP UI
# =========================================================
st.title("Sahay Live: Peer Matchmaking 🌐")

# CHECK CONNECTION
conn = get_db_connection()
if not conn:
    st.error("⚠️ Database Disconnected.")
    st.info("To make this live, you must add Google Service Account credentials to Streamlit Secrets.")
    st.markdown("[See Instructions below on how to fix this]")
    st.stop()

# ---------------------------------------------------------
# STAGE 1: LOGIN / REGISTER
# ---------------------------------------------------------
if st.session_state.stage == 1:
    st.header("Step 1: Join the Queue")
    
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("I am a:", ["Student", "Teacher"])
        name = st.text_input("My Name")
        st.session_state.user_name = name
    with col2:
        grade = st.selectbox("Grade", ["Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"])
        time_slot = st.selectbox("Available Time", ["4-5 PM", "5-6 PM", "6-7 PM"])
        
    subjects = st.multiselect("Subjects", ["Math", "Science", "English", "History"])
    
    if st.button("Go Live & Find Partner", type="primary"):
        if name:
            with st.spinner("Saving to cloud database..."):
                profile_data = {
                    "role": role, "name": name, "grade": grade, 
                    "time": time_slot, "subjects": subjects
                }
                save_profile_to_sheet(profile_data)
                
                # Save to session
                st.session_state.profile = profile_data
                st.session_state.stage = 2
                st.rerun()
        else:
            st.warning("Enter your name")

# ---------------------------------------------------------
# STAGE 2: LIVE MATCHMAKING
# ---------------------------------------------------------
elif st.session_state.stage == 2:
    st.header("Step 2: Finding a Partner...")
    st.info(f"Looking for a partner in **{st.session_state.profile['time']}** slot...")
    
    # Auto-refresh logic (Polling)
    if st.button("🔄 Check for Match Now"):
        partner, partner_name = find_live_match(
            st.session_state.profile["role"],
            st.session_state.profile["time"],
            st.session_state.profile["grade"]
        )
        
        if partner is not None:
            st.success(f"Match Found! You are paired with **{partner_name}**")
            st.session_state.partner_name = partner_name
            
            # Create Match ID
            if st.session_state.profile["role"] == "Teacher":
                m_id = create_match_record(st.session_state.user_name, partner_name)
            else:
                m_id = create_match_record(partner_name, st.session_state.user_name)
                
            st.session_state.match_id = m_id
            time.sleep(1)
            st.session_state.stage = 3
            st.rerun()
        else:
            st.warning("Still looking... tell your friend to register with the opposite role!")

# ---------------------------------------------------------
# STAGE 3: REAL-TIME CHAT
# ---------------------------------------------------------
elif st.session_state.stage == 3:
    st.header(f"Live Session: {st.session_state.user_name} & {st.session_state.partner_name}")
    
    # 1. AI SETUP
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

    col_chat, col_tools = st.columns([2, 1])

    # --- CHAT AREA ---
    with col_chat:
        st.subheader("Discussion Board")
        
        # Load messages from cloud
        msgs_df = get_messages(st.session_state.match_id)
        
        container = st.container(height=400)
        with container:
            if not msgs_df.empty:
                for idx, row in msgs_df.iterrows():
                    is_me = row['sender'] == st.session_state.user_name
                    with st.chat_message("user" if is_me else "assistant"):
                        st.write(f"**{row['sender']}**: {row['message']}")
            else:
                st.write("No messages yet. Say hello!")

        # Send Message
        with st.form("chat_form", clear_on_submit=True):
            user_msg = st.text_input("Type message...")
            sent = st.form_submit_button("Send 🚀")
            
            if sent and user_msg:
                send_message(st.session_state.match_id, st.session_state.user_name, user_msg)
                st.rerun()
                
        if st.button("🔄 Refresh Chat"):
            st.rerun()

    # --- TOOLS AREA ---
    with col_tools:
        st.subheader("Tools")
        
        if st.button("🤖 Ask AI Helper"):
            if not msgs_df.empty:
                last_context = msgs_df.iloc[-1]['message']
                model = genai.GenerativeModel("gemini-1.5-flash")
                resp = model.generate_content(f"A student asked: '{last_context}'. Give a short hint.")
                send_message(st.session_state.match_id, "AI Bot", f"🤖 {resp.text}")
                st.rerun()
                
        if st.button("End Session"):
            st.session_state.stage = 4
            st.rerun()
