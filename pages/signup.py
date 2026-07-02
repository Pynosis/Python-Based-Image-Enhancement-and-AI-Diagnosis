import os
import streamlit as st
from modules.auth import register_user
from modules.encryption import encrypt_file_to_disk


def show():
    st.markdown("""
        <style>
        .signup-title {
            font-size: 28px;
            font-weight: 700;
            color: #0d1b2a;
            text-align: center;
            margin-bottom: 8px;
        }
        .signup-subtitle {
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
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #028090 !important;
        }
        .login-link {
            text-align: center;
            font-size: 14px;
            margin-top: 24px;
            color: #555;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.markdown('<div class="signup-title">Create Account</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="signup-subtitle">Medical Image Enhancement & AI Diagnosis</div>',
                    unsafe_allow_html=True)

        fullname  = st.text_input("", placeholder="Full Name")
        username  = st.text_input("", placeholder="Username")
        email     = st.text_input("", placeholder="Email Address")
        password  = st.text_input("", placeholder="Password", type="password")
        confirm   = st.text_input("", placeholder="Confirm Password", type="password")
        role      = st.selectbox("Role", ["doctor", "radiologist", "researcher"])
        license_file = None
        if role in ("doctor", "radiologist"):
            st.markdown("**Upload PMDC License**")
            license_file = st.file_uploader(
                "Accepted formats: PDF, JPG, PNG",
                type=["pdf", "jpg", "jpeg", "png"]
                )
        signup = st.button("Create Account")


        

        # ── Validation + submission ────────────────────────────
        if signup:

            # 1. check empty fields
            if not fullname or not username or not email or not password or not confirm:
                st.error("Please fill in all fields.")

            # 2. check passwords match
            elif password != confirm:
                st.error("Passwords do not match.")

            # 3. minimum password length
            elif len(password) < 8:
                st.error("Password must be at least 8 characters.")

            # 4. doctor/radiologist must upload license
            elif role in ("doctor", "radiologist") and not license_file:
                st.error("Please upload your PMDC license to continue.")

            else:
                # ── Save license file encrypted to disk ────────
                license_path = None

                if license_file and role in ("doctor", "radiologist"):
                    # create uploads folder if it doesn't exist
                    os.makedirs("uploads/licenses", exist_ok=True)

                    # build a safe file path using username
                    ext = license_file.name.split(".")[-1]
                    save_path = f"uploads/licenses/{username}_pmdc.{ext}"

                    # read raw bytes from uploaded file
                    file_bytes = license_file.read()

                    # encrypt and save to disk
                    encrypt_file_to_disk(file_bytes, save_path)
                    license_path = save_path

                # ── Call register_user from auth.py ────────────
                with st.spinner("Creating your account..."):
                    success, message = register_user(
                        username=username,
                        email=email,
                        password=password,
                        full_name=fullname,
                        role=role,
                        pmdc_license_file_path=license_path
                    )

                # ── React to result ────────────────────────────
                if success:
                    st.success(message)

                    if role in ("doctor", "radiologist"):
                        # show pending message and redirect
                        st.info("Redirecting to verification page...")
                        st.session_state.pending_message = message
                        st.session_state.page = "pending"
                    else:
                        # researcher — auto approved, go to login
                        st.info("Redirecting to login...")
                        st.session_state.page = "login"

                    st.rerun()

                else:
                    st.error(message)

        # ── Back to login ──────────────────────────────────────
        st.markdown('<div class="login-link">Already have an account?</div>',
                    unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            if st.button("Log In", key="goto_login", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()