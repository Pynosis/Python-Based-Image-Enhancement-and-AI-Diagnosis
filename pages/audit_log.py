"""
pages/audit_log.py
Admin-only audit log viewer.
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from modules.auth import require_auth, require_role, get_current_user
from modules.database import execute_query


def get_audit_logs(filter_action=None, filter_username=None, filter_role=None, days=30):
    query = """
        SELECT id, username_snapshot, role_snapshot, action,
        detail, ip_address, timestamp
        FROM audit_logs
        WHERE timestamp >= %s
    """
    params = [datetime.utcnow() - timedelta(days=days)]

    if filter_action and filter_action != "All":
        query += " AND action = %s"
        params.append(filter_action)
    if filter_username:
        query += " AND username_snapshot LIKE %s"
        params.append(f"%{filter_username}%")
    if filter_role and filter_role != "All":
        query += " AND role_snapshot = %s"
        params.append(filter_role)

    query += " ORDER BY timestamp DESC LIMIT 1000"
    return execute_query(query, tuple(params), fetch_all=True)


def show():
    require_auth()
    require_role("admin")  # ← admin only

    user = get_current_user()

    st.markdown("""
        <style>
        [data-testid="stMetric"] {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 12px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("# 🔍 Audit Log")
    st.markdown(f"**{user['full_name']}** (Admin)")
    st.divider()

    col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 4])
    with col_nav1:
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.page = "admin"
            st.rerun()
    with col_nav2:
        if st.button("🚪 Logout", use_container_width=True):
            from modules.auth import logout
            logout()

    st.divider()
    st.markdown("### Filters")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filter_action = st.selectbox("Action", [
            "All", "LOGIN_SUCCESS", "LOGIN_FAILED", "LOGOUT",
            "REGISTER", "SCAN_UPLOADED", "SCAN_ENHANCED",
            "DIAGNOSIS_RUN", "REPORT_GENERATED", "REPORT_DOWNLOADED",
            "USER_APPROVED", "USER_REJECTED", "USER_SUSPENDED",
            "USER_ACTIVATED", "USER_DELETED", "ACCESS_DENIED"
        ])
    with col_f2:
        filter_role = st.selectbox("Role", ["All", "admin", "doctor", "radiologist", "researcher"])
    with col_f3:
        filter_username = st.text_input("Username", placeholder="Search...")
    with col_f4:
        days = st.selectbox("Period (days)", [7, 14, 30, 60, 90], index=2)

    logs = get_audit_logs(
        filter_action=filter_action,
        filter_username=filter_username if filter_username else None,
        filter_role=filter_role,
        days=int(days)
    )

    if logs:
        total        = len(logs)
        logins       = sum(1 for l in logs if l["action"] == "LOGIN_SUCCESS")
        diagnoses    = sum(1 for l in logs if l["action"] == "DIAGNOSIS_RUN")
        enhancements = sum(1 for l in logs if l["action"] == "SCAN_ENHANCED")
        reports      = sum(1 for l in logs if l["action"] == "REPORT_DOWNLOADED")

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Actions", total)
        with col2:
            st.metric("Logins", logins)
        with col3:
            st.metric("Diagnoses", diagnoses)
        with col4:
            st.metric("Enhancements", enhancements)
        with col5:
            st.metric("Reports", reports)

    st.divider()

    if not logs:
        st.info("No audit logs found for the selected filters.")
        return

    st.markdown(f"Showing **{len(logs)}** records from last **{days}** days")

    df = pd.DataFrame(logs)
    df.columns = ["ID", "Username", "Role", "Action", "Detail", "IP Address", "Timestamp"]

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(
        label="⬇️ Export to CSV",
        data=csv_buf.getvalue(),
        file_name=f"audit_log_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

    st.divider()

    action_icons = {
        "LOGIN_SUCCESS": "🟢", "LOGIN_FAILED": "🔴", "LOGOUT": "⚪",
        "DIAGNOSIS_RUN": "🔵", "SCAN_ENHANCED": "🟣",
        "REPORT_GENERATED": "🟡", "REPORT_DOWNLOADED": "🟡",
        "USER_APPROVED": "🟢", "USER_REJECTED": "🔴",
        "USER_SUSPENDED": "🔴", "USER_DELETED": "🔴",
        "ACCESS_DENIED": "🔴", "REGISTER": "🔵",
        "SCAN_UPLOADED": "🔵",
    }

    for log in logs:
        timestamp = log["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if log["timestamp"] else "Unknown"
        icon = action_icons.get(log["action"], "⚪")

        with st.expander(
            f"{icon} {log['action']} — {log['username_snapshot']} ({log['role_snapshot']}) — {timestamp}"
        ):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**User:** {log['username_snapshot']}")
                st.write(f"**Role:** {log['role_snapshot'].capitalize()}")
                st.write(f"**Action:** {log['action']}")
            with col_b:
                st.write(f"**Time:** {timestamp}")
                st.write(f"**IP:** {log['ip_address'] or 'Unknown'}")
                if log["detail"]:
                    st.write(f"**Detail:** {log['detail']}")
