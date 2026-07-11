import os
import streamlit as st
from modules.auth import register_user
from modules.encryption import encrypt_file_to_disk


def show():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }
        div[data-testid="InputInstructions"] {
            display: none !important;
        }
        /* Remove default page padding */
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }

        /* Remove gap between columns */
        div[data-testid="stHorizontalBlock"] {
            gap: 0rem !important;
        }

        /* Remove padding inside each column */
        div[data-testid="column"] {
            padding: 0px !important;
        }

        /* Remove extra spacing between stacked elements */
        div[data-testid="stVerticalBlock"] {
            gap: 0.3rem !important;
        }

        /* Remove default margin around the app */
        .main {
            padding: 0rem !important;
        }
        div.st-key-left_panel {
            background: #f3f4f6;
            min-height: 100vh;
            padding: 32px 48px;
        }
        .brand-dot {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #ffffff;
            margin-bottom: 40px;
        }
        .tagline {
            font-size: 20px;
            font-weight: 700;
            color: #6b7280;
            line-height: 1.4;
            margin-bottom: 60px;
        }
        .image-placeholder {
            width: 100%;
            max-width: 320px;
            height: 360px;
            background: #e9eaee;
            border-radius: 12px;
        }

        div.st-key-right_panel {
            padding: 32px 80px 0px 80px;
            max-width: 560px;
            margin: 0 auto;
        }

        .signup-title {
            font-size: 30px;
            font-weight: 800;
            color: #0d1b2a;
            margin-bottom: 32px;
        }

        div[data-testid="stTextInput"] > div {
            background: #ffffff !important;
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
        div[data-testid="stSelectbox"] > div > div {
            border-radius: 25px !important;
            border: 1px solid #d8dce1 !important;
            background: #f7f8fa !important;
            overflow: hidden !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background: #f7f8fa !important;
            border: 1px solid #d8dce1 !important;
            box-shadow: none !important;
            min-height: 48px !important;
            display: flex !important;
            align-items: center !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div > div {
            font-size: 14px !important;
            color: #444 !important;
            font-weight: 400 !important;
            padding: 0 12px !important;
        }
        div[data-testid="stFileUploader"] {
            border-radius: 16px !important;
            border: 1px dashed #d8dce1 !important;
            background: #f7f8fa !important;
            padding: 8px !important;
        }

        div.st-key-create_account button {
            background-color: #0d1b2a !important;
            color: white !important;
            border-radius: 25px !important;
            width: 100% !important;
            padding: 14px !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            border: none !important;
            cursor: pointer !important;
        }
        div.st-key-create_account button:hover {
            background-color: #1b3a5c !important;
        }
        div.st-key-goto_login {
            display: flex;
            justify-content: center;
        }
        div.st-key-goto_login button {
            background: none !important;
            border: none !important;
            box-shadow: none !important;
            color: #0d1b2a !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            padding: 0 !important;
            cursor: pointer;
        }
        div.st-key-goto_login button:hover {
            color: #028090 !important;
            text-decoration: underline;
        }
        div.st-key-goto_login button p {
            font-size: 14px !important;
            font-weight: 700 !important;
        }  
        </style>
    """, unsafe_allow_html=True)

    left, right = st.columns([1, 1.6])

    with left:
        with st.container(key="left_panel"):
            st.markdown('<div class="brand-dot"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="tagline">We at Painosis are always fully focused on helping your child</div>',
                unsafe_allow_html=True
            )
            st.markdown('<div class="image-placeholder"></div>', unsafe_allow_html=True)

    with right:
        with st.container(key="right_panel"):
            st.markdown('<div class="signup-title">Sign Up</div>', unsafe_allow_html=True)

            fullname = st.text_input("Full Name", placeholder="Enter Full Name", label_visibility="collapsed")
            username = st.text_input("Username", placeholder="Enter your username", label_visibility="collapsed")
            email = st.text_input("Email", placeholder="Enter your Email", label_visibility="collapsed")
            role = st.selectbox("", ["Select Role", "Doctor", "Radiologist", "Researcher"], label_visibility="collapsed")
            password = st.text_input("Password", placeholder="Enter your password", type="password", label_visibility="collapsed")
            confirm = st.text_input("Confirm Password", placeholder="Enter your confirm password", type="password", label_visibility="collapsed")
            
            

            license_file = None
            if role in ("Doctor", "Radiologist"):
                license_file = st.file_uploader(
                    "Upload your PMDC License",
                    type=["pdf", "jpg", "jpeg", "png"],
                    label_visibility="collapsed"
                )

            agree = st.checkbox("I agree that this system is for diagnostic support only")

            signup = st.button("Sign Up", key="create_account", use_container_width=True)

            # ── Validation + submission ────────────────────────────
            if signup:

                if role == "Select Role":
                    st.error("Please select a role.")

                elif not fullname or not username or not email or not password or not confirm:
                    st.error("Please fill in all fields.")

                elif password != confirm:
                    st.error("Passwords do not match.")

                elif len(password) < 8:
                    st.error("Password must be at least 8 characters.")

                elif role in ("Doctor", "Radiologist") and not license_file:
                    st.error("Please upload your PMDC license to continue.")

                elif not agree:
                    st.error("You must agree to the terms to continue.")

                else:
                    license_path = None

                    if license_file and role in ("Doctor", "Radiologist"):
                        os.makedirs("uploads/licenses", exist_ok=True)
                        ext = license_file.name.split(".")[-1]
                        save_path = f"uploads/licenses/{username}_pmdc.{ext}"
                        file_bytes = license_file.read()
                        encrypt_file_to_disk(file_bytes, save_path)
                        license_path = save_path

                    with st.spinner("Creating your account..."):
                        success, message = register_user(
                            username=username,
                            email=email,
                            password=password,
                            full_name=fullname,
                            role=role,
                            pmdc_license_file_path=license_path
                        )

                    if success:
                        st.success(message)

                        if role in ("Doctor", "Radiologist"):
                            st.info("Redirecting to verification page...")
                            st.session_state.pending_message = message
                            st.session_state.page = "pending"
                        else:
                            st.info("Redirecting to login...")
                            st.session_state.page = "login"

                        st.rerun()

                    else:
                        st.error(message)

            if st.button("Already have an account? Login here.", key="goto_login", use_container_width=False):
                st.session_state.page = "login"
                st.rerun()