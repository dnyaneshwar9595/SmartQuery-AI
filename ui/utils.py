from core.graph import workflow
from langchain_core.messages import HumanMessage

def load_conversation(thread_id):
    """Load conversation from workflow state"""
    try:
        state = workflow.get_state(config={"configurable": {"thread_id": thread_id}})
        messages = state.values.get('messages', [])
        
        temp_messages = []
        for message in messages:
            if isinstance(message, HumanMessage):
                role = 'user'
            else:
                role = 'assistant'
            temp_messages.append({'role': role, 'content': message.content})
        
        return temp_messages
    except Exception as e:
        return []

def generate_response(user_input, config):
    """Generate response and stream final assistant message"""
    for event in workflow.stream(
        {'messages': [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="values"
    ):
        messages = event.get('messages', [])
        if messages:
            last_msg = messages[-1]
            
            if hasattr(last_msg, 'content') and last_msg.content:
                if last_msg.__class__.__name__ == 'AIMessage':
                    if not hasattr(last_msg, 'tool_calls') or not last_msg.tool_calls:
                        yield last_msg.content
                        break