"""RAG chatbot package — companion to Post 22."""
from dotenv import load_dotenv

load_dotenv()

__all__ = ["ingest", "retrieve", "prompt", "chat", "eval"]
