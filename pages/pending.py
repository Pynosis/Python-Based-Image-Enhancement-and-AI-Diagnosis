import streamlit as st


def show():
    st.markdown("""
        <style>
        .pending-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-color: #f0f2f6;
        }
        .pending-box {
            background: white;
            padding: 50px 40px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            width: 100%;
            max-width: 480px;
            text-align: center;
        }
        .pending-icon { font-size: 56px; margin-bottom: 16px; }
        .pending-title {
            font-size: 24px;
            font-weight: 700;
            color: #0d1b2a;
            margin-bottom: 12px;
        }
        .pending-message {
            font-size: 14px;
            color: #666;
            line-height: 1.7;
            margin-bottom: 28px;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        message = st.session_state.get("pending_message", "")

        # determine which screen to show based on the message
        if "rejected" in message.lower():
            st.markdown('<div class="pending-icon">❌</div>', unsafe_allow_html=True)
            st.markdown('<div class="pending-title">Registration Rejected</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="pending-message">{message}</div>',
                        unsafe_allow_html=True)
            st.markdown(
                '<div class="pending-message">Please contact the admin if you believe this is an error.</div>',
                unsafe_allow_html=True
            )

        elif "suspended" in message.lower():
            st.markdown('<div class="pending-icon">🚫</div>', unsafe_allow_html=True)
            st.markdown('<div class="pending-title">Account Suspended</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="pending-message">{message}</div>',
                        unsafe_allow_html=True)

        else:
            # default: pending verification
            st.markdown('<div class="pending-icon">⏳</div>', unsafe_allow_html=True)
            st.markdown('<div class="pending-title">Awaiting Verification</div>',
                        unsafe_allow_html=True)
            st.markdown(
                '<div class="pending-message">'
                'Your PMDC license has been submitted and is currently under review by the admin. '
                'You will be able to log in once your account is approved. '
                'This usually takes 1–2 business days.'
                '</div>',
                unsafe_allow_html=True
            )

        # back to login button
        if st.button("← Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.session_state.pending_message = ""
            st.rerun()
