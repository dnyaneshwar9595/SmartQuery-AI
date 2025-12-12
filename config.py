import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.05"))

    # Database Settings (Postgres for checkpointer + threads)
    DB_URI = os.getenv(
        "DB_URI",
        "postgresql://postgres:Kaustubh%407@localhost:5432/smart_query?sslmode=disable"
    )

    # AWS / Athena / Glue Settings
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

    GLUE_DATABASE_NAME = os.getenv("GLUE_DATABASE_NAME")
    ATHENA_WORKGROUP = os.getenv("ATHENA_WORKGROUP", "primary")
    ATHENA_OUTPUT_LOCATION = os.getenv("ATHENA_OUTPUT_LOCATION")
    
    # Athena query settings
    ATHENA_QUERY_TIMEOUT = int(os.getenv("ATHENA_QUERY_TIMEOUT", "120"))
    ATHENA_MAX_RETRIES = int(os.getenv("ATHENA_MAX_RETRIES", "3"))

    # Chat Settings
    MAX_MESSAGES_PER_CHAT = int(os.getenv("MAX_MESSAGES_PER_CHAT", "20"))  # 10 Q&A pairs
    
    # UI Settings
    PAGE_TITLE = os.getenv("PAGE_TITLE", "Data Visualization")
    PAGE_ICON = "🤖"
    
    # LangSmith (optional)
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "langgraph_demo")