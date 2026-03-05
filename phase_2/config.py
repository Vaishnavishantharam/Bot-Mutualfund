"""
Phase 2: Embedding and vector store config.
"""

# Path to schemes.json (relative to project root)
SCHEMES_JSON_PATH = "data/schemes.json"

# Embedding model: sentence-transformers model name (local, no API key)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Vector store path (relative to project root); FAISS index + metadata saved here
VECTOR_STORE_PATH = "data/vector_store"

# Top-k for retrieval (used by Phase 3)
TOP_K = 5
