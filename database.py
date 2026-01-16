import sqlite3

# =========================================================
# DATABASE CONNECTION
# =========================================================
conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

# =========================================================
# SAFE COLUMN CHECK
# =========================================================
def column_exists(table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return column in [row[1] for row in cursor.fetchall()]

# =========================================================
# INITIALIZE DATABASE
# =========================================================
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
        user_id INTEGER PRIMARY KEY,
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
    if not column_exists("profiles", "class_level"):
        cursor.execute(
            "ALTER TABLE profiles ADD COLUMN class_level INTEGER"
        )

    if not column_exists("profiles", "last_seen"):
        cursor.execute(
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
        created_at TEXT DEFAULT (datetime('now')),
        created_ts INTEGER
    )
    """)

    if not column_exists("messages", "created_ts"):
        cursor.execute(
            "ALTER TABLE messages ADD COLUMN created_ts INTEGER"
        )

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
    # LEGACY RATINGS
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
    # SESSION RATINGS
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
    # REMATCH REQUESTS
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

    # -------------------------
    # STUDY SESSIONS
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT UNIQUE,
        user1_id INTEGER,
        user2_id INTEGER,
        started_at INTEGER,
        ended_at INTEGER,
        summary TEXT
    )
    """)

    # -------------------------
    # SESSION QUIZZES
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS session_quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        user_id INTEGER,
        score INTEGER,
        total INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # -------------------------
    # INDEXES (SAFE)
    # -------------------------
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_profiles_match_id ON profiles(match_id)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_match_id ON messages(match_id)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_created_ts ON messages(created_ts)"
    )

    # -------------------------
    # FINAL COMMIT
    # -------------------------
    conn.commit()
