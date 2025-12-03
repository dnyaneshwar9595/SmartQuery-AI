from langchain_community.tools import DuckDuckGoSearchRun
from config import Config

def get_search_tool():
    """Get configured search tool"""
    return DuckDuckGoSearchRun(region=Config.SEARCH_REGION)