import streamlit as st
from logger import setup_logging
from db import init_db
from ui import login_register, render_main_ui
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting post_muse application")
    
    # Set page config
    try:
        st.set_page_config(page_title="Post Muse", layout="wide")
        logger.debug("Streamlit page configuration set")
    except Exception as e:
        logger.error(f"Failed to set page configuration: {e}")
        st.error(f"Page configuration error: {e}")
        return

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        st.error(f"Database initialization error: {e}")
        return

    # Render main UI
    try:
        render_main_ui()
        logger.debug("Main UI rendered successfully")
    except Exception as e:
        logger.error(f"Unexpected error in main UI rendering: {e}")
        st.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()