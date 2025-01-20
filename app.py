"""
Expense Management Portal - Complete Application
"""

import streamlit as st
import pandas as pd
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

    def _initialize_google_services(self):
        """Initialize Google Sheets and Drive services with caching"""
        @st.cache_resource
        def _get_services(_):
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"],
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive.file'
                    ]
                )
                sheets = build('sheets', 'v4', credentials=credentials)
                drive = build('drive', 'v3', credentials=credentials)
                return sheets, drive
            except Exception as e:
                st.error(f"Error initializing Google services: {str(e)}")
                raise
        
        return _get_services(1)  # Pass dummy argument for caching
    def test_drive_access(self):
        """Test Drive API access"""
        try:
            # List files to test access
            results = self.drive_service.files().list(
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            return True
        except Exception as e:
            st.error(f"Drive API error: {str(e)}")
            return False

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

    def show_expense_form(self):
        """Display expense submission form"""
        st.markdown("### Submit New Expense")

        with st.form("expense_form", clear_on_submit=True):
            date = st.date_input(
                "Date of Expense",
                value=datetime.now().date()
            )

            category = st.selectbox(
                "Category",
                options=self.get_expense_categories()
            )

            vendor = st.selectbox(
                "Vendor",
                options=self.get_vendors()
            )

            if vendor == "Other":
                custom_vendor = st.text_input("Specify Vendor")
                vendor = custom_vendor if custom_vendor else vendor

            amount = st.number_input(
                "Amount",
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )

            description = st.text_area(
                "Description",
                placeholder="Enter expense details..."
            )

            submitted = st.form_submit_button("Submit Expense")
            
        if submitted:
            if category == "Select Category":
                st.error("Please select a category")
                return
            if vendor == "Select Vendor":
                st.error("Please select or specify a vendor")
                return
            if amount <= 0:
                st.error("Please enter a valid amount")
                return
            if not description:
                st.error("Please provide a description")
                return

                        # Prepare expense data
            # Get the next ID
            next_id = len(self.read_sheet_to_df(self.expenses_sheet_id, 'A:L')) + 1
            
            # Ensure all 12 columns are properly formatted
            expense_data = [
                str(next_id),                                    # ID (column A)
                str(st.session_state.user_data['teacher_id']),   # Teacher ID (column B)
                date.strftime('%Y-%m-%d'),                       # Date (column C)
                str(category),                                   # Category (column D)
                str(vendor),                                     # Vendor (column E)
                str(float(amount)),                             # Amount (column F)
                str(description),                               # Description (column G)
                'pending',                                       # Status (column H)
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),    # Submitted date (column I)
                ' ',                                             # Approved by (column J)
                ' ',                                             # Approved date (column K)
                ' '                                              # Comments (column L)
            ]
                        # Validate that we have exactly 12 columns before submitting
            if len(expense_data) != 12:
                st.error(f"Internal error: Expected 12 columns, got {len(expense_data)}")
                return False

            if self.append_to_sheet(self.expenses_sheet_id, 'A:L', [expense_data]):
                st.success("Expense submitted successfully!")
                with st.expander("View Submitted Expense"):
                    st.json({
                        'Date': date.strftime('%Y-%m-%d'),
                        'Category': category,
                        'Vendor': vendor,
                        'Amount': f"${amount:.2f}",
                        'Description': description,
                        'Status': 'Pending Approval'
                    })
            else:
                st.error("Failed to submit expense. Please try again.")

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

    def show_dashboard(self):
        """Display main dashboard after login"""
        self.show_logged_in_header()

        # Sidebar for navigation
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
            self.show_expense_history()  # Admin sees all expenses
        else:
            self.show_expense_form()  # Default to expense form

    def logout(self):
        """Handle user logout"""
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.rerun()

    def run(self):
        """Main application entry point"""
        if not st.session_state.authenticated:
            self.show_login()
        else:
            self.show_dashboard()

if __name__ == "__main__":
    app = ExpenseApp()
    app.run()