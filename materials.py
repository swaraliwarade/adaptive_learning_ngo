import streamlit as st
from materials_data import MATERIALS

def materials_page():
    st.title("📚 Learning Materials")
    
    # Class Selection
    standard = st.selectbox("Select Class", list(MATERIALS.keys()))
    
    if standard:
        # Subject Selection
        subject = st.selectbox("Select Subject", list(MATERIALS[standard].keys()))
        
        if subject:
            st.subheader(f"Class {standard} - {subject}")
            for item in MATERIALS[standard][subject]:
                with st.expander(f"📘 {item['topic']}"):
                    st.write("**Quick Notes:**")
                    for note in item["notes"]:
                        st.write(f"- {note}")
                    st.markdown(f"[🔗 Read More]({item['link']})")
