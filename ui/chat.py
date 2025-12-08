import streamlit as st
from database.threads import save_thread
from ui.utils import generate_response
from ui.chart_renderer import render_chart
import json
from core.graph import workflow
from langchain_core.messages import HumanMessage

def render_chat_interface():
    """Render main chat interface"""
    
    # Display message history
    for idx, message in enumerate(st.session_state["message_history"]):
        with st.chat_message(message['role']):
            # Check if message contains chart config
            if message['role'] == 'assistant' and message.get('chart_config'):
                chart_config = message['chart_config']
                render_chart(chart_config, unique_id=f"msg_{idx}")  # ✅ Pass unique ID with index
            else:
                st.markdown(message.get('content', ''))
    
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
            with st.spinner("🔍 Processing..."):
                # Get the full result with chart config
                result, chart_config = generate_response_with_chart(user_input, CONFIG)
                
                # Get current message index for unique key
                current_idx = len(st.session_state["message_history"])
                
                # Only render chart if chart_config exists
                if chart_config:
                    render_chart(chart_config, unique_id=f"msg_{current_idx}")  # ✅ Pass unique ID
                    st.session_state["message_history"].append({
                        "role": "assistant", 
                        "content": result,
                        "chart_config": chart_config
                    })
                else:
                    # Just text response
                    st.markdown(result)
                    st.session_state["message_history"].append({
                        "role": "assistant", 
                        "content": result
                    })
                    
def generate_response_with_chart(user_input, config):
    """Generate response and extract chart config if present"""
    from core.graph import workflow
    from langchain_core.messages import HumanMessage
    
    # Run the workflow
    result = workflow.invoke(
        {'messages': [HumanMessage(content=user_input)]},
        config=config
    )
    # print(result)
    # Extract chart config from state
    chart_config = result.get('chart_config')
    
    # Get last message content
    last_message = result['messages'][-1].content if result.get('messages') else "No response"
    
    return last_message, chart_config