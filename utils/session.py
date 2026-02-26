import streamlit as st

def reset_session():
    """Reset session state for new chat"""
    st.session_state['thread_id'] = None  # Will be created when first message arrives
    st.session_state['message_history'] = []

def initialize_session():
    """Initialize session state variables"""
    if "message_history" not in st.session_state:
        st.session_state["message_history"] = []
    
    if 'thread_id' not in st.session_state:
        st.session_state['thread_id'] = None  # Will be created when first message arrives