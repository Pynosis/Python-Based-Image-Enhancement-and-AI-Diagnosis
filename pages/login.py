import streamlit as st
from modules.auth import login
from datetime import datetime, timedelta

def show(cookie_manager=None):
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        }

/* ...all your existing rules below, unchanged... */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(div.st-key-login_card) {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 40px 48px 32px 48px;
            max-width: 560px;
            margin: 16px auto;
        }
        .login-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .login-logo {
            font-size: 18px;
            font-weight: 800;
            letter-spacing: 1px;
            color: #0d1b2a;
        }
        .login-title {
            font-size: 30px;
            font-weight: 800;
            color: #0d1b2a;
            text-align: center;
            margin-top:32px;
        }
        div[data-testid="stTextInput"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        div[data-testid="stTextInput"] > div {
            background: #f7f8fa !important;
            border: 1px solid #d8dce1 !important;
            border-radius: 25px !important;
            overflow: hidden !important;
        }
        .stTextInput input {
            border: none !important;
            background: transparent !important;
            padding: 14px 22px !important;
            font-size: 14px !important;
            color: #444 !important;
        }
        div[data-testid="stTextInput"] button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        .stTextInput input:focus {
            border-color: #0d1b2a !important;
            box-shadow: 0 0 0 2px rgba(13,27,42,0.08) !important;
            
        }
        .forgot-link {
            text-align: left;
            font-size: 13px;
            color: #6b7280;
            margin-top: -8px;
            margin-bottom: 20px;
            cursor: pointer;
            text-decoration:underline;
        }
        .forgot-link:hover {
            color: #028090 !important;
            text-decoration: underline;
        }
        div[data-testid="stFormSubmitButton"] button {
            background-color: #0d1b2a !important;
            color: white !important;
            border-radius: 25px !important;
            width: 100% !important;
            padding: 14px !important;
            font-size: 16px !important;
            font-weight: 800 !important;
            border: none !important;
            cursor: pointer !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #1b3a5c !important;
        }
        div[data-testid="stButton"] button {
            background: none !important;
            border: none !important;
            box-shadow: none !important;
            color: #0d1b2a !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            width: auto !important;
            display: block;
        }
        div[data-testid="stButton"] button:hover {
            color: #028090 !important;
            background: none !important;
        }
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
        div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        }
        div.st-key-goto_signup {
        display: flex;
        justify-content: center;
        margin-top: 4px;
}
div.st-key-goto_signup button {
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    color: #0d1b2a !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    padding: 0 !important;
    cursor: pointer;
}
div.st-key-goto_signup button:hover {
    color: #028090 !important;
    text-decoration: underline;
}
div.st-key-goto_signup button p {
    font-size: 14px !important;
    font-weight: 700 !important;
}        
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])

    with col2:
        with st.container(key="login_card", border=True):
            st.markdown('<div class="login-title">Painosis Login</div>', unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("", placeholder="username or email")
                password = st.text_input("", placeholder="password", type="password")
                st.markdown('<div class="forgot-link">Forgot Username or Password?</div>',unsafe_allow_html=True)
                submitted = st.form_submit_button("LOGIN", use_container_width=True)
                if submitted:
                    if not username or not password:
                        st.error("Please fill in all fields.")
                    else:
                        with st.spinner("Logging in..."):
                            success, message = login(username, password)

                        if success:
                            if cookie_manager:
                                cookie_manager.set(
                                    "session_token",
                                    st.session_state["session_token"],
                                    expires_at=datetime.now() + timedelta(hours=24)
                                )

                            role = st.session_state.role
                            if role == "admin":
                                st.session_state.page = "admin"
                            elif role in ("doctor", "radiologist"):
                                st.session_state.page = "upload"
                            elif role == "researcher":
                                st.session_state.page = "upload"

                            st.rerun()

                        else:
                            if "pending" in message.lower() or "rejected" in message.lower():
                                st.session_state.page = "pending"
                                st.session_state.pending_message = message
                                st.rerun()
                            else:
                                st.error(message)

            if st.button("New User? create an account", key="goto_signup",  use_container_width=False):
                st.session_state.page = "signup"
                st.rerun()