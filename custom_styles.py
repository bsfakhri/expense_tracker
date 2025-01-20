# custom_styles.py

def get_css():
    return """
        <style>
        /* Main container */
        .main {
            padding: 1rem;
        }
        
        /* Header styling */
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            margin-bottom: 20px;
        }
        
        .user-info {
            text-align: right;
            color: #4B5563;
        }
        
        /* Card styling */
        .expense-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            height: 100%;
            margin-bottom: 1rem;
            transition: transform 0.2s;
        }
        
        .expense-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Status badge styling */
        .status-badge {
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        /* Form styling */
        .expense-form {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        
        /* Button styling */
        .stButton>button {
            border-radius: 8px;
            height: 42px;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Input styling */
        .stTextInput>div>div>input,
        .stNumberInput>div>div>input {
            border-radius: 8px;
        }
        
        .stSelectbox>div>div {
            border-radius: 8px;
        }
        
        /* Status colors */
        .no-entries { color: #6B7280; background: #F3F4F6; }
        .draft { color: #1E40AF; background: #DBEAFE; }
        .pending { color: #92400E; background: #FEF3C7; }
        .approved { color: #065F46; background: #D1FAE5; }
        .rejected { color: #991B1B; background: #FEE2E2; }
        
        /* Table styling */
        .expense-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .expense-table th {
            background: #F9FAFB;
            padding: 12px;
            text-align: left;
            font-weight: 500;
        }
        
        .expense-table td {
            padding: 12px;
            border-top: 1px solid #E5E7EB;
        }
        
        /* Login form styling */
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 2rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Year selector styling */
        .year-selector {
            min-width: 120px;
        }
        </style>
    """