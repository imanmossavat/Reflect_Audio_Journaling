"""
config.py — Single source of truth for all pipeline parameters.

Change values here. Nothing else needs to be touched.
"""

from pathlib import Path

# ── Timeline ──────────────────────────────────────────────────────────────────

DURATION_DAYS = 90          # 7 = one week, 14 = two weeks, 90 = three months

# ── Entities ──────────────────────────────────────────────────────────────────

MIN_ENTITIES  = 10          # validator enforces this lower bound
MAX_ENTITIES  = 20          # instruction to the model (not hard-enforced)

# ── Backend ───────────────────────────────────────────────────────────────────

BACKEND       = "anthropic" # "anthropic" | "ollama"

ANTHROPIC_MODEL = "claude-opus-4-6"
OLLAMA_MODEL    = "qwen2.5:32b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# ── Generation ────────────────────────────────────────────────────────────────

MAX_TOKENS  = 8192
MAX_RETRIES = 3             # local models need more retries than Claude

# ── Paths ─────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent / "outputs"
