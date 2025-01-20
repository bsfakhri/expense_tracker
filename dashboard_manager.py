import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

class DashboardManager:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.sheets_service = build('sheets', 'v4', credentials=credentials)
        self.expenses_sheet_id = st.secrets["EXPENSES_SHEET_ID"]
        self.drafts_sheet_id = st.secrets["DRAFTS_SHEET_ID"]

    def get_available_years(self) -> List[int]:
        """Get list of available years (current year ± 2 years)"""
        current_year = datetime.now().year
        return list(range(current_year - 2, current_year + 3))
    
    def get_all_months_status(self, year: int, teacher_id: str) -> Dict:
        """Get status and summary for all months in a single API call"""
        try:
            # Fetch all expenses for the year in one call
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.expenses_sheet_id,
                range='A2:M'  # Skip header row
            ).execute()
            
            # Initialize empty month data
            all_months_data = {month: {
                'status': 'no_entries',
                'total_amount': 0.00,
                'entry_count': 0,
                'draft_count': 0
            } for month in range(1, 13)}
            
            if 'values' in result:
                for row in result.get('values', []):
                    try:
                        expense_date = datetime.strptime(row[2], '%Y-%m-%d')
                        if expense_date.year == year and row[1] == teacher_id:
                            month = expense_date.month
                            all_months_data[month]['total_amount'] += float(row[5])
                            all_months_data[month]['entry_count'] += 1
                            if row[7] == 'draft':
                                all_months_data[month]['draft_count'] += 1
                            all_months_data[month]['status'] = row[7]
                    except (ValueError, IndexError):
                        continue
                        
            return all_months_data
                
        except Exception as e:
            st.error(f"Error fetching months status: {str(e)}")
            return {month: {
                'status': 'error',
                'total_amount': 0,
                'entry_count': 0,
                'draft_count': 0
            } for month in range(1, 13)}

    def get_month_status(self, year: int, month: int, teacher_id: str) -> Dict:
        """Get status and summary for a specific month"""
        try:
            # Check cache first
            cache_key = f"{year}_{month}_{teacher_id}"
            cached_data = st.session_state.get(f'cache_{cache_key}')
            cache_time = st.session_state.get(f'cache_time_{cache_key}')
            
            # Return cached data if it's less than 5 minutes old
            if cached_data and cache_time:
                if (datetime.now().timestamp() - cache_time) < 300:
                    return cached_data

            expenses = self._get_month_expenses(year, month, teacher_id)
            drafts = self._get_month_drafts(year, month, teacher_id)
            
            total_amount = sum(float(exp.get('amount', 0)) for exp in expenses)
            entry_count = len(expenses)
            draft_count = len(drafts)
            
            # Determine status
            if entry_count == 0 and draft_count == 0:
                status = "no_entries"
            elif draft_count > 0:
                status = "draft"
            elif any(exp.get('status') == 'rejected' for exp in expenses):
                status = "rejected"
            elif any(exp.get('status') == 'pending' for exp in expenses):
                status = "pending"
            else:
                status = "approved"
                
            result = {
                'status': status,
                'total_amount': total_amount,
                'entry_count': entry_count,
                'draft_count': draft_count
            }
            
            # Update cache
            st.session_state[f'cache_{cache_key}'] = result
            st.session_state[f'cache_time_{cache_key}'] = datetime.now().timestamp()
            
            return result
            
        except Exception as e:
            st.error(f"Error fetching month status: {str(e)}")
            return {
                'status': 'error',
                'total_amount': 0,
                'entry_count': 0,
                'draft_count': 0
            }

    def _get_month_expenses(self, year: int, month: int, teacher_id: str) -> List[Dict]:
        """Fetch expenses for a specific month"""
        try:
            # Use A1:M for all columns excluding the receipt columns (if any)
            range_name = 'A1:M'  # This gets id through comments columns
            
            try:
                result = self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=self.expenses_sheet_id,
                    range=range_name
                ).execute()
            except Exception as e:
                st.error(f"API Error: {str(e)}")
                st.error(f"Spreadsheet ID: {self.expenses_sheet_id}")
                return []

            if 'values' not in result:
                return []
                
            # Get headers from first row
            headers = result['values'][0]
                
            expenses = []
            # Start from index 1 to skip header row
            for row in result['values'][1:]:
                try:
                    if len(row) < 8:  # Ensure minimum columns exist
                        continue
                        
                    expense_date = datetime.strptime(row[2], '%Y-%m-%d')
                    if (expense_date.year == year and 
                        expense_date.month == month and 
                        row[1] == teacher_id):
                        expenses.append({
                            'id': row[0],
                            'amount': float(row[5]),
                            'status': row[7],
                        })
                except (ValueError, IndexError) as e:
                    continue
                    
            return expenses
        except Exception as e:
            st.error(f"Error in _get_month_expenses: {str(e)}")
            return []

    def _get_month_drafts(self, year: int, month: int, teacher_id: str) -> List[Dict]:
        """Fetch drafts for a specific month"""
        try:
            # Use A1:H to match your sheet structure
            range_name = 'A1:H'
            
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.drafts_sheet_id,
                range=range_name
            ).execute()
            
            if 'values' not in result:
                return []
                
            drafts = []
            # Skip header row
            for row in result['values'][1:]:
                try:
                    # Check if the row has enough columns
                    if len(row) < 5:  # we need at least 5 columns for basic info
                        continue
                        
                    # Match year and month string directly since that's how it's stored
                    row_month = row[1]  # 'January', 'February', etc.
                    row_year = int(row[2])  # 2025
                    
                    if (row_year == year and 
                        row_month == datetime.strptime(str(month), "%m").strftime("%B") and 
                        row[0] == teacher_id):
                        # Parse the expenses JSON string if needed
                        expenses_data = row[3] if len(row) > 3 else "[]"
                        
                        drafts.append({
                            'teacher_id': row[0],
                            'month': row[1],
                            'year': row_year,
                            'expenses': expenses_data,
                            'status': row[4] if len(row) > 4 else 'draft'
                        })
                except (ValueError, IndexError) as e:
                    st.error(f"Error processing draft row: {str(e)}")
                    continue
                    
            return drafts
        except Exception as e:
            st.error(f"Error in _get_month_drafts: {str(e)}")
            return []