"""
Expense Management Portal - Complete Application (Part 1: Core Setup)
"""

import streamlit as st
import pandas as pd
import json
import uuid
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import plotly.express as px

class ExpenseApp:
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
        if 'expense_draft' not in st.session_state:
            st.session_state.expense_draft = []
            
        self._set_custom_css()
        self.sheets_service = self._initialize_google_sheets()
        self.users_sheet_id = st.secrets["USERS_SHEET_ID"]
        self.expenses_sheet_id = st.secrets["EXPENSES_SHEET_ID"]
        self.drafts_sheet_id = st.secrets["DRAFTS_SHEET_ID"]

    
    def _set_custom_css(self):
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
            .expense-form {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .expense-list {
                margin-top: 20px;
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .status-badge {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 14px;
            }
            .status-draft {
                background-color: #e2e8f0;
                color: #1a202c;
            }
            .status-pending {
                background-color: #fef3c7;
                color: #92400e;
            }
            .status-approved {
                background-color: #d1fae5;
                color: #065f46;
            }
            .status-rejected {
                background-color: #fee2e2;
                color: #991b1b;
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
        
        return _get_sheets_service(1)

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
        """Validate user credentials"""
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

    def logout(self):
        """Handle user logout"""
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.session_state.expense_draft = []
        st.rerun()

    """
    Expense Management Portal - Part 2: Data Handling Methods
    This part contains all the data manipulation and business logic methods.
    """

    def get_expense_categories(self):
        """Get hierarchical expense categories"""
        return {
            "Operating Income": {
                "Programs of Qism al Tahfeez": [
                    "QAT Mukhayyam",
                    "QAT Online (Full-time)",
                    "QAT Rawdat al Atfaal",
                    "QAT Tahfeez al Kibaar",
                    "QAT Tahfeez al Kibaar (Tayseer)",
                    "QAT Mukhayyam (Hifz Only)",
                    "QAT Online (Part-time)"
                ],
                "Camp Activities": ["Camps"],
                "Others": [
                    "Others - Specify Income Name",
                    "Arrears (Receivable of previous year)"
                ]
            },
            "Expenses": {
                "Wazifas / Salaries and benefits": [
                    "Tayeen Khidmatguzar",
                    "Wafdul Huffaz",
                    "Full-time KG (non tayeen)",
                    "Part-time KG (non tayeen)",
                    "Admin/Operational Staff"
                ],
                "Utilities": [
                    "Internet",
                    "Telephone",
                    "Electricity",
                    "Gas",
                    "Water",
                    "Others - Specify utility"
                ],
                "Administrative expenses": [
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
                    "Cleaning & Washing"
                ]
            }
        }

    def get_vendors(self):
        """Get list of vendors"""
        return [
            "Select Vendor",
            "Tesco",
            "Lidl",
            "Adil Halal Meet",
            "Costco",
            "Local Restaurant",
            "Uber/Lyft",
            "Airlines",
            "Hotels",
            "Other"
        ]

    def append_to_sheet(self, sheet_id, range_name, values):
        """Append values to Google Sheet"""
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

    def update_sheet_cell(self, sheet_id, range_name, value):
        """Update a single cell in Google Sheet"""
        try:
            body = {
                'values': [[value]]
            }
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            # Clear cache after successful update
            self.read_sheet_to_df.clear()
            return True
        except Exception as e:
            st.error(f"Error updating cell: {str(e)}")
            return False

    def save_draft_expenses(self, month, year, expenses_list):
        """Save expenses as draft"""
        try:
            # First, check if a draft already exists for this month/year
            existing_drafts = self.get_draft_expenses(month, year)
            draft_data = {
                'draft_id': existing_drafts[0]['draft_id'] if existing_drafts else str(uuid.uuid4()),
                'teacher_id': st.session_state.user_data['teacher_id'],
                'month': month,
                'year': str(year),
                'expenses': json.dumps(expenses_list),
                'status': 'draft',
                'created_date': existing_drafts[0]['created_date'] if existing_drafts else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_modified_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if existing_drafts:
                # Update existing draft
                draft_row = self.find_draft_row(month, year)
                if draft_row:
                    for col, value in enumerate(draft_data.values(), start=1):
                        range_name = f'{chr(64 + col)}{draft_row}'
                        self.update_sheet_cell(self.drafts_sheet_id, range_name, value)
                    return True
            else:
                # Create new draft
                values = [[v for v in draft_data.values()]]
                return self.append_to_sheet(self.drafts_sheet_id, 'A:H', values)
            
            return False
        except Exception as e:
            st.error(f"Error saving draft: {str(e)}")
            return False

    def get_draft_expenses(self, month=None, year=None):
        """Get draft expenses for the current user"""
        try:
            drafts_df = self.read_sheet_to_df(self.drafts_sheet_id, 'A:H')
            if drafts_df.empty:
                return []
                
            # Filter by user
            drafts_df = drafts_df[
                drafts_df['teacher_id'] == str(st.session_state.user_data['teacher_id'])
            ]
            
            # Filter by month/year if provided
            if month and year:
                drafts_df = drafts_df[
                    (drafts_df['month'] == month) & 
                    (drafts_df['year'] == str(year))
                ]
            
            # Parse JSON expenses
            drafts_df['expenses'] = drafts_df['expenses'].apply(
                lambda x: json.loads(x) if x else []
            )
            
            return drafts_df.to_dict('records')
        except Exception as e:
            st.error(f"Error getting drafts: {str(e)}")
            return []

    def find_draft_row(self, month, year):
        """Find the row number for a specific draft"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.drafts_sheet_id,
                range='A:H'
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return None
                
            for i, row in enumerate(values[1:], start=2):  # Start from 2 to account for header
                if (row[2] == month and  # month column
                    row[3] == str(year) and  # year column
                    row[1] == str(st.session_state.user_data['teacher_id'])):  # teacher_id column
                    return i
                    
            return None
        except Exception as e:
            st.error(f"Error finding draft row: {str(e)}")
            return None

    def submit_monthly_expenses(self, month, year, expenses_list):
        """Submit all expenses for final approval"""
        try:
            success = True
            for expense in expenses_list:
                # Get the next ID
                next_id = len(self.read_sheet_to_df(self.expenses_sheet_id, 'A:L')) + 1
                
                expense_data = [
                    str(next_id),  # ID
                    str(st.session_state.user_data['teacher_id']),  # Teacher ID
                    expense['date'],  # Date
                    expense['category'],  # Category
                    expense.get('vendor', 'Not specified'),  # Vendor
                    str(float(expense['amount'])),  # Amount
                    expense.get('description', ''),  # Description
                    'pending',  # Status
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Submitted date
                    ' ',  # Approved by
                    ' ',  # Approved date
                    ' '   # Comments
                ]
                
                if not self.append_to_sheet(self.expenses_sheet_id, 'A:L', [expense_data]):
                    success = False
                    break
            
            if success:
                # Update draft status to submitted
                draft_row = self.find_draft_row(month, year)
                if draft_row:
                    self.update_sheet_cell(self.drafts_sheet_id, f'F{draft_row}', 'submitted')
                
            return success
        except Exception as e:
            st.error(f"Error submitting expenses: {str(e)}")
            return False

    def update_expense_status(self, row_number, status, comments='', approver=''):
        """Update expense status in Google Sheet"""
        try:
            # Update status
            self.update_sheet_cell(
                self.expenses_sheet_id,
                f'H{row_number}',
                status
            )
            
            # Update approver
            if approver:
                self.update_sheet_cell(
                    self.expenses_sheet_id,
                    f'J{row_number}',
                    approver
                )
                
            # Update approval date
            self.update_sheet_cell(
                self.expenses_sheet_id,
                f'K{row_number}',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # Update comments
            if comments:
                self.update_sheet_cell(
                    self.expenses_sheet_id,
                    f'L{row_number}',
                    comments
                )
            
            return True
        except Exception as e:
            st.error(f"Error updating expense status: {str(e)}")
            return False

    def get_expense_analytics(self, df):
        """Calculate expense analytics"""
        try:
            # Convert amount to float
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            analytics = {
                'total_amount': df['amount'].sum(),
                'average_amount': df['amount'].mean(),
                'total_count': len(df),
                'by_category': df.groupby('category')['amount'].agg(['sum', 'count']).to_dict('index'),
                'by_status': df['status'].value_counts().to_dict(),
                'monthly_trend': df.groupby(pd.to_datetime(df['date']).dt.strftime('%Y-%m'))['amount'].sum().to_dict()
            }
            
            return analytics
        except Exception as e:
            st.error(f"Error calculating analytics: {str(e)}")
            return None

    """
    Expense Management Portal - Part 3A: Core UI Components
    This part contains the core UI components and header display methods.
    """

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

    def show_monthly_expense_form(self):
        """Display the monthly expense form with draft support"""
        st.markdown("### Monthly Expense Entry")
        
        # Month and year selection
        col1, col2 = st.columns(2)
        with col1:
            month = st.selectbox(
                "Month",
                options=['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December']
            )
        with col2:
            year = st.selectbox(
                "Year",
                options=range(datetime.now().year - 1, datetime.now().year + 1)
            )
        
        # Load existing draft if any
        drafts = self.get_draft_expenses(month, year)
        current_draft = drafts[0] if drafts else None
        
        if current_draft:
            expenses_list = current_draft['expenses']
            status = current_draft['status']
            st.info(f"Loaded {status} from {current_draft['last_modified_date']}")
        else:
            expenses_list = []
            status = 'draft'
        
        # Display expense form in a card
        with st.container():
            st.markdown('<div class="expense-form">', unsafe_allow_html=True)
            
            # Category selection
            categories = self.get_expense_categories()
            main_category = st.selectbox(
                "Main Category",
                options=list(categories.keys())
            )
            
            if main_category:
                sub_categories = categories[main_category]
                sub_category = st.selectbox(
                    "Sub Category",
                    options=list(sub_categories.keys())
                )
                
                if sub_category:
                    items = sub_categories[sub_category]
                    item = st.selectbox(
                        "Item",
                        options=items
                    )
            
            # Expense details
            col1, col2 = st.columns(2)
            with col1:
                amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f"
                )
                
                vendor = st.selectbox(
                    "Vendor",
                    options=self.get_vendors()
                )
                
            with col2:
                date = st.date_input(
                    "Date",
                    value=datetime.now().date()
                )
                
                if vendor == "Other":
                    custom_vendor = st.text_input("Specify Vendor")
                    vendor = custom_vendor if custom_vendor else vendor
            
            description = st.text_area(
                "Description",
                placeholder="Enter expense details..."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Add to Draft", use_container_width=True):
                    if not all([main_category, sub_category, item, amount > 0, vendor != "Select Vendor"]):
                        st.error("Please fill in all required fields")
                    else:
                        new_expense = {
                            'date': date.strftime('%Y-%m-%d'),
                            'main_category': main_category,
                            'sub_category': sub_category,
                            'item': item,
                            'vendor': vendor,
                            'amount': amount,
                            'description': description
                        }
                        expenses_list.append(new_expense)
                        
                        if self.save_draft_expenses(month, year, expenses_list):
                            st.success("Expense added to draft")
                            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Display expense list if there are any expenses
        if expenses_list:
            self.show_expense_list(expenses_list, month, year)

    """
    Expense Management Portal - Part 3B: Expense History and Analytics
    This part contains the expense history display and analytics components.
    """

    def show_expense_list(self, expenses_list, month, year):
        """Display list of expenses with actions"""
        st.markdown('<div class="expense-list">', unsafe_allow_html=True)
        st.markdown("### Expense List")
        
        # Calculate total
        total_amount = sum(float(expense['amount']) for expense in expenses_list)
        st.markdown(f"**Total Amount: ${total_amount:,.2f}**")
        
        # Display expenses in a table
        expenses_df = pd.DataFrame(expenses_list)
        if not expenses_df.empty:
            expenses_df['amount'] = expenses_df['amount'].apply(lambda x: f"${float(x):,.2f}")
            st.dataframe(
                expenses_df[[
                    'date', 'main_category', 'sub_category', 'item',
                    'vendor', 'amount', 'description'
                ]],
                use_container_width=True
            )
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save as Draft", use_container_width=True):
                if self.save_draft_expenses(month, year, expenses_list):
                    st.success("Draft saved successfully!")
        
        with col2:
            if st.button("Submit for Approval", use_container_width=True):
                if self.submit_monthly_expenses(month, year, expenses_list):
                    st.success("Expenses submitted for approval!")
                    st.session_state.expense_draft = []
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    def show_expense_history(self):
        """Display expense history with filtering and analytics"""
        st.markdown("### Expense History")
        
        # Get all expenses
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
                )
            )
        
        with col2:
            status_filter = st.multiselect(
                "Status",
                options=sorted(expenses_df['status'].unique()),
                default=sorted(expenses_df['status'].unique())
            )
        
        with col3:
            category_filter = st.multiselect(
                "Category",
                options=sorted(expenses_df['category'].unique()),
                default=sorted(expenses_df['category'].unique())
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
            
            if st.session_state.user_data['role'] != 'admin':
                mask &= (expenses_df['teacher_id'] == st.session_state.user_data['teacher_id'])
            
            filtered_df = expenses_df[mask].copy()
            
            if not filtered_df.empty:
                # Show analytics
                analytics = self.get_expense_analytics(filtered_df)
                if analytics:
                    self.show_expense_analytics(analytics)
                
                # Show expense list based on role
                if st.session_state.user_data['role'] == 'admin':
                    self.show_admin_expense_table(filtered_df)
                else:
                    self.show_user_expense_table(filtered_df)
            else:
                st.info("No expenses found for the selected filters")

    def show_expense_analytics(self, analytics):
        """Display expense analytics visualizations"""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Amount", f"${analytics['total_amount']:,.2f}")
        with col2:
            st.metric("Total Expenses", analytics['total_count'])
        with col3:
            st.metric("Average Amount", f"${analytics['average_amount']:,.2f}")
        
        # Show visualizations
        tab1, tab2 = st.tabs(["Category Analysis", "Monthly Trend"])
        
        with tab1:
            fig = px.pie(
                values=list(analytics['by_category'].values()),
                names=list(analytics['by_category'].keys()),
                title="Expenses by Category"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            trend_data = pd.DataFrame(
                list(analytics['monthly_trend'].items()),
                columns=['Month', 'Amount']
            )
            fig = px.line(
                trend_data,
                x='Month',
                y='Amount',
                title="Monthly Expense Trend"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    """
    Expense Management Portal - Part 3C: Admin Interface and Dashboard
    This part contains the admin interface and main dashboard components.
    """

    def show_admin_expense_table(self, df):
        """Display expense table with approval controls for admins"""
        st.markdown("### Pending Approvals")
        
        pending_df = df[df['status'] == 'pending'].copy()
        if not pending_df.empty:
            for _, row in pending_df.iterrows():
                with st.expander(
                    f"📋 {row['date'].strftime('%Y-%m-%d')} - {row['category']} (${float(row['amount']):,.2f})"
                ):
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
                                    int(row['id']) + 1,
                                    'approved',
                                    comments,
                                    st.session_state.user_data['teacher_id']
                                ):
                                    st.success("Expense approved!")
                                    st.rerun()
                                    
                        with reject_col:
                            if st.button("❌ Reject", key=f"reject_{row['id']}"):
                                if self.update_expense_status(
                                    int(row['id']) + 1,
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
            status_class = {
                'pending': 'status-pending',
                'approved': 'status-approved',
                'rejected': 'status-rejected',
                'draft': 'status-draft'
            }.get(row['status'], '')
            
            with st.expander(
                f"{row['date'].strftime('%Y-%m-%d')} - {row['category']} (${float(row['amount']):,.2f})"
            ):
                st.markdown(
                    f'<span class="status-badge {status_class}">{row["status"].title()}</span>',
                    unsafe_allow_html=True
                )
                
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

    def show_dashboard(self):
        """Display main dashboard after login"""
        self.show_logged_in_header()

        # Sidebar navigation
        with st.sidebar:
            st.markdown("### Navigation")
            
            if st.button("📝 Submit Monthly Expenses", use_container_width=True):
                st.session_state.current_page = 'submit_expense'
                st.rerun()
                
            if st.button("📊 History & Analytics", use_container_width=True):
                st.session_state.current_page = 'history'
                st.rerun()
                
            if st.session_state.user_data['role'] == 'admin':
                if st.button("👥 Admin Dashboard", use_container_width=True):
                    st.session_state.current_page = 'admin'
                    st.rerun()
                    
            if st.button("👋 Logout", use_container_width=True):
                self.logout()
                st.rerun()

            # Display user role and info
            st.markdown("---")
            st.markdown("### User Info")
            st.markdown(f"**Name:** {st.session_state.user_data['name']}")
            st.markdown(f"**Role:** {st.session_state.user_data['role']}")
            st.markdown(f"**ID:** {st.session_state.user_data['teacher_id']}")

        # Show appropriate page based on navigation
        if st.session_state.current_page == 'submit_expense':
            self.show_monthly_expense_form()
        elif st.session_state.current_page == 'history':
            self.show_expense_history()
        elif st.session_state.current_page == 'admin' and st.session_state.user_data['role'] == 'admin':
            self.show_expense_history()  # Admin sees all expenses
        else:
            self.show_monthly_expense_form()  # Default to expense form


    def run(self):
        """Main application entry point"""
        if not st.session_state.authenticated:
            self.show_login()
        else:
            self.show_dashboard()

if __name__ == "__main__":
    app = ExpenseApp()
    app.run()