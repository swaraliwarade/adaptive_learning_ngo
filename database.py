import sqlite3
import threading

# =========================================================
# DATABASE CONNECTION
# =========================================================
conn = sqlite3.connect(
    "app.db",
    check_same_thread=False
)
cursor = conn.cursor()

_db_lock = threading.Lock()

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
    with _db_lock:

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
        # PROFILES (UPDATED WITH ACCEPTED COLUMN)
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
            accepted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # -------------------------
        # SAFE MIGRATIONS (PROFILES)
        # -------------------------
        if not column_exists("profiles", "class_level"):
            cursor.execute("ALTER TABLE profiles ADD COLUMN class_level INTEGER")

        if not column_exists("profiles", "last_seen"):
            cursor.execute("ALTER TABLE profiles ADD COLUMN last_seen INTEGER")
            
        # FIX FOR MUTUAL CONFIRMATION
        if not column_exists("profiles", "accepted"):
            cursor.execute("ALTER TABLE profiles ADD COLUMN accepted INTEGER DEFAULT 0")

        # -------------------------
        # CHAT MESSAGES (UPDATED WITH FILE_PATH)
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            sender TEXT,
            message TEXT,
            file_path TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            created_ts INTEGER
        )
        """)

        # -------------------------
        # SAFE MIGRATIONS (MESSAGES)
        # -------------------------
        if not column_exists("messages", "created_ts"):
            cursor.execute("ALTER TABLE messages ADD COLUMN created_ts INTEGER")
            
        # FIX FOR FILE SHARING
        if not column_exists("messages", "file_path"):
            cursor.execute("ALTER TABLE messages ADD COLUMN file_path TEXT")

        # -------------------------
        # SESSION FILES (UNCHANGED)
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
        # SESSION RATINGS (UNCHANGED)
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
        # USER STREAKS (UNCHANGED)
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_streaks (
            user_id INTEGER PRIMARY KEY,
            streak INTEGER DEFAULT 0,
            last_active DATE
        )
        """)

        # -------------------------
        # REMATCH REQUESTS (UNCHANGED)
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
        # STUDY SESSIONS (UNCHANGED)
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
        # SESSION QUIZZES (UNCHANGED)
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
        # INDEXES (UNCHANGED)
        # -------------------------
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_match_id ON profiles(match_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_match_id ON messages(match_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_ts ON messages(created_ts)")

        # -------------------------
        # FINAL COMMIT
        # -------------------------
        conn.commit()

# =========================================================
# AUTO INIT (SAFE)
# =========================================================
init_db()
