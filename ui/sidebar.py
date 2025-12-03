import streamlit as st
from database.threads import load_all_threads, delete_thread
from utils.session import reset_session
from ui.utils import load_conversation

def render_sidebar():
    """Render sidebar with conversations"""
    st.sidebar.title("🤖 LangGraph Chatbot")
    
    if st.sidebar.button("➕ New Chat", use_container_width=True):
        reset_session()
        st.rerun()
    
    st.sidebar.header("💬 My Conversations")
    
    # Load threads from database
    all_threads = load_all_threads()
    
    if all_threads:
        for thread_id, title in all_threads:
            col1, col2 = st.sidebar.columns([4, 1])
            
            with col1:
                if st.button(title, key=f"btn_{thread_id}", use_container_width=True):
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