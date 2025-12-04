from langchain_openai import ChatOpenAI
from config import Config
from core.state import ChatState

# Initialize chatbot
chatbot = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    temperature=Config.TEMPERATURE
)

def create_chat_node(tools):
    """Factory function to create chat node with tools"""
    chatbot_with_tools = chatbot.bind_tools(tools)
    
    def chat_node(state: ChatState) -> ChatState:
        messages = state['messages']
        response = chatbot_with_tools.invoke(messages)
        return {'messages': [response]}
    
    return chat_node