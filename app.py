import streamlit as st
from ratings import show_rating_ui
from matching import find_matches

# -------------------------------
# App stage control
# -------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = 1

if "profile" not in st.session_state:
    st.session_state.profile = {}

if "students" not in st.session_state:
    st.session_state.students = []

# -------------------------------
# App Title
# -------------------------------
st.title("Peer Learning Matchmaking System")

# -------------------------------
# STAGE 1 : Profile Setup
# -------------------------------
if st.session_state.stage == 1:
    st.header("Step 1: Profile Setup")

    role = st.radio(
        "Who are you?",
        ["Student", "Teacher"]
    )

    name = st.text_input("Name")

    time = st.selectbox(
        "Available Time Slot",
        ["4–5 PM", "5–6 PM", "6–7 PM"]
    )

    # ✅ DEFAULT VALUES (CRITICAL)
    year = None
    good_at = []
    weak_at = []
    expertise = []

    # -------- Student Section --------
    if role == "Student":
        year = st.selectbox(
            "Current Year",
            ["First Year (FY)", "Second Year (SY)", "Third Year (TY)", "Fourth Year"]
        )

        good_at = st.multiselect(
            "Strong Subjects",
            ["LAC", "CPPS", "CST", "CGD", "ESE", "IEEE", "IKS", "MFR", "OOPC", "QP"]
        )

        weak_at = st.multiselect(
            "Weak Subjects",
            ["LAC", "CPPS", "CST", "CGD", "ESE", "IEEE", "IKS", "MFR", "OOPC", "QP"]
        )

    # -------- Teacher Section --------
    else:
        expertise = st.multiselect(
            "Subjects You Teach",
            ["LAC", "CPPS", "CST", "CGD", "ESE", "IEEE", "IKS", "MFR", "OOPC", "QP"]
        )

    # -------- SUBMIT BUTTON (ONLY PLACE profile IS CREATED) --------
    if st.button("Submit Profile & Continue"):
        profile = {
            "role": role,
            "name": name,
            "time": time,
            "year": year,
            "good_at": good_at if role == "Student" else expertise,
            "weak_at": weak_at if role == "Student" else []
        }

        # Save profile safely
        st.session_state.profile = profile

        # Save students only
        if role == "Student":
            st.session_state.students.append(profile)

        # Move to next stage
        st.session_state.stage = 2
        st.rerun()

# -------------------------------
# STAGE 2 : TEMP CONFIRMATION SCREEN
# -------------------------------
if st.session_state.stage == 2:
    st.header("Finding the Best Match for You 🎮")

    with st.spinner("Analyzing skills... Comparing profiles..."):
        import time
        time.sleep(2)

    matches = find_matches(st.session_state.students)

    if matches:
        best_match = matches[0]
        st.success("Match Found! 🎯")

        st.write("### Mentor–Mentee Pair")
        st.write(f"**Mentor:** {best_match['Mentor']}")
        st.write(f"**Mentee:** {best_match['Mentee']}")
        st.write(f"**Compatibility Score:** {best_match['Score']}")

        st.session_state.current_match = best_match

        if st.button("Start Learning Session"):
            st.session_state.stage = 3
            st.rerun()
    else:
        st.warning("No suitable match found yet.")
        if st.button("Go Back"):
            st.session_state.stage = 1
            st.rerun()

    # -------------------------------
# STAGE 3 : Learning Session
# -------------------------------
if st.session_state.stage == 3:
    st.header("Learning Session 💬")

    match = st.session_state.current_match

    st.info(
        f"Mentor: **{match['Mentor']}**  |  "
        f"Mentee: **{match['Mentee']}**  |  "
        f"Score: **{match['Score']}**"
    )

    st.markdown("### Chat Area (Prototype)")

    chat_input = st.text_area(
        "Type your doubt here",
        placeholder="e.g. I don’t understand LAC differentiation…"
    )

    if st.button("Send Message"):
        if chat_input.strip():
            st.success("Message sent (prototype)")
        else:
            st.warning("Please type a message")

    st.divider()

    col1, col2, col3 = st.columns(3)

    # -------- AI Helper --------
    with col1:
        if st.button("Ask AI 🤖"):
            st.info(
                "AI Suggestion (prototype):\n"
                "Break the problem into steps and revise the basic formula first."
            )

    # -------- Add Faculty --------
    with col2:
        if st.button("Add Faculty 👩‍🏫"):
            st.warning(
                "Faculty has been notified.\n"
                "(Prototype – will connect to real system later)"
            )

    # -------- End Session --------
    with col3:
        if st.button("End Session"):
            st.session_state.stage = 4
            st.rerun()
# -------------------------------
# STAGE 4 : Rating & Rewards
# -------------------------------
if st.session_state.stage == 4:
    st.header("Session Completed 🎉")
    st.write("Please rate your mentor")

    show_rating_ui()
    if st.button("Finish"):
        st.success("Thank you for using the Peer Learning Matchmaking System!")
        st.session_state.stage = 1
        st.session_state.profile = {}
        st.session_state.current_match = {}
        st.rerun()
        
