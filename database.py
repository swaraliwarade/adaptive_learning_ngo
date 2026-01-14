import sqlite3

conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():

    # -------------------------
    # AUTH USERS
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
    # PROFILES
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER UNIQUE,
        role TEXT,
        grade TEXT,
        time TEXT,
        strong_subjects TEXT,
        weak_subjects TEXT,
        teaches TEXT,
        status TEXT DEFAULT 'waiting',
        match_id TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # -------------------------
    # SAFE MIGRATIONS
    # -------------------------
    def add_column_if_missing(sql):
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError:
            pass

    # Existing migration
    add_column_if_missing(
        "ALTER TABLE profiles ADD COLUMN class_level INTEGER"
    )

    # ✅ REQUIRED FOR LIVE SESSION PRESENCE
    add_column_if_missing(
        "ALTER TABLE profiles ADD COLUMN last_seen INTEGER"
    )

    # -------------------------
    # CHAT MESSAGES
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        sender TEXT,
        message TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # -------------------------
    # SESSION FILES
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS session_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        uploader TEXT,
        filename TEXT,
        filepath TEXT,
        uploaded_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # -------------------------
    # LEGACY RATINGS (KEEP)
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ratings (
        mentor TEXT,
        mentee TEXT,
        rating INTEGER,
        session_date DATE
    )
    """)

    # -------------------------
    # SESSION RATINGS (NEW)
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS session_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        rater_id INTEGER,
        rater_name TEXT,
        rating INTEGER CHECK(rating BETWEEN 1 AND 5),
        rated_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # -------------------------
    # USER STREAKS
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_streaks (
        user_id INTEGER PRIMARY KEY,
        streak INTEGER DEFAULT 0,
        last_active DATE
    )
    """)

    # -------------------------
    # 🔁 REMATCH REQUESTS
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rematch_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    conn.commit()
