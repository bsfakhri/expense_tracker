# dashboard_ui.py
import streamlit as st
import calendar
from datetime import datetime
from custom_styles import get_css

def inject_custom_css():
    """Inject custom CSS"""
    st.markdown(get_css(), unsafe_allow_html=True)

def render_header(user_name: str, role: str):
    """Render the dashboard header"""
    st.markdown(
        f'''
        <div class="header-container">
            <h1 style="margin: 0;">Welcome, {user_name}</h1>
            <div class="user-info">
                <span>{role}</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )

def render_year_selector(available_years: list, current_year: int) -> int:
    """Render a cleaner year selector"""
    year = st.selectbox(
        "Select Year",  # Providing a meaningful label
        options=available_years,
        index=available_years.index(current_year),
        key="year_selector",
        label_visibility="hidden"  # Hide the label but maintain accessibility
    )
    return year

def get_status_style(status: str) -> tuple:
    """Get status color and background"""
    status_styles = {
        'no_entries': ('gray', '#F3F4F6'),
        'draft': ('#1E40AF', '#DBEAFE'),
        'pending': ('#92400E', '#FEF3C7'),
        'approved': ('#065F46', '#D1FAE5'),
        'rejected': ('#991B1B', '#FEE2E2'),
        'error': ('#1F2937', '#F3F4F6')
    }
    return status_styles.get(status, status_styles['error'])

def render_month_card(month_num: int, month_data: dict, on_click) -> None:
    """Render an individual month card"""
    month_name = calendar.month_name[month_num]
    status = month_data['status']
    text_color, bg_color = get_status_style(status)
    
    with st.container():
        st.markdown(f'''
            <div class="expense-card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <h3 style="margin: 0; font-size: 1.25rem;">{month_name}</h3>
                    <div class="status-badge" style="color: {text_color}; background: {bg_color};">
                        {status.title()}
                    </div>
                </div>
                <div style="margin-top: 1rem;">
                    <p style="margin: 0; font-size: 1.25rem; font-weight: 500;">£{month_data['total_amount']:.2f}</p>
                    <p style="margin: 0; color: #6B7280;">{month_data['entry_count']} entries</p>
                    {f'<p style="margin: 0; color: #6B7280;">{month_data["draft_count"]} drafts</p>' if month_data.get("draft_count", 0) > 0 else ''}
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        if st.button("View Details", key=f"view_{month_num}", use_container_width=True):
            on_click(month_num)

def render_month_grid(year: int, month_data: dict, handle_month_click) -> None:
    """Render the grid of month cards"""
    st.write("")  # Add some spacing
    for row in range(4):
        cols = st.columns(3)
        for col in range(3):
            month_num = row * 3 + col + 1
            if month_num <= 12:
                with cols[col]:
                    render_month_card(
                        month_num,
                        month_data.get(month_num, {
                            'status': 'no_entries',
                            'total_amount': 0.00,
                            'entry_count': 0,
                            'draft_count': 0
                        }),
                        handle_month_click
                    )