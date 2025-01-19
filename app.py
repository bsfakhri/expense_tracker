"""
Expense Management Portal - Part 1: Authentication and User Management
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

class ExpenseApp:
    def __init__(self):
        # Initialize Streamlit page configuration
        st.set_page_config(
            page_title="Expense Management Portal",
            layout="centered",
            initial_sidebar_state="collapsed"
        )
        
        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_data' not in st.session_state:
            st.session_state.user_data = None
            
        # Set up the application
        self._set_custom_css()
        self.sheets_service = self._initialize_google_sheets()
        self.users_sheet_id = st.secrets["USERS_SHEET_ID"]
        self.expenses_sheet_id = st.secrets["EXPENSES_SHEET_ID"]

    @staticmethod
    def _set_custom_css():
        """Set custom CSS for better UI"""
        st.markdown("""
            <style>
            .big-font {
                font-size: 24px !important;
                font-weight: bold;
            }
            .stButton>button {
                width: 100%;
                height: 50px;
                font-size: 18px;
                margin: 5px 0;
                border-radius: 10px;
            }
            .login-container {
                max-width: 400px;
                margin: 0 auto;
                padding: 20px;
                border-radius: 10px;
                background-color: #f8f9fa;
            }
            .header-container {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 0;
                margin-bottom: 20px;
            }
            </style>
        """, unsafe_allow_html=True)

    def _initialize_google_sheets(self):
        """Initialize Google Sheets connection with caching"""
        @st.cache_resource
        def _get_sheets_service(_):
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"],
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                return build('sheets', 'v4', credentials=credentials)
            except Exception as e:
                st.error(f"Error initializing Google Sheets: {str(e)}")
                raise
        
        return _get_sheets_service(1)  # Pass a dummy argument for caching

    @st.cache_data(ttl=30)
    def read_sheet_to_df(_self, sheet_id, range_name):
        """Read Google Sheet data with caching"""
        try:
            result = _self.sheets_service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return pd.DataFrame()
                
            df = pd.DataFrame(values[1:], columns=values[0])
            df = df.replace(['', 'None', 'NaN', 'nan'], '')
            return df
            
        except Exception as e:
            st.error(f"Error reading Google Sheet: {str(e)}")
            return pd.DataFrame()

    def validate_credentials(self, its_id, pin):
        """Validate user credentials against the users sheet"""
        try:
            users_df = self.read_sheet_to_df(self.users_sheet_id, 'A:D')
            if users_df.empty:
                return False
            
            users_df['teacher_id'] = users_df['teacher_id'].astype(str).str.strip()
            users_df['pin'] = users_df['pin'].astype(str).str.strip()
            
            user = users_df[
                (users_df['teacher_id'] == str(its_id).strip()) & 
                (users_df['pin'] == str(pin).strip())
            ]
            
            if not user.empty:
                st.session_state.user_data = user.iloc[0].to_dict()
                return True
            return False
            
        except Exception as e:
            st.error(f"Error validating credentials: {str(e)}")
            return False

    def show_login(self):
        """Display login page with user authentication form"""
        st.markdown("""
            <div class="header-container">
                <span class="big-font">📊 Expense Management Portal</span>
            </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown("### Login")
            its_id = st.text_input(
                "ITS ID",
                placeholder="Enter your ITS ID",
                key="login_its_id"
            ).strip()
            
            pin = st.text_input(
                "PIN",
                type="password",
                placeholder="Enter your 4-digit PIN",
                max_chars=4,
                key="login_pin"
            ).strip()

            if st.button("Login", key="login_button"):
                if not its_id or not pin:
                    st.error("Please enter both ITS ID and PIN")
                elif len(pin) != 4:
                    st.error("PIN must be 4 digits")
                elif not pin.isdigit():
                    st.error("PIN must contain only digits")
                else:
                    if self.validate_credentials(its_id, pin):
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
            
            st.markdown('</div>', unsafe_allow_html=True)

    def show_logged_in_header(self):
        """Display header for logged-in users showing name and role"""
        st.markdown(f"""
            <div class="header-container">
                <span class="big-font">📊 Expense Management Portal</span>
                <div>
                    <span>Welcome, {st.session_state.user_data['name']}</span>
                    <span style="margin-left: 10px;">({st.session_state.user_data['role']})</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    def logout(self):
        """Handle user logout by clearing session state"""
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.rerun()

    def run(self):
        """Main application entry point and routing"""
        if not st.session_state.authenticated:
            self.show_login()
        else:
            self.show_logged_in_header()
            if st.sidebar.button("Logout"):
                self.logout()
            st.info("Login successful! Parts 2 and 3 will add expense management features.")

if __name__ == "__main__":
    app = ExpenseApp()
    app.run()