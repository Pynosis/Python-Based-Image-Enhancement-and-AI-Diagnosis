import streamlit as st
from modules.database import execute_query, execute_write
from modules.auth import require_auth, require_role
from modules.audit import log_action, USER_APPROVED, USER_REJECTED, USER_SUSPENDED, USER_ACTIVATED, USER_DELETED
from datetime import datetime
from modules.encryption import decrypt_file_from_disk


# ── Database functions ─────────────────────────────────────────

def get_dashboard_stats():
    total   = execute_query("SELECT COUNT(*) as total FROM users", fetch_one=True)
    active  = execute_query("SELECT COUNT(*) as total FROM users WHERE is_active = 1", fetch_one=True)
    pending = execute_query(
        "SELECT COUNT(*) as total FROM users WHERE is_approved = 0 AND role IN ('doctor','radiologist') AND rejection_reason IS NULL",
        fetch_one=True
    )
    return total, active, pending


def show_license(file_path, username):
    try:
        ext        = file_path.split(".")[-1].lower()
        file_bytes = decrypt_file_from_disk(file_path)
        if ext in ("jpg", "jpeg", "png"):
            st.image(file_bytes, caption=f"PMDC License — {username}")
            st.download_button(
                label="⬇️ Download License",
                data=file_bytes,
                file_name=f"{username}_pmdc.{ext}",
                mime=f"image/{ext}",
                key=f"dl_{username}"
            )
        elif ext == "pdf":
            st.download_button(
                label="📄 Download License PDF",
                data=file_bytes,
                file_name=f"{username}_pmdc.pdf",
                mime="application/pdf",
                key=f"dl_{username}"
            )
    except Exception as e:
        st.error(f"Could not load license file: {e}")


def get_pending_approvals():
    return execute_query(
        """SELECT full_name, username, email, role, pmdc_license_file_path, created_at
           FROM users
           WHERE is_approved = 0
           AND role IN ('doctor', 'radiologist')
           AND rejection_reason IS NULL""",
        fetch_all=True
    )


def get_all_users():
    return execute_query(
        """SELECT id, full_name, username, email, role,
                  is_approved, is_active, last_login, created_at
           FROM users
           WHERE role != 'admin'
           ORDER BY created_at DESC""",
        fetch_all=True
    )


def approve_doctor(doctor_username):
    execute_write(
        """UPDATE users
           SET is_approved = 1,
               approved_by = %s,
               approved_at = %s
           WHERE username = %s""",
        (st.session_state.user_id, datetime.utcnow(), doctor_username)
    )
    log_action(st.session_state.user_id, st.session_state.username,
               st.session_state.role, USER_APPROVED,
               f"Approved doctor: {doctor_username}")


def reject_doctor(doctor_username, reason):
    execute_write(
        """UPDATE users
           SET rejection_reason = %s,
               approved_by = %s,
               approved_at = %s
           WHERE username = %s""",
        (reason, st.session_state.user_id, datetime.utcnow(), doctor_username)
    )
    log_action(st.session_state.user_id, st.session_state.username,
               st.session_state.role, USER_REJECTED,
               f"Rejected doctor: {doctor_username}. Reason: {reason}")


def suspend_user(username):
    execute_write(
        "UPDATE users SET is_active = 0, session_token = NULL WHERE username = %s",
        (username,)
    )
    log_action(st.session_state.user_id, st.session_state.username,
               st.session_state.role, USER_SUSPENDED,
               f"Suspended user: {username}")


def activate_user(username):
    execute_write(
        "UPDATE users SET is_active = 1 WHERE username = %s",
        (username,)
    )
    log_action(st.session_state.user_id, st.session_state.username,
               st.session_state.role, USER_ACTIVATED,
               f"Activated user: {username}")


def delete_user(username):
    execute_write("DELETE FROM users WHERE username = %s", (username,))
    log_action(st.session_state.user_id, st.session_state.username,
               st.session_state.role, USER_DELETED,
               f"Deleted user: {username}")


# ── UI ─────────────────────────────────────────────────────────

def show():
    require_auth()
    require_role("admin")

    st.markdown("""
        <style>
        [data-testid="stMetric"] {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        [data-testid="stMetricValue"] {
            font-size: 36px;
            font-weight: 700;
            color: #0d1b2a;
        }
        [data-testid="stMetricLabel"] {
            font-size: 14px;
            color: #888;
            font-weight: 500;
        }
        </style>
    """, unsafe_allow_html=True)

    # ── Header ─────────────────────────────────────────────────
    st.markdown("# 🧠 Admin Dashboard")
    st.markdown("Welcome back, **{}**".format(st.session_state.full_name))
    st.divider()

    # ── Stats ──────────────────────────────────────────────────
    total, active, pending = get_dashboard_stats()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Users", total["total"])
    with col2:
        st.metric("Active Users", active["total"])
    with col3:
        st.metric("Pending Approvals", pending["total"])

    st.divider()

    # ── Tabs ───────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["⏳ Pending Approvals", "👥 User Management"])

    # ── Tab 1: Pending approvals ───────────────────────────────
    with tab1:
        st.markdown("### Doctors & Radiologists awaiting verification")
        doctors = get_pending_approvals()

        if not doctors:
            st.info("No pending approvals right now.")
        else:
            for doctor in doctors:
                with st.expander(
                    f"👤 {doctor['full_name']} ({doctor['role']}) — {doctor['email']}"
                ):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Username:** {doctor['username']}")
                        st.write(f"**Email:** {doctor['email']}")
                        st.write(f"**Role:** {doctor['role'].capitalize()}")
                        st.write(f"**Registered:** {doctor['created_at']}")
                    with col_b:
                        if doctor["pmdc_license_file_path"]:
                            st.write("**PMDC License:** Uploaded ✅")
                            show_license(
                                doctor["pmdc_license_file_path"],
                                doctor["username"]
                            )
                        else:
                            st.write("**PMDC License:** Not uploaded ❌")

                    st.markdown("---")
                    col_approve, col_reject = st.columns(2)

                    with col_approve:
                        if st.button("✅ Approve",
                                     key=f"approve_{doctor['username']}",
                                     use_container_width=True):
                            approve_doctor(doctor["username"])
                            st.success(f"{doctor['full_name']} approved!")
                            st.rerun()

                    with col_reject:
                        reason = st.text_input(
                            "Rejection reason",
                            key=f"reason_{doctor['username']}",
                            placeholder="Enter reason before rejecting"
                        )
                        if st.button("❌ Reject",
                                     key=f"reject_{doctor['username']}",
                                     use_container_width=True):
                            if reason:
                                reject_doctor(doctor["username"], reason)
                                st.success(f"{doctor['full_name']} rejected.")
                                st.rerun()
                            else:
                                st.error("Please enter a rejection reason first.")

    # ── Tab 2: User management ─────────────────────────────────
    with tab2:
        st.markdown("### All Users")
        users = get_all_users()

        if not users:
            st.info("No users found.")
        else:
            for user in users:
                with st.expander(
                    f"{'🟢' if user['is_active'] else '🔴'} "
                    f"{user['full_name']} — {user['role'].capitalize()}"
                ):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Username:** {user['username']}")
                        st.write(f"**Email:** {user['email']}")
                        st.write(f"**Role:** {user['role'].capitalize()}")
                        st.write(f"**Status:** {'Active ✅' if user['is_active'] else 'Suspended 🚫'}")
                        st.write(f"**Approved:** {'Yes ✅' if user['is_approved'] else 'No ❌'}")
                    with col_b:
                        last_login = user["last_login"] or "Never"
                        st.write(f"**Last Login:** {last_login}")
                        st.write(f"**Registered:** {user['created_at']}")

                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if user["is_active"]:
                            if st.button("🚫 Suspend",
                                         key=f"suspend_{user['username']}",
                                         use_container_width=True):
                                suspend_user(user["username"])
                                st.warning(f"{user['full_name']} suspended.")
                                st.rerun()
                        else:
                            if st.button("✅ Activate",
                                         key=f"activate_{user['username']}",
                                         use_container_width=True):
                                activate_user(user["username"])
                                st.success(f"{user['full_name']} activated.")
                                st.rerun()

                    with col3:
                        if st.button("🗑️ Delete",
                                    key=f"delete_{user['username']}",
                                    use_container_width=True,
                                    type="primary"):
                            delete_user(user["username"])
                            st.error(f"{user['full_name']} deleted.")
                            st.rerun()

    # ── Bottom navigation ──────────────────────────────────────────
    st.divider()
    col_l, col_m, col_r = st.columns([1, 1, 4])
    with col_l:
        if st.button("🔍 Audit Log", use_container_width=True):
            st.session_state.page = "audit_log"
            st.rerun()
    with col_m:
        if st.button("🚪 Logout", use_container_width=True):
            from modules.auth import logout
            logout()