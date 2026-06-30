"""
modules/database.py
Central MySQL connection layer. Uses a connection pool so Streamlit's
per-session reruns don't open a new raw connection every time.
"""

import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "painosis"),
}

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="medscan_pool",
            pool_size=10,
            **DB_CONFIG
        )
    return _pool


def get_db_connection():
    """
    Returns a connection from the pool.
    Caller is responsible for closing it (use try/finally or context manager).
    """
    return _get_pool().get_connection()


def execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """
    Convenience wrapper for simple SELECT queries.
    For INSERT/UPDATE/DELETE, use get_db_connection() directly so you
    control commit() explicitly.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None
        cursor.close()
        return result
    finally:
        conn.close()


def execute_write(query: str, params: tuple = ()):
    """
    Convenience wrapper for INSERT/UPDATE/DELETE.
    Commits automatically. Returns the cursor's lastrowid for INSERTs.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        cursor.close()
        return last_id
    finally:
        conn.close()


def test_connection() -> bool:
    """Quick health check — call this once at app startup if you want a sanity check."""
    try:
        conn = get_db_connection()
        conn.ping(reconnect=True)
        conn.close()
        return True
    except Exception as e:
        print(f"[DB ERROR] Connection failed: {e}")
        return False