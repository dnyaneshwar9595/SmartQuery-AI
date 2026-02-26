import streamlit as st
from config import Config
from utils.session import initialize_session
from ui.sidebar import render_sidebar
from ui.chat import render_chat_interface
from database.chat_history import create_tables

# Page configuration
st.set_page_config(
    page_title=Config.PAGE_TITLE,
    page_icon=Config.PAGE_ICON,
    layout="wide"
)

# Initialize database tables
create_tables()

# Initialize session
initialize_session()

# Render UI
render_sidebar()
render_chat_interface()