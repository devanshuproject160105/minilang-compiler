"""
AI Assistant module for MiniLang compiler.
"""

from .assistant import AIAssistant
from .templates import (
    offline_explain_error,
    offline_explain_stage,
    offline_generate_code,
    offline_optimization_hints,
)

__all__ = [
    "AIAssistant",
    "offline_explain_error",
    "offline_explain_stage",
    "offline_generate_code",
    "offline_optimization_hints",
]
