import streamlit as st
from practice_data import PRACTICE_DATA
from streak import update_streak

def practice_page():
    profile = st.session_state.user_profile

    st.subheader("Practice Questions")

    # -------- CLASS --------
    if profile["role"] == "Student":
        user_class = profile["class"]
        st.info(f"Class: {user_class}")
    else:
        user_class = st.selectbox("Select Class", list(PRACTICE_DATA.keys()))

    if user_class not in PRACTICE_DATA:
        st.warning("Practice not available for this class yet.")
        return

    # -------- SUBJECT --------
    subject = st.selectbox(
        "Select Subject",
        list(PRACTICE_DATA[user_class].keys())
    )

    # -------- TOPIC --------
    topic = st.selectbox(
        "Select Topic",
        list(PRACTICE_DATA[user_class][subject].keys())
    )

    questions = PRACTICE_DATA[user_class][subject][topic]

    st.divider()
    st.markdown("### 📝 Answer the following:")

    user_answers = []
    for i, q in enumerate(questions):
        ans = st.radio(
            f"Q{i+1}. {q['q']}",
            q["options"],
            key=f"q_{i}"
        )
        user_answers.append(ans)

    # -------- SUBMIT --------
    if st.button("Submit Practice"):
        score = 0
        for i, q in enumerate(questions):
            if user_answers[i] == q["answer"]:
                score += 1

        st.success(f"✅ Your Score: {score} / {len(questions)}")

        # Update streak ONCE per day
        update_streak()

        if score == len(questions):
            st.balloons()
