
import os
from pathlib import Path

# API Configuration
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/generate")
CLAUDE_API_URL = os.environ.get("CLAUDE_API_URL", "https://api.anthropic.com/v1/messages")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Model Configuration
CLAUDE_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514", 
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307"
]

CLAUDE_VISION_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307"
]

DEFAULT_OLLAMA_MODEL = "llava"
DEFAULT_MODEL = "claude-3-haiku-20240307"

# Paths
DEFAULT_STATE_FILE = os.path.expanduser("~/.meal_plan_state.json")

# Image Extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
