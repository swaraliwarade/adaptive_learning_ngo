import streamlit as st

def show_rating_ui():
    st.header("Rate Your Session")
    
    if "rating" not in st.session_state:
        st.session_state.rating = 0
        
    cols = st.columns(5)
    for i in range(5):
        star = "⭐" if i < st.session_state.rating else "☆"
        if cols[i].button(star, key=f"star_{i}"):
            st.session_state.rating = i + 1
            
    st.write(f"Rating: {st.session_state.rating}/5")
