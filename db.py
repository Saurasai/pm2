import sqlite3
import os
from passlib.context import CryptContext
import streamlit as st
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

DB_PATH = "data/users.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
IST = pytz.timezone("Asia/Kolkata")

def migrate_db():
    logger.info("Migrating database schema")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Add reminder_minutes column if not exists
        c.execute("ALTER TABLE scheduled_posts ADD COLUMN reminder_minutes INTEGER NOT NULL DEFAULT 60")
        # Add reminder_sent column if not exists
        c.execute("ALTER TABLE scheduled_posts ADD COLUMN reminder_sent BOOLEAN NOT NULL DEFAULT 0")
        conn.commit()
        logger.debug("Database schema migrated successfully")
    except sqlite3.Error as e:
        if "duplicate column name" not in str(e).lower():
            logger.error(f"Database migration error: {e}")
            st.error(f"Database migration error: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def init_db():
    logger.info("Initializing database")
    try:
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                api_calls INTEGER NOT NULL DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                schedule_time TEXT NOT NULL,
                reminder_minutes INTEGER NOT NULL DEFAULT 60,
                reminder_sent BOOLEAN NOT NULL DEFAULT 0
            )
        """)
        # Add default admin account if it doesn't exist
        c.execute("SELECT email FROM users WHERE email = 'admin'")
        if not c.fetchone():
            hashed = pwd_context.hash("pass99()")
            c.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", 
                     ('admin', hashed, 'admin'))
        conn.commit()
        logger.debug("Database tables created successfully with admin account")
        migrate_db()  # Run migration for existing DBs
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        st.error(f"Database initialization error: {e}")
        raise
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def add_user(email: str, password: str, role="user"):
    logger.info(f"Attempting to add user: {email}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        hashed = pwd_context.hash(password)
        c.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (email, hashed, role))
        conn.commit()
        logger.debug(f"User {email} added successfully")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"User {email} already exists")
        return False
    except sqlite3.Error as e:
        logger.error(f"Database error during user addition: {e}")
        st.error(f"Database error during user addition: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def verify_user(email: str, password: str):
    logger.info(f"Verifying user: {email}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        if row and pwd_context.verify(password, row[0]):
            logger.debug(f"User {email} verified successfully")
            return True
        logger.warning(f"Invalid credentials for user: {email}")
        return False
    except sqlite3.Error as e:
        logger.error(f"Database error during user verification: {e}")
        st.error(f"Database error during user verification: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def get_user_role(email: str):
    logger.info(f"Fetching role for user: {email}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        role = row[0] if row else None
        logger.debug(f"User {email} role: {role}")
        return role
    except sqlite3.Error as e:
        logger.error(f"Database error fetching user role: {e}")
        st.error(f"Database error fetching user role: {e}")
        return None
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def get_api_calls(email: str):
    logger.info(f"Fetching API calls for user: {email}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT api_calls FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        calls = row[0] if row else 0
        logger.debug(f"API calls for {email}: {calls}")
        return calls
    except sqlite3.Error as e:
        logger.error(f"Database error fetching API call count: {e}")
        st.error(f"Database error fetching API call count: {e}")
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def increment_api_calls(email: str):
    logger.info(f"Incrementing API calls for user: {email}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET api_calls = api_calls + 1 WHERE email = ?", (email,))
        conn.commit()
        logger.debug(f"API calls incremented for {email}")
    except sqlite3.Error as e:
        logger.error(f"Database error incrementing API call count: {e}")
        st.error(f"Database error incrementing API call count: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def schedule_post(user_email, platform, content, schedule_time, reminder_minutes=60):
    logger.info(f"Scheduling post for user: {user_email}, platform: {platform}, reminder: {reminder_minutes} min before")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Ensure schedule_time is stored in IST ISO format
        if isinstance(schedule_time, datetime):
            schedule_time = schedule_time.astimezone(IST).isoformat()
        c.execute(
            "INSERT INTO scheduled_posts (user_email, platform, content, schedule_time, reminder_minutes) VALUES (?, ?, ?, ?, ?)",
            (user_email, platform, content, schedule_time, reminder_minutes)
        )
        conn.commit()
        logger.debug(f"Post scheduled successfully for {user_email} on {platform} at {schedule_time}")
    except sqlite3.Error as e:
        logger.error(f"Database error scheduling post: {e}")
        st.error(f"Database error scheduling post: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def get_user_scheduled_posts(user_email):
    logger.info(f"Fetching scheduled posts for user: {user_email}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT id, platform, content, schedule_time, reminder_minutes FROM scheduled_posts WHERE user_email = ? ORDER BY schedule_time",
            (user_email,)
        )
        posts = c.fetchall()
        logger.debug(f"Retrieved {len(posts)} scheduled posts for {user_email}")
        return posts
    except sqlite3.Error as e:
        logger.error(f"Database error fetching scheduled posts: {e}")
        st.error(f"Database error fetching scheduled posts: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def get_reminder_posts():
    """
    Fetch posts where reminder is due: schedule_time - reminder_minutes <= now (IST) and reminder not sent.
    Returns list of (user_email, platform, content, schedule_time, reminder_minutes, id)
    """
    logger.info("Fetching due reminder posts")
    now = datetime.now(IST).isoformat()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT user_email, platform, content, schedule_time, reminder_minutes, id
            FROM scheduled_posts
            WHERE reminder_sent = 0
            AND schedule_time > ?
            AND ? >= datetime(schedule_time, '-' || reminder_minutes || ' minutes')
            ORDER BY schedule_time
        """, (now, now))
        posts = c.fetchall()
        logger.debug(f"Retrieved {len(posts)} due reminder posts")
        return posts
    except sqlite3.Error as e:
        logger.error(f"Database error fetching reminder posts: {e}")
        st.error(f"Database error fetching reminder posts: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def mark_reminder_sent(post_id):
    """
    Mark a post's reminder as sent.
    """
    logger.info(f"Marking reminder sent for post ID: {post_id}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE scheduled_posts SET reminder_sent = 1 WHERE id = ?", (post_id,))
        conn.commit()
        logger.debug(f"Reminder marked sent for post {post_id}")
    except sqlite3.Error as e:
        logger.error(f"Database error marking reminder sent: {e}")
        st.error(f"Database error marking reminder sent: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def get_all_users():
    logger.info("Fetching all users")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT email, role, api_calls FROM users")
        users = c.fetchall()
        logger.debug(f"Retrieved {len(users)} users")
        return users
    except sqlite3.Error as e:
        logger.error(f"Database error fetching all users: {e}")
        st.error(f"Database error fetching all users: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def get_all_scheduled_posts():
    logger.info("Fetching all scheduled posts")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, user_email, platform, content, schedule_time, reminder_minutes FROM scheduled_posts ORDER BY schedule_time")
        posts = c.fetchall()
        logger.debug(f"Retrieved {len(posts)} scheduled posts")
        return posts
    except sqlite3.Error as e:
        logger.error(f"Database error fetching all scheduled posts: {e}")
        st.error(f"Database error fetching all scheduled posts: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def delete_scheduled_post(post_id):
    logger.info(f"Deleting scheduled post with ID: {post_id}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
        conn.commit()
        logger.debug(f"Scheduled post {post_id} deleted successfully")
    except sqlite3.Error as e:
        logger.error(f"Database error deleting scheduled post: {e}")
        st.error(f"Database error deleting scheduled post: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")