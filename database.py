import sqlite3

conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():

    # -------------------------
    # AUTH USERS (LOGIN)
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    # -------------------------
    # USER PROFILES (MATCHMAKING)
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER,
        role TEXT,
        grade TEXT,
        class INTEGER,
        time TEXT,
        strong_subjects TEXT,
        weak_subjects TEXT,
        teaches TEXT
    )
    """)

    # -------------------------
    # SESSION RATINGS (STREAK + LEADERBOARD)
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ratings (
        mentor TEXT,
        mentee TEXT,
        rating INTEGER,
        session_date DATE
    )
    """)

    conn.commit()
