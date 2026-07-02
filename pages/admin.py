import streamlit as st
from modules.database import execute_query
from modules.auth import require_auth, require_role


def get_dashboard_status():
    total = execute_query("SELECT COUNT(*) as total FROM users", fetch_one=True)
    active = execute_query("SELECT COUNT(*) as total FROM users where is_active = 1", fetch_one = True )
    pending = execute_query("SELECT COUNT(*) as total FROM users where is_approved = 0", fetch_one=True)
    return total, active, pending

def show():
    require_auth()
    require_role("admin")
    total, active, pending = get_dashboard_status()
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
            """,unsafe_allow_html=True)
    st.markdown("# Admin Dashboard")
    st.markdown("Welcome back, **{}**".format(st.session_state.full_name))
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1: 
        st.metric("total users", total["total"])
    with col2: 
        st.metric("active users", active["total"])
    with col3:
        st.metric("pending users", pending["total"])

