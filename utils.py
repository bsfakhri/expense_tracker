# utils.py
import streamlit as st
from functools import wraps
from datetime import datetime
import time

def check_session_timeout():
    """Check if the session has timed out (30 minutes)."""
    if 'login_time' in st.session_state:
        if time.time() - st.session_state.login_time > 1800:  # 30 minutes
            logout()
            st.error("Session expired. Please login again.")
            st.stop()

def require_auth(func):
    """Decorator to require authentication for pages."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        check_session_timeout()
        if not st.session_state.get('authenticated'):
            st.error("Please login to access this page")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def require_admin(func):
    """Decorator to require admin role."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        check_session_timeout()
        if not st.session_state.get('authenticated'):
            st.error("Please login to access this page")
            st.stop()
        if st.session_state.user_data.get('role') != 'admin':
            st.error("Admin access required")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def logout():
    """Clear session state and log out user."""
    for key in st.session_state.keys():
        del st.session_state[key]
    st.experimental_rerun()

def initialize_dashboard_state():
    """Initialize dashboard-related session state variables"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'
    if 'selected_year' not in st.session_state:
        st.session_state.selected_year = datetime.now().year
    if 'selected_month' not in st.session_state:
        st.session_state.selected_month = None
    if 'dashboard_manager' not in st.session_state:
        st.session_state.dashboard_manager = None

def clear_month_cache():
    """Clear all month status cache entries"""
    keys_to_remove = [key for key in st.session_state.keys() if key.startswith('cache_')]
    for key in keys_to_remove:
        del st.session_state[key]