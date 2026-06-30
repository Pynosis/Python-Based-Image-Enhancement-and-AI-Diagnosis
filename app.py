import streamlit as st

st.set_page_config(
    page_title="Painosis",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---- Hide default Streamlit UI ----
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

# ---- Session state initialization ----
defaults = {
    "logged_in": False,
    "username": None,
    "name": None,
    "role": None,
    "user_id": None,
    "page": "login"
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---- Routing ----
if not st.session_state.logged_in:
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
    role = st.session_state.role

    if role == "Admin":
        if st.session_state.page == "admin":
            from pages.admin import show
            show()
    else:
        if st.session_state.page == "upload":
            from pages.uploads import show
            show()
        elif st.session_state.page == "history":
            from pages.history import show
            show()
        elif st.session_state.page == "results":
            from pages.results import show
            show()
        elif st.session_state.page == "profile":
            from pages.profile import show
            show()
        else:
            st.session_state.page = "upload"
            st.rerun()