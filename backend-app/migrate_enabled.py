"""
Migration script to add 'enabled' column to UserSessionWord and UserSessionVerb tables.
Run this once to migrate existing data.
"""

import sqlite3
import os

DATABASE_PATH = "/app/data/polingo.db"

# For local development, use relative path
if not os.path.exists(DATABASE_PATH):
    DATABASE_PATH = "data/polingo.db"


def migrate():
    if not os.path.exists(DATABASE_PATH):
        print(f"Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Check and add 'enabled' column to usersessionword table
    cursor.execute("PRAGMA table_info(usersessionword)")
    columns = [col[1] for col in cursor.fetchall()]

    if "enabled" not in columns:
        print("Adding 'enabled' column to usersessionword table...")
        cursor.execute(
            "ALTER TABLE usersessionword ADD COLUMN enabled BOOLEAN DEFAULT 1"
        )
        cursor.execute("UPDATE usersessionword SET enabled = 1 WHERE enabled IS NULL")
        print("Done!")
    else:
        print("'enabled' column already exists in usersessionword table")

    # Check and add 'enabled' column to usersessionverb table
    cursor.execute("PRAGMA table_info(usersessionverb)")
    columns = [col[1] for col in cursor.fetchall()]

    if "enabled" not in columns:
        print("Adding 'enabled' column to usersessionverb table...")
        cursor.execute(
            "ALTER TABLE usersessionverb ADD COLUMN enabled BOOLEAN DEFAULT 1"
        )
        cursor.execute("UPDATE usersessionverb SET enabled = 1 WHERE enabled IS NULL")
        print("Done!")
    else:
        print("'enabled' column already exists in usersessionverb table")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")


if __name__ == "__main__":
    migrate()
