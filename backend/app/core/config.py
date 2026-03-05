import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in: backend/ first, then project root (parent of backend/)
_here = Path(__file__).resolve().parent.parent.parent.parent  # project root
load_dotenv(_here / ".env")
load_dotenv()  # fallback — picks up .env in cwd

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"  # Fast & low-token. Switch to "llama-3.3-70b-versatile" for higher accuracy.

# Retrieval settings — keep lower for speed (higher = slower + more tokens)
TOP_K_RETRIEVAL = 5
TOP_K_CLAIM_EVIDENCE = 2

# Chunking settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
