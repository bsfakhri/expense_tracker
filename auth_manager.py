# auth_manager.py
import streamlit as st
import typing
from google.oauth2 import service_account
from googleapiclient.discovery import build
import hashlib
import time

class AuthManager:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        self.sheets_service = build('sheets', 'v4', credentials=credentials)
        self.users_sheet_id = st.secrets["USERS_SHEET_ID"]
        self.max_attempts = 3
        self.lockout_duration = 300  # 5 minutes in seconds

    def validate_teacher_id(self, teacher_id: str) -> bool:
        """Validate teacher ID format."""
        if not teacher_id:
            return False
        return len(teacher_id) >= 4 and teacher_id.isalnum()

    def validate_pin(self, pin: str) -> bool:
        """Validate PIN format."""
        if not pin:
            return False
        return len(pin) == 4 and pin.isdigit()

    def check_rate_limit(self, teacher_id: str) -> bool:
        """Check if user is rate limited."""
        current_time = time.time()
        
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
            
        if teacher_id in st.session_state.login_attempts:
            attempts = st.session_state.login_attempts[teacher_id]
            if len(attempts) >= self.max_attempts:
                oldest_attempt = attempts[0]
                if current_time - oldest_attempt < self.lockout_duration:
                    return False
                st.session_state.login_attempts[teacher_id] = []
        
        return True

    def record_login_attempt(self, teacher_id: str):
        """Record a login attempt."""
        current_time = time.time()
        if teacher_id not in st.session_state.login_attempts:
            st.session_state.login_attempts[teacher_id] = []
        st.session_state.login_attempts[teacher_id].append(current_time)

    def get_user_data(self, teacher_id: str) -> typing.Optional[dict]:
        """Retrieve user data from Google Sheets."""
        try:
            # Get all users data
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.users_sheet_id,
                range='A:E'  # Get all rows from columns A through E
            ).execute()

            if 'values' not in result:
                st.error("No data found in the users sheet")
                return None

            # Search for the user
            header = result['values'][0]  # First row contains headers
            for row in result['values'][1:]:  # Skip header row
                # Ensure row has enough columns
                row_data = row + [''] * (len(header) - len(row))
                
                if row_data[0] == teacher_id:  # First column is teacher_id
                    return {
                        'teacher_id': row_data[0],
                        'name': row_data[1],
                        'pin': row_data[2],
                        'role': row_data[3],
                        'is_active': row_data[4].upper() == 'TRUE'
                    }
            return None

        except Exception as e:
            st.error(f"Error retrieving user data: {str(e)}")
            st.error(f"Sheet ID being used: {self.users_sheet_id}")
            # Print the first part of credentials for verification (safely)
            cred_email = self.sheets_service._credentials.service_account_email
            st.error(f"Using service account: {cred_email}")
            return None

    def authenticate(self, teacher_id: str, pin: str) -> typing.Tuple[bool, str]:
        """Authenticate user with teacher ID and PIN."""
        if not self.validate_teacher_id(teacher_id):
            return False, "Invalid teacher ID format"
            
        if not self.validate_pin(pin):
            return False, "Invalid PIN format"
            
        if not self.check_rate_limit(teacher_id):
            remaining_time = self.lockout_duration - (time.time() - st.session_state.login_attempts[teacher_id][0])
            return False, f"Account temporarily locked. Try again in {int(remaining_time)} seconds"

        user_data = self.get_user_data(teacher_id)
        if not user_data:
            self.record_login_attempt(teacher_id)
            return False, "Invalid credentials"

        if not user_data['is_active']:
            return False, "Account is inactive"

        if pin != user_data['pin']:
            self.record_login_attempt(teacher_id)
            return False, "Invalid credentials"

        # Successful login
        st.session_state.authenticated = True
        st.session_state.user_data = user_data
        st.session_state.login_time = time.time()
        return True, "Login successful"