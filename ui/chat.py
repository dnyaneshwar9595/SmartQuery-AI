# import streamlit as st
# from database.threads import save_thread
# from ui.chart_renderer import render_chart
# from core.graph import workflow

# from langchain_core.messages import HumanMessage
# import json
# import hashlib

# def render_chat_interface():
#     """
#     Main chat interface with improved message rendering and state handling.
#     """
    
#     # Display conversation history
#     for idx, message in enumerate(st.session_state["message_history"]):
#         with st.chat_message(message['role']):
            
#             # Render assistant messages with potential charts
#             if message['role'] == 'assistant':
                
#                 # Always show text content if present
#                 if message.get('content'):
#                     st.markdown(message['content'])
                
#                 # Render chart if configuration exists
#                 if message.get('chart_config'):
#                     chart_config = message['chart_config']
#                     unique_id = f"msg_{idx}_{message.get('message_id', 'default')}"
#                     render_chart(chart_config, unique_id=unique_id)
                
#                 # Show error if present
#                 if message.get('error'):
#                     st.error(f" Error: {message['error']}")
            
#             # Render user messages
#             else:
#                 st.markdown(message.get('content', ''))
    
#     # Chat input
#     user_input = st.chat_input("Ask me anything about your data...")
    
#     if user_input:
#         handle_user_message(user_input)

# def handle_user_message(user_input: str):
#     """
#     Process user message and generate response with proper state management.
#     """
    
#     # Check if this is the first message (for thread naming)
#     is_first_message = len(st.session_state["message_history"]) == 0
    
#     # Add user message to history
#     user_message = {
#         "role": "user",
#         "content": user_input,
#         "message_id": generate_message_id(user_input)
#     }
#     st.session_state["message_history"].append(user_message)
    
#     # Save thread if first message
#     if is_first_message:
#         title = create_thread_title(user_input)
#         save_thread(st.session_state['thread_id'], title)
    
#     # Display user message
#     with st.chat_message('user'):
#         st.markdown(user_input)
    
#     # Generate assistant response
#     config = {"configurable": {"thread_id": st.session_state['thread_id']}}
    
#     with st.chat_message('assistant'):
#         with st.spinner(" Thinking..."):
#             try:
#                 # Run workflow and get results
#                 result = workflow.invoke(
#                     {'messages': [HumanMessage(content=user_input)]},
#                     config=config
#                 )
                
#                 # Extract response components
#                 assistant_message = extract_assistant_response(result)
                
#                 # Display response
#                 if assistant_message.get('content'):
#                     st.markdown(assistant_message['content'])
                
#                 if assistant_message.get('chart_config'):
#                     current_idx = len(st.session_state["message_history"])
#                     unique_id = f"msg_{current_idx}_{assistant_message['message_id']}"
#                     render_chart(assistant_message['chart_config'], unique_id=unique_id)
                
#                 if assistant_message.get('error'):
#                     st.error(f"⚠️ {assistant_message['error']}")
                
#                 # Add to history
#                 st.session_state["message_history"].append(assistant_message)
                
#             except Exception as e:
#                 error_msg = f"An error occurred: {str(e)}"
#                 st.error(error_msg)
                
#                 # Add error message to history
#                 error_message = {
#                     "role": "assistant",
#                     "content": "I encountered an error processing your request.",
#                     "error": str(e),
#                     "message_id": generate_message_id(f"error_{user_input}")
#                 }
#                 st.session_state["message_history"].append(error_message)

# def extract_assistant_response(workflow_result: dict) -> dict:
#     """
#     Extract assistant response from workflow result with all relevant data.
    
#     Returns:
#         dict: {
#             'role': 'assistant',
#             'content': str,
#             'chart_config': dict or None,
#             'error': str or None,
#             'message_id': str
#         }
#     """
    
#     # Get last message content
#     messages = workflow_result.get('messages', [])
#     last_message_content = messages[-1].content if messages else "No response generated"
    
#     # Get chart config (if any)
#     chart_config = workflow_result.get('chart_config')
    
#     # Get error (if any)
#     error = workflow_result.get('error')
    
#     # Generate unique message ID for keying
#     message_id = generate_message_id(f"{last_message_content}_{chart_config}")
    
#     assistant_message = {
#         "role": "assistant",
#         "content": last_message_content,
#         "chart_config": chart_config,
#         "error": error,
#         "message_id": message_id
#     }
    
#     return assistant_message

# def create_thread_title(first_message: str, max_length: int = 50) -> str:
#     """
#     Create a readable thread title from the first message.
#     """
#     title = first_message.strip()
    
#     # Truncate if too long
#     if len(title) > max_length:
#         title = title[:max_length].rsplit(' ', 1)[0] + "..."
    
#     return title

# def generate_message_id(content: str) -> str:
#     """
#     Generate unique ID for a message based on its content.
#     Used for React key generation.
#     """
#     return hashlib.md5(content.encode()).hexdigest()[:12]

# def format_sql_display(sql: str) -> str:
#     """
#     Format SQL query for display with syntax highlighting.
#     """
#     return f"```sql\n{sql}\n```"

# def should_show_sql(state: dict) -> bool:
#     """
#     Determine if SQL query should be displayed to user.
#     """
#     # Show SQL if debug mode is enabled
#     debug_mode = st.session_state.get('debug_mode', False)
    
#     # Or if query was classified as 'db'
#     intent = state.get('intent')
    
#     return debug_mode or intent == 'db'

import streamlit as st
from database.threads import save_thread
from ui.chart_renderer import render_chart
from core.graph import workflow
from langchain_core.messages import HumanMessage
from config import Config
import hashlib

def render_chat_interface():
    """Main chat interface with message limit handling"""
    
    # Check if message limit reached
    message_count = len(st.session_state["message_history"])
    limit_reached = message_count >= Config.MAX_MESSAGES_PER_CHAT
    
    if limit_reached:
        st.warning(f"⚠️ Message limit reached ({Config.MAX_MESSAGES_PER_CHAT} messages). Please start a new chat.")
    
    # Display conversation
    for idx, message in enumerate(st.session_state["message_history"]):
        with st.chat_message(message['role']):
            if message['role'] == 'assistant':
                if message.get('content'):
                    st.markdown(message['content'])
                
                if message.get('chart_config'):
                    unique_id = f"msg_{idx}_{message.get('message_id', idx)}"
                    render_chart(message['chart_config'], unique_id=unique_id)
                
                if message.get('error'):
                    st.error(f"⚠️ {message['error']}")
            else:
                st.markdown(message.get('content', ''))
    
    # Chat input (disabled if limit reached)
    user_input = st.chat_input(
        "Ask about your data..." if not limit_reached else "Message limit reached - start new chat",
        disabled=limit_reached
    )
    
    if user_input:
        handle_user_message(user_input)


def handle_user_message(user_input: str):
    """Process user message"""
    
    is_first_message = len(st.session_state["message_history"]) == 0
    
    # Add user message
    user_message = {
        "role": "user",
        "content": user_input,
        "message_id": generate_message_id(user_input)
    }
    st.session_state["message_history"].append(user_message)
    
    # Save thread title on first message
    if is_first_message:
        title = user_input[:50] + ("..." if len(user_input) > 50 else "")
        save_thread(st.session_state['thread_id'], title)
    
    # Display user message
    with st.chat_message('user'):
        st.markdown(user_input)
    
    # Generate response
    config = {"configurable": {"thread_id": st.session_state['thread_id']}}
    
    with st.chat_message('assistant'):
        with st.spinner("🤔 Processing..."):
            try:
                result = workflow.invoke(
                    {'messages': [HumanMessage(content=user_input)]},
                    config=config
                )
                
                # Extract response
                last_message_content = result['messages'][-1].content if result.get('messages') else "No response"
                chart_config = result.get('chart_config')
                error = result.get('error')
                
                # Display response
                if last_message_content:
                    st.markdown(last_message_content)
                
                if chart_config:
                    current_idx = len(st.session_state["message_history"])
                    unique_id = f"msg_{current_idx}_{generate_message_id(last_message_content)}"
                    render_chart(chart_config, unique_id=unique_id)
                
                if error:
                    st.error(f"⚠️ {error}")
                
                # Save to history
                assistant_message = {
                    "role": "assistant",
                    "content": last_message_content,
                    "chart_config": chart_config,
                    "error": error,
                    "message_id": generate_message_id(last_message_content)
                }
                st.session_state["message_history"].append(assistant_message)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                
                st.session_state["message_history"].append({
                    "role": "assistant",
                    "content": "I encountered an error.",
                    "error": str(e),
                    "message_id": generate_message_id(f"error_{user_input}")
                })


def generate_message_id(content: str) -> str:
    """Generate unique message ID"""
    return hashlib.md5(content.encode()).hexdigest()[:12]