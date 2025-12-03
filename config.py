import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = "gpt-4o-mini"
    TEMPERATURE = 0.5
    
    # Database Settings
    DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")
    
    # Search Settings
    SEARCH_REGION = "us-en"
    
    # UI Settings
    PAGE_TITLE = "Data Visualization"
    PAGE_ICON = "🤖"