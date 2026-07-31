import os
import sys

# Add the root directory to sys.path to resolve imports cleanly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_google_genai import ChatGoogleGenerativeAI
from utils.config import config


def create_llm():
    """Initialize and return the Google Gemini LLM instance for the agent."""
    return ChatGoogleGenerativeAI(
        model=config.MODEL_NAME,
        google_api_key=config.GEMINI_API_KEY,
        temperature=0.2,
    )


