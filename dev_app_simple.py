"""
Expense Management Portal - Part 1: Core Classes and Setup
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import plotly.express as px

class DraftManager:
    """Handles all draft-related operations"""
    def __init__(self, sheets_service, drafts_sheet_id):
        self.sheets_service = sheets_service
        self.drafts_sheet_id = drafts_sheet_id
        
    def load_draft(self, month, year, teacher_id):
        """Load draft with proper error handling and validation"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.drafts_sheet_id,
                range='A:H'
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return {"expenses": [], "status": "new"}
                
            # Ensure we have header row
            if len(values) < 1:
                return {"expenses": [], "status": "new"}
                
            # Create DataFrame with explicit column names
            columns = ['teacher_id', 'month', 'year', 'expenses', 'status', 'created_date', 'last_modified', 'comments']
            df = pd.DataFrame(values[1:], columns=columns)
            
            if df.empty:
                return {"expenses": [], "status": "new"}
                
            # Convert data types and handle filtering
            df['teacher_id'] = df['teacher_id'].astype(str)
            df['year'] = df['year'].astype(str)
            
            draft = df[
                (df['month'].str.strip() == str(month).strip()) & 
                (df['year'].str.strip() == str(year).strip()) &
                (df['teacher_id'].str.strip() == str(teacher_id).strip())
            ]
            
            if draft.empty:
                return {"expenses": [], "status": "new"}
                
            try:
                expenses = json.loads(draft.iloc[0]['expenses'])
                # Validate expense structure
                for expense in expenses:
                    required_fields = ['date', 'category', 'vendor', 'description', 'amount', 'id']
                    if not all(field in expense for field in required_fields):
                        st.error(f"Invalid expense structure detected. Some required fields are missing.")
                        return {"expenses": [], "status": "new"}
                        
                return {
                    "expenses": expenses,
                    "status": draft.iloc[0]['status'],
                    "created_date": draft.iloc[0]['created_date'],
                    "last_modified": draft.iloc[0]['last_modified']
                }
            except json.JSONDecodeError:
                st.error("Error decoding draft data. Creating new draft.")
                return {"expenses": [], "status": "new"}
            except Exception as e:
                st.error(f"Error processing draft data: {str(e)}")
                return {"expenses": [], "status": "new"}
                
        except Exception as e:
            st.error(f"Error loading draft: {str(e)}")
            return {"expenses": [], "status": "new"}
        
    def save_draft(self, month, year, teacher_id, expenses, status='draft'):
        """Save draft with validation and error handling"""
        try:
            # Validate expenses before saving
            for expense in expenses:
                if not self._validate_expense(expense):
                    st.error("Invalid expense data detected. Draft not saved.")
                    return False
                    
            draft_data = {
                'teacher_id': str(teacher_id),
                'month': month,
                'year': str(year),
                'expenses': json.dumps(expenses),
                'status': status,
                'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            existing_row = self._find_draft_row(month, year, teacher_id)
            
            if existing_row:
                # Update existing draft
                for col, value in enumerate(draft_data.values(), start=1):
                    range_name = f'{chr(64 + col)}{existing_row}'
                    if not self._update_cell(range_name, value):
                        return False
            else:
                # Create new draft
                if not self._append_draft([list(draft_data.values())]):
                    return False
            
            return True
            
        except Exception as e:
            st.error(f"Error saving draft: {str(e)}")
            return False

    def _validate_expense(self, expense):
        """Validate expense data structure"""
        required_fields = ['date', 'category', 'vendor', 'description', 'amount', 'id']
        
        # Check all required fields exist
        if not all(field in expense for field in required_fields):
            return False
            
        # Validate data types
        try:
            datetime.strptime(expense['date'], '%Y-%m-%d')
            float(expense['amount'])
            int(expense['id'])
            str(expense['category'])
            str(expense['vendor'])
            str(expense['description'])
        except (ValueError, TypeError):
            return False
            
        return True

    def _find_draft_row(self, month, year, teacher_id):
        """Find existing draft row with error handling"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.drafts_sheet_id,
                range='A:H'
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return None
                
            for i, row in enumerate(values):
                if (len(row) >= 3 and 
                    row[0] == str(teacher_id) and 
                    row[1] == month and 
                    row[2] == str(year)):
                    return i + 1
            return None
            
        except Exception as e:
            st.error(f"Error finding draft row: {str(e)}")
            return None

    def _update_cell(self, range_name, value):
        """Update single cell with error handling"""
        try:
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.drafts_sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': [[value]]}
            ).execute()
            return True
        except Exception as e:
            st.error(f"Error updating cell: {str(e)}")
            return False

    def _append_draft(self, values):
        """Append new draft with error handling"""
        try:
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.drafts_sheet_id,
                range='A:H',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': values}
            ).execute()
            return True
        except Exception as e:
            st.error(f"Error appending draft: {str(e)}")
            return False

class ExpenseApp:
    """Main application class"""
    def __init__(self):
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
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'submit_expense'
        if 'current_draft' not in st.session_state:
            st.session_state.current_draft = None
            
        self._set_custom_css()
        self.sheets_service = self._initialize_google_sheets()
        self.users_sheet_id = st.secrets["USERS_SHEET_ID"]
        self.expenses_sheet_id = st.secrets["EXPENSES_SHEET_ID"]
        self.drafts_sheet_id = st.secrets["DRAFTS_SHEET_ID"]
        
        # Initialize draft manager
        self.draft_manager = DraftManager(self.sheets_service, self.drafts_sheet_id)

    
    def _set_custom_css(self):
        """Set custom CSS for better UI"""
        st.markdown("""
            <style>
            .main-content { max-width: 1200px; margin: 0 auto; padding: 1rem; }
            .expense-form {
                background-color: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                margin-bottom: 2rem;
            }
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
            .status-badge {
                display: inline-block;
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.875rem;
                font-weight: 500;
            }
            .status-draft { background-color: #e2e8f0; color: #1a202c; }
            .status-pending { background-color: #fef3c7; color: #92400e; }
            .status-submitted { background-color: #d1fae5; color: #065f46; }
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
        
        return _get_sheets_service(1)

    @staticmethod
    def get_expense_categories():
        """Get list of expense categories"""
        return [
            "Select Category",
            "Tayeen Khidmatguzar",
            "Wafdul Huffaz",
            "Full-time KG (non tayeen)",
            "Part-time KG (non tayeen)",
            "Admin/Operational Staff",
            "Internet",
            "Telephone",
            "Electricity",
            "Gas",
            "Water",
            "Others - Specify utility",
            "Stationary",
            "IT requirements",
            "Legal",
            "Taxes and Licenses",
            "Accreditation",
            "Travel and conveyence (Office only)",
            "Security",
            "First aid",
            "Advertising / marketing",
            "Dues and subscription",
            "Web hosting and domain",
            "Printing and publications",
            "Maintenance expenses",
            "Cleaning & Washing",
            "Relocation (KG Badli)",
            "Rent / Jamat facilities",
            "Housing Allowance",
            "Inayat/Benefits",
            "Food Pantry",
            "Mawaid",
            "Refreshments",
            "Awards and gifts",
            "Rehlat ilmi / Tafreeh",
            "Ikhtebar",
            "Workshops / Seminars",
            "Sports activites",
            "Hostel Maintenance & House Keeping",
            "Laundry services",
            "Camps",
            "Equipment",
            "Renovation",
            "Others - Specify Expense"
        ]

    @staticmethod
    def get_vendors():
        """Get list of common vendors"""
        return [
            "Select Vendor",
            "Amazon",
            "Office Depot",
            "Staples",
            "Local Restaurant",
            "Uber/Lyft",
            "Airlines",
            "Hotels",
            "Other"
        ]
    
    """
    Expense Management Portal - Part 2: Form Handling and User Interface
    """

    def show_login(self):
        """Display login page"""
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

    def show_expense_form(self):
        """Display expense submission form with draft support"""
        st.markdown("### Submit New Expense")
        
        # Load or initialize draft data
        if 'current_month' not in st.session_state:
            st.session_state.current_month = datetime.now().strftime('%B')
            
        if 'current_draft' not in st.session_state:
            try:
                draft_data = self.draft_manager.load_draft(
                    st.session_state.current_month,
                    datetime.now().year,
                    st.session_state.user_data['teacher_id']
                )
                st.session_state.current_draft = draft_data if draft_data else {"expenses": [], "status": "new"}
            except Exception as e:
                st.error(f"Error loading draft: {str(e)}")
                st.session_state.current_draft = {"expenses": [], "status": "new"}
                
        # For debugging
        st.write("Debug - Current Draft:", st.session_state.current_draft)
        
        # Display current draft status
        status_colors = {
            'new': 'blue',
            'draft': 'orange',
            'submitted': 'green'
        }
        status = st.session_state.current_draft.get('status', 'new')
        st.markdown(
            f'<div class="status-badge" style="background-color: {status_colors[status]}20; '
            f'color: {status_colors[status]}; margin-bottom: 20px;">'
            f'Status: {status.title()}</div>',
            unsafe_allow_html=True
        )

        with st.form("expense_form", clear_on_submit=True):
            # Date selection
            date = st.date_input(
                "Date of Expense",
                value=datetime.now().date(),
                min_value=datetime(datetime.now().year, 1, 1).date(),
                max_value=datetime.now().date()
            )

            # Category selection
            category = st.selectbox(
                "Category",
                options=self.get_expense_categories()
            )

            # Vendor selection with custom input
            vendor = st.selectbox(
                "Vendor",
                options=self.get_vendors()
            )

            if vendor == "Other":
                custom_vendor = st.text_input("Specify Vendor")
                vendor = custom_vendor if custom_vendor else vendor

            # Amount input
            amount = st.number_input(
                "Amount",
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )

            # Description input
            description = st.text_area(
                "Description",
                placeholder="Enter expense details..."
            )

            submitted = st.form_submit_button("Add Expense")
            
        if submitted:
            if not self._validate_expense_input(category, vendor, amount, description):
                return

            # Generate new expense ID
            current_expenses = st.session_state.current_draft.get('expenses', [])
            next_id = len(current_expenses) + 1

            # Create new expense
            new_expense = {
                'id': next_id,
                'date': date.strftime('%Y-%m-%d'),
                'category': category,
                'vendor': vendor,
                'description': description,
                'amount': float(amount)
            }

            # Add to current draft
            current_expenses.append(new_expense)
            st.session_state.current_draft['expenses'] = current_expenses

            # Save draft automatically
            if self.draft_manager.save_draft(
                st.session_state.current_month,
                datetime.now().year,
                st.session_state.user_data['teacher_id'],
                current_expenses
            ):
                st.success("Expense added successfully!")
                st.rerun()
            else:
                st.error("Failed to save expense. Please try again.")

        # Show existing expenses
        self._show_expense_list()

        # Draft action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Draft", use_container_width=True):
                if self.draft_manager.save_draft(
                    st.session_state.current_month,
                    datetime.now().year,
                    st.session_state.user_data['teacher_id'],
                    st.session_state.current_draft.get('expenses', [])
                ):
                    st.success("Draft saved successfully!")
                    
        with col2:
            if st.button("Submit for Approval", use_container_width=True, type="primary"):
                if self._submit_expenses_for_approval():
                    st.success("Expenses submitted for approval!")
                    st.rerun()

    def _show_expense_list(self):
        """Display list of expenses in current draft"""
        expenses = st.session_state.current_draft.get('expenses', [])
        if not expenses:
            st.info("No expenses added yet.")
            return

        st.markdown("### Current Expenses")
        
        total_amount = 0
        for expense in sorted(expenses, key=lambda x: x['date']):
            with st.expander(f"{expense['date']} - {expense['category']} (${expense['amount']:.2f})"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write("**Category:**", expense['category'])
                    st.write("**Vendor:**", expense['vendor'])
                    st.write("**Description:**", expense['description'])
                    
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{expense['id']}"):
                        if self._delete_expense(expense['id']):
                            st.success("Expense deleted!")
                            st.rerun()
                            
                total_amount += expense['amount']

        st.markdown(f"### Total Amount: ${total_amount:.2f}")

    def _validate_expense_input(self, category, vendor, amount, description):
        """Validate expense input fields"""
        if category == "Select Category":
            st.error("Please select a category")
            return False
        if vendor == "Select Vendor":
            st.error("Please select or specify a vendor")
            return False
        if amount <= 0:
            st.error("Please enter a valid amount")
            return False
        if not description:
            st.error("Please provide a description")
            return False
        return True

    def _delete_expense(self, expense_id):
        """Delete an expense from current draft"""
        try:
            expenses = st.session_state.current_draft.get('expenses', [])
            updated_expenses = [e for e in expenses if e['id'] != expense_id]
            st.session_state.current_draft['expenses'] = updated_expenses
            
            return self.draft_manager.save_draft(
                st.session_state.current_month,
                datetime.now().year,
                st.session_state.user_data['teacher_id'],
                updated_expenses
            )
        except Exception as e:
            st.error(f"Error deleting expense: {str(e)}")
            return False

    def _submit_expenses_for_approval(self):
        """Submit current draft for approval"""
        try:
            expenses = st.session_state.current_draft.get('expenses', [])
            if not expenses:
                st.error("No expenses to submit")
                return False

            # Move expenses to main expense sheet
            for expense in expenses:
                expense_data = [
                    str(expense['id']),                                    # ID
                    str(st.session_state.user_data['teacher_id']),        # Teacher ID
                    expense['date'],                                       # Date
                    expense['category'],                                   # Category
                    expense['vendor'],                                     # Vendor
                    str(expense['amount']),                               # Amount
                    expense['description'],                               # Description
                    'pending',                                            # Status
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),        # Submitted date
                    '',                                                   # Approved by
                    '',                                                   # Approved date
                    ''                                                    # Comments
                ]
                
                if not self.append_to_sheet(self.expenses_sheet_id, 'A:L', [expense_data]):
                    st.error("Failed to submit expenses")
                    return False

            # Save draft with submitted status
            if not self.draft_manager.save_draft(
                st.session_state.current_month,
                datetime.now().year,
                st.session_state.user_data['teacher_id'],
                expenses,
                status='submitted'
            ):
                return False

            # Clear current draft
            st.session_state.current_draft = {
                "expenses": [],
                "status": "new"
            }
            
            return True
        except Exception as e:
            st.error(f"Error submitting expenses: {str(e)}")
            return False
    def show_dashboard(self):
        """Display main dashboard after login"""
        self.show_logged_in_header()

        # Sidebar navigation
        with st.sidebar:
            st.title("Navigation")
            
            if st.button("📝 Submit Expense", use_container_width=True):
                st.session_state.current_page = 'submit_expense'
                
            if st.button("📊 History & Analytics", use_container_width=True):
                st.session_state.current_page = 'history'
                
            if st.session_state.user_data['role'] == 'admin':
                if st.button("👥 Admin Dashboard", use_container_width=True):
                    st.session_state.current_page = 'admin'
                    
            if st.button("👋 Logout", use_container_width=True):
                self.logout()

        # Show appropriate page based on navigation
        if st.session_state.current_page == 'submit_expense':
            self.show_expense_form()
        elif st.session_state.current_page == 'history':
            self.show_expense_history()
        elif st.session_state.current_page == 'admin' and st.session_state.user_data['role'] == 'admin':
            self.show_admin_dashboard()
        else:
            self.show_expense_form()

    def show_logged_in_header(self):
        """Display header for logged-in users"""
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
        """Handle user logout"""
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.session_state.current_draft = None
        st.rerun()

    """
    Expense Management Portal - Part 3: Data Management and Processing
    """


    def validate_credentials(self, its_id, pin):
        """Validate user credentials with improved error handling"""
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

    @st.cache_data(ttl=30)
    def read_sheet_to_df(_self, sheet_id, range_name):
        """Read Google Sheet data with caching and error handling"""
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

    def append_to_sheet(self, sheet_id, range_name, values):
        """Append values to Google Sheet with error handling"""
        try:
            body = {'values': values}
            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            # Clear cache after successful append
            self.read_sheet_to_df.clear()
            return True
        except Exception as e:
            st.error(f"Error appending to Google Sheet: {str(e)}")
            return False

    def show_expense_history(self):
        """Display expense history with filtering and sorting"""
        st.markdown("### Expense History")
        
        expenses_df = self.read_sheet_to_df(self.expenses_sheet_id, 'A:L')
        if expenses_df.empty:
            st.info("No expenses found")
            return
            
        # Convert date columns
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        expenses_df['submitted_date'] = pd.to_datetime(expenses_df['submitted_date'])
        
        # Filtering options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_range = st.date_input(
                "Date Range",
                value=(
                    datetime.now().date() - timedelta(days=30),
                    datetime.now().date()
                ),
                key="date_range"
            )
        
        with col2:
            status_filter = st.multiselect(
                "Status",
                options=sorted(expenses_df['status'].unique()),
                default=sorted(expenses_df['status'].unique()),
                key="status_filter"
            )
        
        with col3:
            category_filter = st.multiselect(
                "Category",
                options=sorted(expenses_df['category'].unique()),
                default=sorted(expenses_df['category'].unique()),
                key="category_filter"
            )

        # Apply filters
        if len(date_range) == 2:
            start_date, end_date = date_range
            mask = (
                (expenses_df['date'].dt.date >= start_date) &
                (expenses_df['date'].dt.date <= end_date) &
                (expenses_df['status'].isin(status_filter)) &
                (expenses_df['category'].isin(category_filter))
            )
            
            if not st.session_state.user_data['role'] == 'admin':
                mask = mask & (expenses_df['teacher_id'] == st.session_state.user_data['teacher_id'])
                
            filtered_df = expenses_df[mask].copy()
            
            if not filtered_df.empty:
                # Add status badges
                filtered_df['status_badge'] = filtered_df['status'].apply(
                    lambda x: {
                        'pending': '🟡 Pending',
                        'approved': '🟢 Approved',
                        'rejected': '🔴 Rejected'
                    }.get(x, x)
                )
                
                # Format amount for display and calculations
                filtered_df['amount_clean'] = filtered_df['amount'].astype(float)
                filtered_df['amount_display'] = filtered_df['amount_clean'].apply(
                    lambda x: f"${x:,.2f}"
                )
                
                # Calculate metrics
                total_amount = filtered_df['amount_clean'].sum()
                pending_count = len(filtered_df[filtered_df['status'] == 'pending'])
                
                # Show metrics
                metrics_col1, metrics_col2 = st.columns(2)
                with metrics_col1:
                    st.metric("Total Amount", f"${total_amount:,.2f}")
                with metrics_col2:
                    st.metric("Pending Expenses", pending_count)
                
                # Show expense table with different views for admin and regular users
                if st.session_state.user_data['role'] == 'admin':
                    self.show_admin_expense_table(filtered_df)
                else:
                    self.show_user_expense_table(filtered_df)
                
                # Show visualizations
                self.show_expense_analytics(filtered_df)
            else:
                st.info("No expenses found for the selected filters")

    def show_admin_expense_table(self, df):
        """Display expense table with approval controls for admins"""
        st.markdown("### Pending Approvals")
        
        pending_df = df[df['status'] == 'pending'].copy()
        if not pending_df.empty:
            for _, row in pending_df.iterrows():
                with st.expander(f"📋 {row['date'].strftime('%Y-%m-%d')} - {row['category']} ({row['amount_display']})"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write("**Description:**", row['description'])
                        st.write("**Vendor:**", row['vendor'])
                        st.write("**Submitted by:**", row['teacher_id'])
                        st.write("**Submitted on:**", row['submitted_date'])
                    
                    with col2:
                        comments = st.text_area(
                            "Comments",
                            key=f"comments_{row['id']}",
                            placeholder="Enter approval/rejection comments..."
                        )
                        
                        approve_col, reject_col = st.columns(2)
                        with approve_col:
                            if st.button("✅ Approve", key=f"approve_{row['id']}"):
                                if self.update_expense_status(
                                    row['id'],
                                    'approved',
                                    comments,
                                    st.session_state.user_data['teacher_id']
                                ):
                                    st.success("Expense approved!")
                                    st.rerun()
                                    
                        with reject_col:
                            if st.button("❌ Reject", key=f"reject_{row['id']}"):
                                if self.update_expense_status(
                                    row['id'],
                                    'rejected',
                                    comments,
                                    st.session_state.user_data['teacher_id']
                                ):
                                    st.success("Expense rejected!")
                                    st.rerun()

    def show_user_expense_table(self, df):
        """Display expense table for regular users"""
        st.markdown("### Your Expenses")
        
        # Sort by date descending
        df_sorted = df.sort_values('date', ascending=False)
        
        for _, row in df_sorted.iterrows():
            with st.expander(
                f"{row['status_badge']} - {row['date'].strftime('%Y-%m-%d')} - {row['category']} ({row['amount_display']})"
            ):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write("**Description:**", row['description'])
                    st.write("**Vendor:**", row['vendor'])
                    st.write("**Submitted on:**", row['submitted_date'])
                
                with col2:
                    if row['approved_by']:
                        st.write("**Approved/Rejected by:**", row['approved_by'])
                        st.write("**On:**", row['approved_date'])
                    if row['comments']:
                        st.write("**Comments:**", row['comments'])

    def show_expense_analytics(self, df):
        """Display expense analytics visualizations"""
        st.markdown("### Expense Analytics")
        
        tab1, tab2 = st.tabs(["Category Analysis", "Time Trends"])
        
        with tab1:
            # Category breakdown
            fig_category = px.pie(
                df,
                values='amount_clean',
                names='category',
                title='Expenses by Category'
            )
            st.plotly_chart(fig_category, use_container_width=True)
            
            # Category summary table
            category_summary = df.groupby('category').agg({
                'amount_clean': ['count', 'sum']
            }).round(2)
            category_summary.columns = ['Count', 'Total Amount']
            category_summary = category_summary.reset_index()
            st.dataframe(category_summary, use_container_width=True)
        
        with tab2:
            # Time series trend
            daily_expenses = df.groupby('date')['amount_clean'].sum().reset_index()
            fig_trend = px.line(
                daily_expenses,
                x='date',
                y='amount_clean',
                title='Daily Expense Trend'
            )
            st.plotly_chart(fig_trend, use_container_width=True)

    def update_expense_status(self, expense_id, status, comments='', approver=''):
        """Update expense status with improved error handling"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.expenses_sheet_id,
                range='A:L'
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return False
            
            # Find row for expense
            for i, row in enumerate(values):
                if row[0] == str(expense_id):
                    row_num = i + 1
                    break
            else:
                st.error("Expense not found")
                return False
            
            # Update status
            self.update_sheet_cell(
                self.expenses_sheet_id,
                f'H{row_num}',
                status
            )
            
            # Update approver
            if approver:
                self.update_sheet_cell(
                    self.expenses_sheet_id,
                    f'J{row_num}',
                    approver
                )
                
            # Update approval date
            self.update_sheet_cell(
                self.expenses_sheet_id,
                f'K{row_num}',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # Update comments
            if comments:
                self.update_sheet_cell(
                    self.expenses_sheet_id,
                    f'L{row_num}',
                    comments
                )
            
            return True
        except Exception as e:
            st.error(f"Error updating expense status: {str(e)}")
            return False

    def run(self):
        """Main application entry point with error handling"""
        try:
            if not st.session_state.authenticated:
                self.show_login()
            else:
                self.show_dashboard()
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please try refreshing the page or contact support if the issue persists.")

if __name__ == "__main__":
    app = ExpenseApp()
    app.run()