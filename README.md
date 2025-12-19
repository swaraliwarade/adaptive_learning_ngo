# Peer Learning Matchmaking System 🎓🤝

A Streamlit-based hackathon prototype that enables adaptive peer learning
for NGO and college students by intelligently pairing mentors and mentees
based on strengths, weaknesses, and availability.

---

## 🚩 Problem Statement
Many NGO and college students face:
- Limited access to qualified teachers
- Diverse learning levels in the same classroom
- Lack of personalized learning support

Traditional one-size-fits-all teaching methods leave learning gaps unaddressed.

---

## 💡 Our Solution
We built a **Peer Learning Matchmaking System** that:
- Collects student skill profiles
- Matches mentors and mentees based on subject strengths and weaknesses
- Creates a collaborative learning session
- Encourages mentors through ratings, credits, and badges

The system is designed to be **simple, scalable, and motivating**.

---

## ⚙️ How the System Works
1. User selects role (Student / Teacher)
2. Students enter:
   - Academic year
   - Strong and weak subjects
   - Available time slot
3. System runs a matching algorithm
4. Best mentor–mentee pair is found
5. Learning session begins (chat, AI helper, faculty option – prototype)
6. Mentee rates mentor after the session

---

## 🎮 Key Features
- Role-based profile setup (Student / Teacher)
- Year-wise student classification (FY, SY, TY, Fourth Year)
- Skill-based mentor–mentee matchmaking
- Gamified matching experience
- Learning session interface
- AI helper & faculty escalation (prototype)
- Rating-based mentor rewards

---

## 🛠️ Tech Stack
- Python
- Streamlit
- GitHub (version control)
- Streamlit Community Cloud (deployment)

---

## 🚀 How to Run Locally
```bash
pip install streamlit
streamlit run app.py
