"""
seed_admin.py
Run this ONCE from the terminal to create the first (and only)
admin account. There is no UI path to register as admin — this
is intentional, it's the only safe way to bootstrap an admin.

Usage:
    python seed_admin.py
"""

import bcrypt
import getpass
from modules.database import get_db_connection


def seed_admin():
    print("=== Painsosis — Admin Account Setup ===\n")

    # check if an admin already exists
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username FROM users WHERE role = 'admin'")
    existing = cursor.fetchall()

    if existing:
        print("An admin account already exists:")
        for row in existing:
            print(f"  - {row['username']} (id: {row['id']})")
        confirm = input("\nCreate another admin anyway? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            cursor.close()
            conn.close()
            return

    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip()
    full_name = input("Admin full name: ").strip()
    password = getpass.getpass("Admin password: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if password != password_confirm:
        print("\nPasswords do not match. Aborted.")
        cursor.close()
        conn.close()
        return

    if len(password) < 8:
        print("\nPassword must be at least 8 characters. Aborted.")
        cursor.close()
        conn.close()
        return

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        cursor.execute(
            """INSERT INTO users
               (username, email, password_hash, full_name, role, is_approved, is_active)
               VALUES (%s, %s, %s, %s, 'admin', TRUE, TRUE)""",
            (username, email, password_hash, full_name)
        )
        conn.commit()
        print(f"\n✓ Admin account '{username}' created successfully.")
    except Exception as e:
        print(f"\n✗ Failed to create admin: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    seed_admin()