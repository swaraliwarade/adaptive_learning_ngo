import streamlit as st

def support_page():

    st.title("Support Education Through NGOs")

    st.markdown("""
    Education has the power to break the cycle of poverty and create long-term social impact.
    Many students from underprivileged backgrounds lack access to quality learning resources,
    trained educators, and academic support.

    By supporting education-focused NGOs, you help ensure access to learning, nutrition,
    safety, and equal opportunities for children across India.
    """)

    st.divider()

    st.subheader("Prominent Indian Education NGOs")

    ngos = [
        ("Akshaya Patra Foundation",
         "Eliminates classroom hunger with mid-day meals.",
         "https://www.akshayapatra.org"),

        ("Pratham",
         "Improves learning quality through foundational literacy.",
         "https://www.pratham.org"),

        ("Nanhi Kali",
         "Supports underprivileged girls' education.",
         "https://www.nanhikali.org"),

        ("Magic Bus",
         "Activity-based learning for education and life skills.",
         "https://www.magicbus.org"),

        ("Teach For India",
         "Addresses educational inequity in low-income schools.",
         "https://www.teachforindia.org"),

        ("Smile Foundation",
         "Mission Education for underprivileged children.",
         "https://www.smilefoundationindia.org"),

        ("CRY (Child Rights and You)",
         "Child rights and access to education.",
         "https://www.cry.org"),

        ("Bal Raksha Bharat",
         "Early learning, education, and child safety.",
         "https://www.savethechildren.in")
    ]

    for name, desc, link in ngos:
        st.markdown(f"### {name}")
        st.write(desc)
        st.markdown(f"[Visit Official Website]({link})")
        st.markdown("---")

    st.subheader("Ways to Support")

    st.markdown("""
    - **Crowdfunding Platforms**
        - [Ketto](https://www.ketto.org)
        - [Impact Guru](https://www.impactguru.com)

    - **Direct Sponsorship**
        - Sponsor a child's education via Nanhi Kali

    - **Corporate & Philanthropy Grants**
        - Partner with NGOs for long-term impact
    """)

    st.success("Thank you for supporting education.")
