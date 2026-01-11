import streamlit as st
from database import cursor, conn

def signup():
    st.subheader("Create Account")

    name = st.text_input("Name", key="signup_name")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")

    if st.button("Sign Up", key="signup_btn"):
        if not name or not email or not password:
            st.warning("Please fill all fields")
            return

        try:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password)
            )
            conn.commit()
            st.success("Account created successfully. Please login.")
        except Exception as e:
            st.error("Email already exists")


def login():
    st.subheader("Login")

    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_btn"):
        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )
        user = cursor.fetchone()

        if user:
            st.session_state.logged_in = True
            st.session_state.user_id = user[0]
            st.session_state.user_name = user[1]
            st.session_state.page = "Dashboard"
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid email or password")


def auth_page():
    st.title("Welcome to Peer Learning Platform")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        login()

    with tab2:
        signup()
