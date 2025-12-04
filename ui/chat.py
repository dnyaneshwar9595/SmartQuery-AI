import streamlit as st
from database.threads import save_thread
from ui.utils import generate_response

def render_chat_interface():
    """Render main chat interface"""
    
    # Display message history
    for message in st.session_state["message_history"]:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
    
    # Chat input
    user_input = st.chat_input("What's in your mind?")
    
    if user_input:
        # Check if first message
        is_first_message = len(st.session_state["message_history"]) == 0
        
        # Add user message
        st.session_state["message_history"].append({"role": "user", "content": user_input})
        
        # Save thread if first message
        if is_first_message:
            title = user_input[:50] + ("..." if len(user_input) > 50 else "")
            save_thread(st.session_state['thread_id'], title)
        
        # Display user message
        with st.chat_message('user'):
            st.markdown(user_input)
        
        # Generate and display assistant response
        CONFIG = {"configurable": {"thread_id": st.session_state['thread_id']}}
        
        with st.chat_message('assistant'):
            ai_message = st.write_stream(generate_response(user_input, CONFIG))
        
        # Add assistant message to history
        st.session_state["message_history"].append({"role": "assistant", "content": ai_message})