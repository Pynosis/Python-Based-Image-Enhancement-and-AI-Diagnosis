"""
modules/audit.py
Silent background logger — records every significant action
taken by any user into the audit_logs table.
Admin-only access to view logs, enforced in the pages layer.

Usage anywhere in the app:
    from modules.audit import log_action
    log_action(user_id, username, role, "LOGIN_SUCCESS", "User logged in from Chrome")
"""

import sys
from datetime import datetime
from modules.database import get_db_connection


# ── Action constants ───────────────────────────────────────────
# Use these instead of raw strings so you never have a typo in a log entry.

# Auth
LOGIN_SUCCESS       = "LOGIN_SUCCESS"
LOGIN_FAILED        = "LOGIN_FAILED"
LOGOUT              = "LOGOUT"
REGISTER            = "REGISTER"
SESSION_EXPIRED     = "SESSION_EXPIRED"

# Scans
SCAN_UPLOADED       = "SCAN_UPLOADED"
SCAN_ENHANCED       = "SCAN_ENHANCED"

# Diagnosis
DIAGNOSIS_RUN       = "DIAGNOSIS_RUN"
REDIAGNOSIS_RUN     = "REDIAGNOSIS_RUN"

# Reports
REPORT_GENERATED    = "REPORT_GENERATED"
REPORT_DOWNLOADED   = "REPORT_DOWNLOADED"

# Admin actions
USER_APPROVED       = "USER_APPROVED"
USER_REJECTED       = "USER_REJECTED"
USER_SUSPENDED      = "USER_SUSPENDED"
USER_ACTIVATED      = "USER_ACTIVATED"
USER_DELETED        = "USER_DELETED"

# Access control
ACCESS_DENIED       = "ACCESS_DENIED"


def log_action(
    user_id: int | None,
    username: str,
    role: str,
    action: str,
    detail: str = "",
    ip_address: str = "unknown"
):
    """
    Records one action to the audit_logs table.
    NEVER raises an exception — a logging failure must never crash the app.

    Args:
        user_id:    The user's DB id. Pass None if user is not yet logged in
                    (e.g. a failed login attempt).
        username:   Stored as a snapshot so logs survive user deletion.
        role:       Stored as a snapshot (admin/doctor/radiologist/researcher).
        action:     Use the constants above e.g. LOGIN_SUCCESS, DIAGNOSIS_RUN.
        detail:     Optional free-text context. Never put raw scan data here.
        ip_address: User's IP — passed in from the Streamlit session.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit_logs
                (user_id, username_snapshot, role_snapshot, action, detail, ip_address, timestamp)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                username,
                role,
                action,
                detail,
                ip_address,
                datetime.utcnow()
            )
        )
        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        # Log to stderr but NEVER surface this error to the user
        print(f"[AUDIT ERROR] Failed to write log: {e}", file=sys.stderr)


def get_all_logs(
    filter_action: str = None,
    filter_username: str = None,
    filter_role: str = None,
    limit: int = 500
) -> list:
    """
    Fetch audit logs for the admin dashboard.
    Supports optional filters by action type, username, and role.
    Returns a list of dicts ordered by most recent first.
    """
    try:
        query = """
            SELECT
                id,
                user_id,
                username_snapshot,
                role_snapshot,
                action,
                detail,
                ip_address,
                timestamp
            FROM audit_logs
            WHERE 1=1
        """
        params = []

        if filter_action:
            query += " AND action = %s"
            params.append(filter_action)

        if filter_username:
            query += " AND username_snapshot LIKE %s"
            params.append(f"%{filter_username}%")

        if filter_role:
            query += " AND role_snapshot = %s"
            params.append(filter_role)

        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        return logs

    except Exception as e:
        print(f"[AUDIT ERROR] Failed to fetch logs: {e}", file=sys.stderr)
        return []
