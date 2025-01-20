import streamlit as st
from datetime import datetime
from auth_manager import AuthManager
from dashboard_manager import DashboardManager
from utils import require_auth, initialize_dashboard_state, clear_month_cache

class ExpenseApp:
    def __init__(self):
        # Configure Streamlit page
        st.set_page_config(
            page_title="Expense Management",
            page_icon="💰",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        self.initialize_session_state()

    def initialize_session_state(self):
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'auth_manager' not in st.session_state:
            st.session_state.auth_manager = AuthManager()
        if 'dashboard_manager' not in st.session_state:
            st.session_state.dashboard_manager = DashboardManager()
        initialize_dashboard_state()

    @require_auth
    def render_dashboard(self):
        # Create main page layout
        header_col1, header_col2, header_col3 = st.columns([2, 0.5, 0.5])
        
        # Welcome message in first column
        with header_col1:
            st.title(f"Welcome, {st.session_state.user_data['name']}")
            st.write(f"{st.session_state.user_data['role']}")
        
        # Year selector in middle column
        with header_col2:
            years = st.session_state.dashboard_manager.get_available_years()
            year = st.selectbox(
                "Select Year",
                options=years,
                index=years.index(st.session_state.selected_year),
                key="year_selector",
                label_visibility="collapsed"
            )
            
            if year != st.session_state.selected_year:
                st.session_state.selected_year = year
                clear_month_cache()
                st.rerun()
        
        # Logout button in last column, aligned to right
        with header_col3:
            st.write("")  # Add some spacing
            col1, col2 = st.columns([0.5, 0.5])
            with col2:
                if st.button("Logout", type="secondary", use_container_width=True):
                    for key in st.session_state.keys():
                        del st.session_state[key]
                    st.rerun()

        # Add separator
        st.markdown("---")
        
        # Month grid
        self.render_month_grid()

    def render_month_grid(self):
        """Render the grid of months with expenses"""
        selected_year = st.session_state.selected_year
        teacher_id = st.session_state.user_data['teacher_id']
        
        # Fetch all months' data at once
        all_months_data = st.session_state.dashboard_manager.get_all_months_status(
            selected_year,
            teacher_id
        )
        
        # Create a 3x4 grid for months
        for row in range(4):
            cols = st.columns(3)
            for col in range(3):
                month_num = row * 3 + col + 1
                if month_num <= 12:
                    with cols[col]:
                        month_data = all_months_data[month_num]
                        month_name = datetime.strptime(f"{month_num}", "%m").strftime("%B")
                        st.subheader(month_name)
                        
                        # Status indicator at the top
                        status = month_data['status'].replace('_', ' ').title()
                        st.markdown(f'<div style="background-color: #f0f2f6; padding: 8px; border-radius: 4px;">{status}</div>', unsafe_allow_html=True)
                        
                        # Amount and entries on same line
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"£{month_data['total_amount']:.2f}")
                        with col2:
                            st.write(f"{month_data['entry_count']} entries")
                        
                        # View details button
                        st.button("View Details", key=f"view_{month_num}", use_container_width=True)

    def render_login_page(self):
        st.markdown("# 📊 Expense Manager")
        st.markdown("---")
        
        with st.form("login_form", clear_on_submit=False):
            teacher_id = st.text_input("Teacher ID", placeholder="Enter your ID")
            pin = st.text_input("PIN", type="password", placeholder="Enter your PIN")
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                success, message = st.session_state.auth_manager.authenticate(teacher_id, pin)
                if success:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error(message)

    def render_expense_form(self):
        st.markdown("### Expense Form")
        month_name = datetime.strptime(str(st.session_state.selected_month), "%m").strftime("%B")
        st.markdown(f"**{month_name} {st.session_state.selected_year}**")
        
        if st.button("← Back to Dashboard"):
            st.session_state.current_page = 'dashboard'
            st.rerun()
        
        st.markdown("---")
        st.info("Expense form implementation coming soon...")

    def run(self):
        if not st.session_state.authenticated:
            self.render_login_page()
        elif st.session_state.current_page == 'dashboard':
            self.render_dashboard()
        elif st.session_state.current_page == 'expense_form':
            self.render_expense_form()

if __name__ == "__main__":
    app = ExpenseApp()
    app.run()