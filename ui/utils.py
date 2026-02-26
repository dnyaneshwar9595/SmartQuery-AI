from core.orchestrator_graph import workflow
from database.chat_history import load_messages_by_thread
from langchain_core.messages import HumanMessage, AIMessage

def load_conversation(thread_id):
    """Load conversation messages from PostgreSQL database"""
    messages_from_db = load_messages_by_thread(thread_id)
    
    temp_messages = []
    for message in messages_from_db:
        if message['role'] == 'user':
            role = 'user'
        else:
            role = 'assistant'
        
        msg_dict = {'role': role, 'content': message['content']}
        if message.get('chart_config'):
            msg_dict['chart_config'] = message['chart_config']
        
        temp_messages.append(msg_dict)
    
    return temp_messages

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