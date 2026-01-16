import streamlit as st
import time
import os
import json
from database import conn
from ai_helper import ask_ai

# Ensure upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# UI STYLES (PERSISTENT LAYOUT)
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        .main-card {
            background: white;
            padding: 25px;
            border-radius: 20px;
            border-top: 8px solid #10b981;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            min-height: 600px;
        }
        .ai-sidebar-card {
            background: #f0fdf4;
            padding: 20px;
            border-radius: 20px;
            border: 1px solid #bbf7d0;
            height: 100%;
        }
        .ai-msg { font-size: 0.85rem; padding: 10px; border-radius: 10px; margin-bottom: 8px; }
        .ai-bot { background: #dcfce7; color: #065f46; border-left: 4px solid #10b981; }
        .ai-user { background: white; color: #1e293b; text-align: right; border-right: 4px solid #94a3b8; }
        
        /* Chat History Height Fix */
        .chat-scroll { height: 350px; overflow-y: auto; display: flex; flex-direction: column; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# PERSISTENT AI CHATBOT COMPONENT
# =========================================================
def render_persistent_ai():
    st.markdown("<div class='ai-sidebar-card'>", unsafe_allow_html=True)
    st.markdown("### 🤖 Sahay AI Assistant")
    st.caption("I'm here to help with questions, definitions, or session summaries.")

    # Initialize AI Chat History
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = [{"role": "bot", "content": "Hello! I'm monitoring your session. Ask me anything!"}]

    # Display History
    for chat in st.session_state.ai_chat_history:
        cls = "ai-bot" if chat["role"] == "bot" else "ai-user"
        st.markdown(f"<div class='ai-msg {cls}'>{chat['content']}</div>", unsafe_allow_html=True)

    # Simple Input
    with st.form("ai_query_form", clear_on_submit=True):
        u_query = st.text_input("Ask AI...", label_visibility="collapsed")
        if st.form_submit_button("Ask"):
            if u_query:
                st.session_state.ai_chat_history.append({"role": "user", "content": u_query})
                response = ask_ai(u_query)
                st.session_state.ai_chat_history.append({"role": "bot", "content": response})
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN MATCHMAKING ROUTER (SPLIT VIEW)
# =========================================================
def matchmaking_page():
    inject_ui()
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

    # Create two columns: 70% Matchmaking | 30% AI Assistant
    col_main, col_ai = st.columns([2.2, 1], gap="medium")

    with col_main:
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        
        step = st.session_state.session_step
        if step == "discovery": show_discovery()
        elif step == "confirmation": show_confirmation()
        elif step == "live": show_live_session()
        elif step == "summary": show_summary()
        elif step == "quiz": show_quiz()
        
        st.markdown("</div>", unsafe_allow_html=True)

    with col_ai:
        render_persistent_ai()

# =========================================================
# INDIVIDUAL STEP LOGIC (STUBS - USE PREVIOUS FULL LOGIC HERE)
# =========================================================
def show_discovery():
    st.title("Find a Partner")
    st.write("Ready to collaborate? Click below to search.")
    if st.button("Search Peers"):
        # ... Insert your search logic here ...
        pass

def show_live_session():
    st.title(f"Live with {st.session_state.peer_info['name']}")
    # ... Insert your render_live_chat() and form logic here ...
    if st.button("End Session"):
        st.session_state.session_step = "summary"
        st.rerun()

# ... (Include show_confirmation, show_summary, show_quiz from previous responses)
