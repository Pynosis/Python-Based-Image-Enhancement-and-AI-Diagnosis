"""
modules/auth.py
Handles everything auth-related:
  - User registration (doctor/radiologist + researcher)
  - Login with bcrypt password verification
  - Strict JWT session management
  - Role-based access control (RBAC)
  - Session timeout enforcement
  - Force logout on suspend/delete

Usage:
    from modules.auth import login, logout, require_auth, require_role, has_permission
"""

import os
import bcrypt
import jwt
import streamlit as st
from datetime import datetime, timedelta
from modules.database import get_db_connection, execute_query, execute_write
from modules.audit import log_action, LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, SESSION_EXPIRED, ACCESS_DENIED
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_change_this")
SESSION_TIMEOUT_MINUTES = 30


# ── Role permission map ────────────────────────────────────────
# Single source of truth for what each role can do.
# Use has_permission() to check these anywhere in the app.

ROLE_PERMISSIONS = {
    "admin": {
        "pages": ["upload", "admin", "audit_log"],
        "can_generate_report":  False,
        "can_download_report":  False,
        "can_diagnose":         False,
        "can_enhance":          False,
        "can_view_history":     False,
        "can_manage_users":     True,
        "can_view_audit":       True,
        "can_approve_users":    True,
    },
    "doctor": {
        "pages": ["upload", "results", "history"],
        "can_generate_report":  True,
        "can_download_report":  True,
        "can_diagnose":         True,
        "can_enhance":          True,
        "can_view_history":     True,
        "can_manage_users":     False,
        "can_view_audit":       False,
        "can_approve_users":    False,
    },
    "radiologist": {
        "pages": ["upload", "results", "history"],
        "can_generate_report":  True,
        "can_download_report":  True,
        "can_diagnose":         True,
        "can_enhance":          True,
        "can_view_history":     True,
        "can_manage_users":     False,
        "can_view_audit":       False,
        "can_approve_users":    False,
    },
    "researcher": {
        "pages": ["upload", "results"],
        "can_generate_report":  False,
        "can_download_report":  False,
        "can_diagnose":         True,
        "can_enhance":          True,
        "can_view_history":     False,
        "can_manage_users":     False,
        "can_view_audit":       False,
        "can_approve_users":    False,
    },
}


# ── Password helpers ───────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ── JWT helpers ────────────────────────────────────────────────

def _generate_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── Registration ───────────────────────────────────────────────

def register_user(
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str,
    pmdc_license_number: str = None,
    pmdc_license_file_path: str = None,
) -> tuple[bool, str]:
    """
    Registers a new user.
    - Doctor/Radiologist: is_approved = FALSE, waits for admin review
    - Researcher: is_approved = TRUE, can login immediately
    Returns (success: bool, message: str)
    """

    # check username and email are not already taken
    existing = execute_query(
        "SELECT id FROM users WHERE username = %s OR email = %s",
        (username, email),
        fetch_one=True
    )
    if existing:
        return False, "Username or email already exists."

    password_hash = hash_password(password)

    # doctors and radiologists must wait for admin approval
    # researchers are auto-approved
    is_approved = True if role == "researcher" else False

    try:
        execute_write(
            """
            INSERT INTO users
                (username, email, password_hash, full_name, role,
                 pmdc_license_number, pmdc_license_file_path, is_approved, is_active)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """,
            (username, email, password_hash, full_name, role,
             pmdc_license_number, pmdc_license_file_path, is_approved)
        )

        log_action(
            user_id=None,
            username=username,
            role=role,
            action="REGISTER",
            detail=f"New {role} registered. Approval required: {not is_approved}"
        )

        if role in ("doctor", "radiologist"):
            return True, "Registration submitted. Wait for admin to verify your PMDC license."
        else:
            return True, "Registration successful. You can now log in."

    except Exception as e:
        return False, f"Registration failed: {str(e)}"


# ── Login ──────────────────────────────────────────────────────

def login(username: str, password: str, ip_address: str = "unknown") -> tuple[bool, str]:
    """
    Authenticates a user and sets up st.session_state.
    Returns (success: bool, message: str)
    """

    user = execute_query(
        """SELECT id, username, password_hash, full_name, role,
                  is_approved, is_active, rejection_reason
           FROM users WHERE username = %s""",
        (username,),
        fetch_one=True
    )

    # user not found — same message as wrong password (security best practice)
    if not user:
        log_action(None, username, "unknown", LOGIN_FAILED,
                   f"Login attempt with unknown username: {username}", ip_address)
        return False, "Invalid username or password."

    # wrong password
    if not verify_password(password, user["password_hash"]):
        log_action(user["id"], username, user["role"], LOGIN_FAILED,
                   "Incorrect password", ip_address)
        return False, "Invalid username or password."

    # account suspended
    if not user["is_active"]:
        log_action(user["id"], username, user["role"], LOGIN_FAILED,
                   "Login attempt on suspended account", ip_address)
        return False, "Your account has been suspended. Contact the admin."

    # doctor/radiologist pending approval
    if user["role"] in ("doctor", "radiologist") and not user["is_approved"]:
        # check if rejected
        if user["rejection_reason"]:
            return False, f"Your registration was rejected. Reason: {user['rejection_reason']}"
        return False, "Your PMDC license is pending admin verification. Please wait."

    # ── all checks passed — create session ──

    token = _generate_token(user["id"])

    # store token in DB so admin can force-logout by nulling it
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET session_token = %s, last_login = %s WHERE id = %s",
        (token, datetime.utcnow(), user["id"])
    )
    conn.commit()
    cursor.close()
    conn.close()

    # write to streamlit session state
    st.session_state["authenticated"]  = True
    st.session_state["user_id"]        = user["id"]
    st.session_state["username"]       = user["username"]
    st.session_state["full_name"]      = user["full_name"]
    st.session_state["role"]           = user["role"]
    st.session_state["session_token"]  = token
    st.session_state["login_time"]     = datetime.utcnow().isoformat()
    st.session_state["last_activity"]  = datetime.utcnow().isoformat()

    log_action(user["id"], username, user["role"], LOGIN_SUCCESS,
               f"Logged in successfully", ip_address)

    return True, "Login successful."


# ── Logout ─────────────────────────────────────────────────────

def logout():
    """Clears session, nulls DB token, logs the action."""
    user_id  = st.session_state.get("user_id")
    username = st.session_state.get("username", "unknown")
    role     = st.session_state.get("role", "unknown")

    if user_id:
        # null the token in DB so it can't be reused
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET session_token = NULL WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()

        log_action(user_id, username, role, LOGOUT, "User logged out")

    st.session_state.clear()
    st.rerun()


# ── Session validation ─────────────────────────────────────────

def require_auth():
    """
    Call this at the TOP of every single page.
    Checks:
      1. Session state exists
      2. JWT token is valid and not expired
      3. Token matches what is stored in DB (catches force-logouts)
      4. Account is still active (catches suspensions)
      5. Inactivity timeout
    Stops the page entirely if any check fails.
    """

    # 1. check session state
    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access this page.")
        st.stop()

    token   = st.session_state.get("session_token")
    user_id = st.session_state.get("user_id")

    # 2. validate JWT
    payload = _decode_token(token)
    if not payload:
        st.error("Your session has expired. Please log in again.")
        log_action(user_id, st.session_state.get("username", "unknown"),
                   st.session_state.get("role", "unknown"), SESSION_EXPIRED)
        st.session_state.clear()
        st.stop()

    # 3. match token against DB (detects force-logout by admin)
    db_user = execute_query(
        "SELECT session_token, is_active FROM users WHERE id = %s",
        (user_id,),
        fetch_one=True
    )

    if not db_user or db_user["session_token"] != token:
        st.error("Your session was ended. Please log in again.")
        st.session_state.clear()
        st.stop()

    # 4. check account still active (catches mid-session suspension)
    if not db_user["is_active"]:
        st.error("Your account has been suspended. Contact the admin.")
        st.session_state.clear()
        st.stop()

    # 5. inactivity timeout
    last_activity = datetime.fromisoformat(st.session_state["last_activity"])
    if datetime.utcnow() - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        st.warning("You were logged out due to inactivity.")
        logout()
        st.stop()

    # ── all good — refresh activity timestamp ──
    st.session_state["last_activity"] = datetime.utcnow().isoformat()


# ── Role-based access control ──────────────────────────────────

def require_role(*allowed_roles: str):
    """
    Call AFTER require_auth() to lock a page to specific roles.

    Examples:
        require_role("admin")
        require_role("doctor", "radiologist")
        require_role("doctor", "radiologist", "admin")
    """
    role = st.session_state.get("role", "")
    if role not in allowed_roles:
        log_action(
            st.session_state.get("user_id"),
            st.session_state.get("username", "unknown"),
            role,
            ACCESS_DENIED,
            f"Role '{role}' attempted to access page restricted to: {allowed_roles}"
        )
        st.error(f"Access denied. This page is for: {', '.join(allowed_roles)} only.")
        st.stop()


def has_permission(permission: str) -> bool:
    """
    Check a specific permission for the current user's role.
    Use this to show/hide individual buttons and UI elements.

    Example:
        if has_permission("can_download_report"):
            st.download_button("Download PDF", ...)
    """
    role = st.session_state.get("role", "")
    return ROLE_PERMISSIONS.get(role, {}).get(permission, False)


def get_current_user() -> dict | None:
    """Returns the current logged-in user's session data as a dict."""
    if not st.session_state.get("authenticated"):
        return None
    return {
        "user_id":   st.session_state.get("user_id"),
        "username":  st.session_state.get("username"),
        "full_name": st.session_state.get("full_name"),
        "role":      st.session_state.get("role"),
    }
