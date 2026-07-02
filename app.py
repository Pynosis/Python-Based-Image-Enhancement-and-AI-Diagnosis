import streamlit as st


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
    "page":          "login"
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ── Routing ────────────────────────────────────────────────────
if not st.session_state.authenticated:
    # ── Public routes (no login required) ──
    if st.session_state.page == "login":
        from pages.login import show
        show()

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
    # ── Protected routes (login required) ──
    from modules.auth import require_auth
    require_auth()  # validates session on every page load

    role = st.session_state.role

    # ── Admin routes ──
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

    # ── Doctor / Radiologist routes ──
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

    # ── Researcher routes ──
    elif role == "researcher":
        if st.session_state.page == "upload":
            from pages.uploads import show
            show()
        elif st.session_state.page == "results":
            from pages.results import show
            show()
        else:
            # researcher cannot access history, profile, admin, audit
            st.session_state.page = "upload"
            st.rerun()

    else:
        # unknown role — force logout
        st.session_state.clear()
        st.error("Unknown role. Please contact admin.")
        st.stop()