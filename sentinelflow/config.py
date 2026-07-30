"""Central configuration. Model and temperature are pinned here so every run
is reproducible; the trace records whatever values were actually used."""

import os

from dotenv import load_dotenv

load_dotenv()

# Pinned defaults per provider. Override via SENTINELFLOW_MODEL only when
# deliberately changing the eval configuration.
DEFAULT_MODELS = {
    "openai": "gpt-4o-2024-08-06",
    "anthropic": "claude-sonnet-4-20250514",
    "gemini": "gemini-3.5-flash-lite",
    "groq": "llama-3.3-70b-versatile",
}

# Free-tier providers served through their OpenAI-compatible endpoints.
OPENAI_COMPATIBLE = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
    },
}

TEMPERATURE = float(os.environ.get("SENTINELFLOW_TEMPERATURE", "0.0"))
MAX_REVISIONS = 2  # Critic rejections beyond this -> unresolved, human review
STRUCTURED_OUTPUT_RETRIES = 1  # one retry with validation-error feedback

EVAL_RUNS = 3  # Stage 5: repeats per case/configuration

DB_PATH = os.environ.get("SENTINELFLOW_DB", "sentinelflow.db")
RUNS_DIR = os.environ.get("SENTINELFLOW_RUNS_DIR", "runs")


def detect_provider() -> str | None:
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    return None


def model_name(provider: str) -> str:
    return os.environ.get("SENTINELFLOW_MODEL") or DEFAULT_MODELS[provider]
