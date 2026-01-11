import streamlit as st
from database import cursor, conn

def signup():
    st.subheader("Create Account")

    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password)
            )
            conn.commit()
            st.success("Account created successfully")
        except:
            st.error("Email already exists")

def login():
    st.subheader("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )
        user = cursor.fetchone()

        if user:
            st.session_state.logged_in = True
            st.session_state.user_id = user[0]
            st.session_state.user_name = user[1]
            st.success("Logged in successfully")
        else:
            st.error("Invalid credentials")

def auth_page():
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        login()
    with tab2:
        signup()
