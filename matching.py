# matching.py
import streamlit as st

# -------------------------------------------------
# SAMPLE PEER DATA (can be DB later)
# -------------------------------------------------
PEERS = [
    {"name": "Aarav", "grade": "10", "subject": "Mathematics"},
    {"name": "Diya", "grade": "10", "subject": "Science"},
    {"name": "Kabir", "grade": "9", "subject": "Mathematics"},
    {"name": "Ananya", "grade": "11", "subject": "English"},
    {"name": "Riya", "grade": "12", "subject": "Science"},
]

SUBJECTS = ["Mathematics", "English", "Science"]

# -------------------------------------------------
# CORE MATCHING FUNCTION
# -------------------------------------------------
def match_peers(grade, subject):
    matches = []
    for peer in PEERS:
        if peer["grade"] == grade and peer["subject"] == subject:
            matches.append(peer)
    return matches

# -------------------------------------------------
# STREAMLIT PAGE
# -------------------------------------------------
def matchmaking_page():

    st.markdown("""
    <div class="card">
        <h2>Peer Learning Matchmaking</h2>
        <p>Select your grade and subject to find suitable peers.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("match_form"):
        grade = st.selectbox("Your Grade", ["9", "10", "11", "12"])
        subject = st.selectbox("Subject", SUBJECTS)
        submitted = st.form_submit_button("Find Matches")

    if submitted:
        results = match_peers(grade, subject)

        if results:
            st.success(f"Found {len(results)} match(es)")
            for r in results:
                st.markdown(f"""
                <div class="card">
                    <strong>Name:</strong> {r['name']} <br>
                    <strong>Grade:</strong> {r['grade']} <br>
                    <strong>Subject:</strong> {r['subject']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No matching peers found.")
