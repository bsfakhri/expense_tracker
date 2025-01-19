import streamlit as st

def main():
    try:
        # Try to access the secrets
        st.write("Testing secrets access:")
        st.write("USERS_SHEET_ID exists:", "USERS_SHEET_ID" in st.secrets)
        st.write("All available secret keys:", list(st.secrets.keys()))
    except Exception as e:
        st.error(f"Error accessing secrets: {str(e)}")

if __name__ == "__main__":
    main()