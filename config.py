import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = "gpt-4o-mini"
    TEMPERATURE = 0.5
    
    # AWS Athena Settings
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    ATHENA_S3_OUTPUT_LOCATION = os.getenv("ATHENA_S3_OUTPUT_LOCATION")
    ATHENA_DATABASE = os.getenv("ATHENA_DATABASE")
    ATHENA_WORKGROUP = os.getenv("ATHENA_WORKGROUP", "primary")
    
    # Database Settings (for other purposes)
    DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")
    
    # Search Settings
    SEARCH_REGION = "us-en"
    
    # UI Settings
    PAGE_TITLE = "Data Visualization"
    PAGE_ICON = "🤖"