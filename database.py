import sqlite3
import threading
import os

# =========================================================
# DATABASE CONFIGURATION
# =========================================================
DB_PATH = "app.db"

conn = sqlite3.connect(
    DB_PATH,
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
            accepted INTEGER DEFAULT 0,
            class_level INTEGER,
            last_seen INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        migrations = [
            ("class_level", "INTEGER"),
            ("last_seen", "INTEGER"),
            ("accepted", "INTEGER DEFAULT 0"),
            ("match_id", "TEXT"),
            ("status", "TEXT DEFAULT 'waiting'")
        ]
        
        for col, col_type in migrations:
            if not column_exists("profiles", col):
                cursor.execute(f"ALTER TABLE profiles ADD COLUMN {col} {col_type}")

        # -------------------------
        # CHAT MESSAGES
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

        if not column_exists("messages", "created_ts"):
            cursor.execute("ALTER TABLE messages ADD COLUMN created_ts INTEGER")
        if not column_exists("messages", "file_path"):
            cursor.execute("ALTER TABLE messages ADD COLUMN file_path TEXT")

        # -------------------------
        # SESSION RATINGS
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            rater_id INTEGER,
            rating INTEGER CHECK(rating BETWEEN 1 AND 5),
            feedback TEXT,
            rated_at TEXT DEFAULT (datetime('now'))
        )
        """)
        
        if not column_exists("session_ratings", "feedback"):
            cursor.execute("ALTER TABLE session_ratings ADD COLUMN feedback TEXT")

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
        # REMATCH REQUESTS (With 'seen' status)
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rematch_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER,
            to_user INTEGER,
            status TEXT DEFAULT 'pending',
            seen INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        if not column_exists("rematch_requests", "seen"):
            cursor.execute("ALTER TABLE rematch_requests ADD COLUMN seen INTEGER DEFAULT 0")

        # -------------------------
        # INDEXES
        # -------------------------
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_match_id ON profiles(match_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_match_id ON messages(match_id)")

        conn.commit()

init_db()
