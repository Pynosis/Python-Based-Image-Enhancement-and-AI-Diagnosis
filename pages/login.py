import streamlit as st

def show():
    st.markdown("""
        <style>
        .login-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-color: #f0f2f6;
        }
        .login-box {
            background: white;
            padding: 50px 40px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            width: 100%;
            max-width: 420px;
        }
        .login-title {
            font-size: 28px;
            font-weight: 700;
            color: #0d1b2a;
            text-align: center;
            margin-bottom: 8px;
        }
        .login-subtitle {
            font-size: 14px;
            color: #888;
            text-align: center;
            margin-bottom: 32px;
        }
        .stTextInput input {
            border-radius: 25px !important;
            border: 1px solid #e0e0e0 !important;
            padding: 12px 20px !important;
            font-size: 14px !important;
        }
        .stTextInput input:focus {
            border-color: #028090 !important;
            box-shadow: 0 0 0 2px rgba(2,128,144,0.1) !important;
        }
        div[data-testid="stFormSubmitButton"] button {
            background-color: #0d1b2a !important;
            color: white !important;
            border-radius: 25px !important;
            width: 100% !important;
            padding: 12px !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            border: none !important;
            cursor: pointer !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #028090 !important;
        }
        .forgot-link {
            text-align: right;
            font-size: 13px;
            color: #028090;
            cursor: pointer;
            margin-top: -10px;
            margin-bottom: 20px;
        }
        .signup-link {
            text-align: center;
            font-size: 14px;
            margin-top: 24px;
            color: #555;
        }
        .signup-link span {
            color: #028090;
            font-weight: 600;
            cursor: pointer;
        }
        </style>
    """, unsafe_allow_html=True)

    # Center the login box
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.markdown('<div class="login-title">Painosis Login</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Medical Image Enhancement & AI Diagnosis</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("", placeholder="Username or Email")
            password = st.text_input("", placeholder="Password", type="password")

            st.markdown('<div class="forgot-link">Forgot Username or Password?</div>', unsafe_allow_html=True)

            submitted = st.form_submit_button("Login")

            if submitted:
                if email == "" or password == "":
                    st.error("Please fill in all fields.")
                else:
                    # Temporary hardcoded login for testing
                    # Replace with DB auth later
                    if email == "doctor@gmail.com" and password == "123":
                        st.session_state.logged_in = True
                        st.session_state.username = "fizza"
                        st.session_state.name = "Fizza Baig"
                        st.session_state.role = "Doctor"
                        st.session_state.user_id = 1
                        st.session_state.page = "upload"
                        st.rerun()
                    elif email == "admin@gmail.com" and password == "123":
                        st.session_state.logged_in = True
                        st.session_state.username = "admin"
                        st.session_state.name = "Admin"
                        st.session_state.role = "Admin"
                        st.session_state.user_id = 2
                        st.session_state.page = "admin"
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")

        # Signup link
        st.markdown('<div class="signup-link">New User? <span id="signup">create an account</span></div>', unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            if st.button("Sign Up", key="goto_signup", use_container_width=True):
                st.session_state.page = "signup"
                st.rerun()