import streamlit as st
from database.chat_history import save_message, create_thread, load_messages_by_thread
from ui.utils import generate_response
from ui.chart_renderer import render_chart
from core.orchestrator_graph import workflow
import json
from langchain_core.messages import HumanMessage, AIMessage

def render_chat_interface():
    """Render main chat interface"""
    
    # Display message history
    for idx, message in enumerate(st.session_state["message_history"]):
        with st.chat_message(message['role']):
            # Check if message contains chart config
            if message['role'] == 'assistant' and message.get('chart_config'):
                chart_config = message['chart_config']
                render_chart(chart_config, unique_id=f"msg_{idx}")
            else:
                st.markdown(message.get('content', ''))
    
    # Chat input
    user_input = st.chat_input("What's in your mind?")
    
    if user_input:
        # Check if first message (thread_id will be None)
        is_first_message = st.session_state['thread_id'] is None
        
        # Create thread if first message
        if is_first_message:
            title = user_input[:50] + ("..." if len(user_input) > 50 else "")
            thread_id = create_thread(title)
            st.session_state['thread_id'] = thread_id
        
        # Add user message to session state
        st.session_state["message_history"].append({"role": "user", "content": user_input})
        
        # Save user message to database
        save_message(st.session_state['thread_id'], 'user', user_input)
        
        # Display user message
        with st.chat_message('user'):
            st.markdown(user_input)
        
        # Generate and display assistant response
        CONFIG = {"configurable": {"thread_id": st.session_state['thread_id']}}
        
        with st.chat_message('assistant'):
            with st.spinner("🔍 Processing..."):
                # Get the full result with chart config
                last_message, chart_config = generate_response_with_chart(user_input, CONFIG)
                
                # Get current message index for unique key
                current_idx = len(st.session_state["message_history"])
                
                # Save assistant message to database
                save_message(st.session_state['thread_id'], 'assistant', last_message, chart_config)
                
                # Only render chart if chart_config exists
                if chart_config:
                    render_chart(chart_config, unique_id=f"msg_{current_idx}")
                    st.session_state["message_history"].append({
                        "role": "assistant", 
                        "content": last_message,
                        "chart_config": chart_config
                    })
                else:
                    # Just text response
                    st.markdown(last_message)
                    st.session_state["message_history"].append({
                        "role": "assistant", 
                        "content": last_message
                    })
                    
def generate_response_with_chart(user_input, config):
    """Generate response and extract chart config if present"""
    print(f"user input is {user_input}")
    
    # Build conversation history from session state
    messages = []
    for msg in st.session_state["message_history"]:
        if msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['content']))
        else:
            messages.append(AIMessage(content=msg['content']))
    
    # Add current user message
    messages.append(HumanMessage(content=user_input))
    
    # Run the workflow (checkpointer is already compiled in graph.py)
    result = workflow.invoke(
        {'messages': messages},
        config=config
    )
    # Extract chart config from state
    chart_config = result.get("chart_config")
    # Get last message content
    last_message = result['messages'][-1].content if result.get('messages') else "No response"
    
    return last_message, chart_config