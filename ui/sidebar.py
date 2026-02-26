import streamlit as st
from database.chat_history import load_threads, delete_thread
from utils.session import reset_session
from ui.utils import load_conversation

def render_sidebar():
    """Render sidebar with conversations"""
    st.sidebar.title("Data Visualization Tool")
    
    if st.sidebar.button("➕ New Chat", width='stretch'):
        reset_session()
        st.rerun()
    
    st.sidebar.header("💬 Your Chats")
    
    # Load threads from database
    all_threads = load_threads()
    
    if all_threads:
        for thread in all_threads:
            thread_id = thread['thread_id']
            title = thread['title']
            
            col1, col2 = st.sidebar.columns([4, 1])
            
            with col1:
                if st.button(title, key=f"btn_{thread_id}", width='stretch'):
                    st.session_state['thread_id'] = thread_id
                    st.session_state['message_history'] = load_conversation(thread_id)
                    st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"del_{thread_id}"):
                    delete_thread(thread_id)
                    if st.session_state['thread_id'] == thread_id:
                        reset_session()
                    st.rerun()
    else:
        st.sidebar.info("No conversations yet. Start a new chat!")