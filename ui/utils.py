from core.graph import workflow
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Dict, Any
import hashlib

def load_conversation(thread_id: str) -> List[Dict[str, Any]]:
    """
    Load complete conversation history including charts from workflow state.
    
    This function reconstructs the full message history with chart configurations
    that were generated during the conversation.
    """
    try:
        # Get state from workflow checkpoint
        state = workflow.get_state(config={"configurable": {"thread_id": thread_id}})
        
        if not state or not state.values:
            return []
        
        messages = state.values.get('messages', [])
        
        # Track chart configs by message index
        # We need to pair charts with their corresponding AI messages
        formatted_messages = []
        chart_config = state.values.get('chart_config')
        
        # Process messages
        for idx, message in enumerate(messages):
            
            # Determine role
            if isinstance(message, HumanMessage):
                formatted_message = {
                    'role': 'user',
                    'content': message.content,
                    'message_id': generate_message_id(f"user_{idx}_{message.content}")
                }
            
            elif isinstance(message, AIMessage):
                formatted_message = {
                    'role': 'assistant',
                    'content': message.content,
                    'message_id': generate_message_id(f"ai_{idx}_{message.content}")
                }
                
                # Attach chart config to the LAST assistant message
                # (since chart is generated after the query response)
                if idx == len(messages) - 1 and chart_config:
                    formatted_message['chart_config'] = chart_config
            
            else:
                # Handle other message types
                formatted_message = {
                    'role': 'assistant',
                    'content': str(message.content) if hasattr(message, 'content') else str(message),
                    'message_id': generate_message_id(f"msg_{idx}")
                }
            
            formatted_messages.append(formatted_message)
        
        return formatted_messages
        
    except Exception as e:
        print(f" Error loading conversation {thread_id}: {e}")
        return []

def load_conversation_with_state_history(thread_id: str) -> List[Dict[str, Any]]:
    """
    Advanced: Load conversation by replaying state history.
    This captures chart configs at each step.
    
    Note: This is more comprehensive but slower for long conversations.
    """
    try:
        # Get all state history
        state_history = list(workflow.get_state_history(
            config={"configurable": {"thread_id": thread_id}}
        ))
        
        if not state_history:
            return []
        
        # We'll build messages by walking through history
        formatted_messages = []
        
        # Track which messages we've seen
        seen_message_ids = set()
        
        for state_snapshot in reversed(state_history):  # Oldest first
            values = state_snapshot.values
            
            messages = values.get('messages', [])
            chart_config = values.get('chart_config')
            
            # Process messages in this state
            for idx, message in enumerate(messages):
                message_hash = hash_message(message)
                
                if message_hash in seen_message_ids:
                    continue
                
                seen_message_ids.add(message_hash)
                
                # Format message
                if isinstance(message, HumanMessage):
                    formatted = {
                        'role': 'user',
                        'content': message.content,
                        'message_id': generate_message_id(f"user_{message_hash}")
                    }
                
                elif isinstance(message, AIMessage):
                    formatted = {
                        'role': 'assistant',
                        'content': message.content,
                        'message_id': generate_message_id(f"ai_{message_hash}")
                    }
                    
                    # If this state has a chart, attach it
                    if chart_config and idx == len(messages) - 1:
                        formatted['chart_config'] = chart_config
                
                else:
                    formatted = {
                        'role': 'assistant',
                        'content': str(message),
                        'message_id': generate_message_id(f"msg_{message_hash}")
                    }
                
                formatted_messages.append(formatted)
        
        return formatted_messages
        
    except Exception as e:
        print(f" Error loading conversation history: {e}")
        # Fallback to simple load
        return load_conversation(thread_id)

def hash_message(message) -> str:
    """Generate hash for a message to detect duplicates"""
    content = message.content if hasattr(message, 'content') else str(message)
    return hashlib.md5(content.encode()).hexdigest()

def generate_message_id(content: str) -> str:
    """Generate unique ID for a message"""
    return hashlib.md5(content.encode()).hexdigest()[:12]

def get_conversation_summary(thread_id: str) -> str:
    """
    Get a brief summary of a conversation for display.
    """
    messages = load_conversation(thread_id)
    
    if not messages:
        return "Empty conversation"
    
    # Count message types
    user_msgs = sum(1 for m in messages if m['role'] == 'user')
    ai_msgs = sum(1 for m in messages if m['role'] == 'assistant')
    charts = sum(1 for m in messages if m.get('chart_config'))
    
    return f"{user_msgs} questions, {ai_msgs} responses, {charts} charts"

def export_conversation_to_json(thread_id: str) -> Dict[str, Any]:
    """
    Export conversation to JSON format for backup/sharing.
    """
    messages = load_conversation(thread_id)
    
    return {
        'thread_id': thread_id,
        'message_count': len(messages),
        'messages': messages
    }