import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Painosis",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Hide default Streamlit UI ──────────────────────────────────
def hide_streamlit_ui():
    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none; }
        [data-testid="stSidebar"] { display: none; }
        [data-testid="collapsedControl"] { display: none; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .block-container { padding-top: 0rem; }
        </style>
    """, unsafe_allow_html=True)

hide_streamlit_ui()

# ── Cookie manager ─────────────────────────────────────────────
cookie_manager = stx.CookieManager()

# ── Session state initialization ───────────────────────────────
defaults = {
    "authenticated": False,
    "user_id":       None,
    "username":      None,
    "full_name":     None,
    "role":          None,
    "session_token": None,
    "login_time":    None,
    "last_activity": None,
    "page":          "login",
    "pending_message": ""
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ── Restore session from cookie on refresh ─────────────────────
if not st.session_state.authenticated:
    token = cookie_manager.get("session_token")
    if token:
        from modules.database import execute_query
        from modules.auth import _decode_token
        payload = _decode_token(token)
        if payload:
            user = execute_query(
                """SELECT id, username, full_name, role,
                          session_token, is_active
                   FROM users WHERE id = %s""",
                (payload["user_id"],),
                fetch_one=True
            )
            if user and user["session_token"] == token and user["is_active"]:
                st.session_state["authenticated"]  = True
                st.session_state["user_id"]        = user["id"]
                st.session_state["username"]       = user["username"]
                st.session_state["full_name"]      = user["full_name"]
                st.session_state["role"]           = user["role"]
                st.session_state["session_token"]  = token
                st.session_state["last_activity"]  = datetime.utcnow().isoformat()

                role = user["role"]
                if role == "admin":
                    st.session_state["page"] = "admin"
                else:
                    st.session_state["page"] = "upload"

# ── Routing ────────────────────────────────────────────────────
if not st.session_state.authenticated:
    if st.session_state.page == "login":
        from pages.login import show
        show(cookie_manager=cookie_manager)
    elif st.session_state.page == "signup":
        from pages.signup import show
        show()
    elif st.session_state.page == "pending":
        from pages.pending import show
        show()
    else:
        st.session_state.page = "login"
        st.rerun()

else:
    from modules.auth import require_auth
    require_auth()

    role = st.session_state.role

    if role == "admin":
        if st.session_state.page == "admin":
            from pages.admin import show
            show()
        elif st.session_state.page == "audit_log":
            from pages.audit_log import show
            show()
        else:
            st.session_state.page = "admin"
            st.rerun()

    elif role in ("doctor", "radiologist"):
        if st.session_state.page == "upload":
            from pages.uploads import show
            show()
        elif st.session_state.page == "results":
            from pages.results import show
            show()
        elif st.session_state.page == "history":
            from pages.history import show
            show()
        elif st.session_state.page == "profile":
            from pages.profile import show
            show()
        else:
            st.session_state.page = "upload"
            st.rerun()

    elif role == "researcher":
        if st.session_state.page == "upload":
            from pages.uploads import show
            show()
        elif st.session_state.page == "results":
            from pages.results import show
            show()
        else:
            st.session_state.page = "upload"
            st.rerun()

    else:
        st.session_state.clear()
        st.error("Unknown role. Please contact admin.")
        st.stop()
