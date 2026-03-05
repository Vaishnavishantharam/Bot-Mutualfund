"""
Phase 3: Groq LLM and pipeline config. Answer only from embeddings; PII/personal info out of scope.
Loads GROQ_API_KEY from .env (project root) or from environment.
"""
import os
from pathlib import Path

# Load .env: first from phase_3 folder, then from project root
_phase_3_dir = Path(__file__).resolve().parent
_project_root = _phase_3_dir.parent
for _dotenv_path in (_phase_3_dir / ".env", _project_root / ".env"):
    if _dotenv_path.is_file():
        try:
            from dotenv import load_dotenv
            load_dotenv(_dotenv_path)
        except ImportError:
            pass
        break  # first .env found wins

# Groq: GROQ_API_KEY from .env or environment; model for chat completion
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Approved citation URLs (must be one of these); fallback for refusals / not in corpus
APPROVED_URLS = [
    "https://www.indmoney.com/mutual-funds/hdfc-large-cap-fund-direct-plan-growth-option-2989",
    "https://www.indmoney.com/mutual-funds/hdfc-flexi-cap-fund-direct-plan-growth-option-3184",
    "https://www.indmoney.com/mutual-funds/hdfc-mid-cap-fund-direct-plan-growth-option-3097",
    "https://www.indmoney.com/mutual-funds/hdfc-small-cap-fund-direct-growth-option-3580",
    "https://www.indmoney.com/mutual-funds/hdfc-nifty-100-index-fund-direct-growth-1040567",
]

# Top-k chunks for retrieval (passed to phase_2.query_store); final list passed to generator
TOP_K = 5
# When we detect a scheme, retrieve this many then filter to that scheme only (so right fund is always returned)
TOP_K_RETRIEVE_FOR_SCHEME = 50
