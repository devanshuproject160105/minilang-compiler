"""
AI Assistant integration for the MiniLang Compiler.
Uses Claude via Anthropic API when ANTHROPIC_API_KEY is configured,
with automated retry loops for natural language generation and
graceful fallback to offline heuristic templates.
"""

import os
from typing import Dict, Any, Optional, List
import dotenv

dotenv.load_dotenv()

from .templates import (
    offline_explain_error,
    offline_explain_stage,
    offline_generate_code,
    offline_optimization_hints,
)

MINILANG_GRAMMAR_SUMMARY = """
MiniLang Grammar Summary:
- Types: int, float, bool, string, void
- Variables: let x: int = 5; or let x = 5;
- Statements end with semicolon ';'
- Functions: fn add(a: int, b: int) -> int { return a + b; }
- Control flow: if (cond) { } else { }, while (cond) { }, for (let i = 0; i < n; i = i + 1) { }
- Builtins: print(arg1, arg2, ...);
- Comments: // single line
"""


class AIAssistant:
    def __init__(self):
        self.api_key: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key and self.api_key.strip() and not self.api_key.startswith("your_"):
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception:
                self.client = None

    def is_online(self) -> bool:
        return self.client is not None

    def explain_error(self, code: str, error: Dict[str, Any]) -> Dict[str, Any]:
        """Explains a compiler error in plain English with a suggested code fix."""
        if not self.is_online():
            return offline_explain_error(code, error)

        prompt = (
            f"You are an encouraging compiler construction instructor.\n"
            f"A student's MiniLang program failed compilation with the following error:\n"
            f"Stage: {error.get('stage')}\n"
            f"Error message: {error.get('message')}\n"
            f"Line: {error.get('line')}, Column: {error.get('column')}\n\n"
            f"Student's Code:\n```minilang\n{code}\n```\n\n"
            f"{MINILANG_GRAMMAR_SUMMARY}\n\n"
            f"Please provide:\n"
            f"1. A clear, plain-English explanation of why this error occurred.\n"
            f"2. The exact line and code that caused it.\n"
            f"3. A concrete suggested fix."
        )

        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            content_text = response.content[0].text
            line = error.get("line", 0)
            code_lines = code.split("\n")
            target_line = code_lines[line - 1] if 1 <= line <= len(code_lines) else ""

            return {
                "explanation": content_text,
                "suggested_fix": "See the AI recommendations above.",
                "line_number": line,
                "code_snippet": target_line,
                "mode": "claude-ai",
            }
        except Exception:
            # Fallback to offline heuristic on any API / network error
            return offline_explain_error(code, error)

    def explain_stage(self, code: str, stage: str, stage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provides a beginner-friendly explanation of what the current compiler stage did on this specific program."""
        if not self.is_online():
            return offline_explain_stage(stage, stage_data)

        prompt = (
            f"You are a computer science professor explaining the compiler construction pipeline.\n"
            f"Explain what the '{stage}' stage accomplished on the following MiniLang program:\n\n"
            f"Code:\n```minilang\n{code}\n```\n\n"
            f"Stage Data Summary:\n{str(stage_data)[:500]}\n\n"
            f"Keep your explanation concise, beginner-friendly, and educational (2-3 short paragraphs)."
        )

        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            content_text = response.content[0].text
            return {
                "title": f"Compiler Stage: {stage.capitalize()}",
                "summary": content_text,
                "what_happened": f"Detailed AI analysis of the {stage} phase on this program.",
                "compiler_concepts": "Formal verification and phase translation.",
                "mode": "claude-ai",
            }
        except Exception:
            return offline_explain_stage(stage, stage_data)

    def generate_code_with_validation(self, description: str, pipeline_class) -> Dict[str, Any]:
        """
        Translates a natural language description into valid MiniLang code.
        Validates with the compiler pipeline and retries up to 2 times if compilation fails.
        """
        if not self.is_online():
            code = offline_generate_code(description)
            pipeline = pipeline_class()
            res = pipeline.compile(code, execute=True)
            return {
                "code": code,
                "valid": res.success,
                "compilation_result": res.to_dict(),
                "attempts": 1,
                "mode": "offline-template",
            }

        prompt = (
            f"Write a complete, valid MiniLang program that satisfies this request:\n"
            f"\"{description}\"\n\n"
            f"{MINILANG_GRAMMAR_SUMMARY}\n"
            f"IMPORTANT: Respond ONLY with the valid MiniLang code inside a ```minilang ... ``` block. No markdown chatter."
        )

        attempts = 0
        max_attempts = 3
        current_code = ""

        while attempts < max_attempts:
            attempts += 1
            try:
                response = self.client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw_text = response.content[0].text
                # Extract code from code block
                if "```minilang" in raw_text:
                    current_code = raw_text.split("```minilang")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    current_code = raw_text.split("```")[1].split("```")[0].strip()
                else:
                    current_code = raw_text.strip()

                # Validate with the actual compiler!
                pipeline = pipeline_class()
                res = pipeline.compile(current_code, execute=True)

                if res.success:
                    return {
                        "code": current_code,
                        "valid": True,
                        "compilation_result": res.to_dict(),
                        "attempts": attempts,
                        "mode": "claude-ai",
                    }

                # If failed, feed error back into prompt for next attempt
                first_err = res.first_error or {"message": "Syntax or semantic validation error"}
                prompt = (
                    f"Your previously generated MiniLang code produced a compilation error:\n"
                    f"Error: {first_err.get('message')} at line {first_err.get('line')}\n\n"
                    f"Previous Code:\n```minilang\n{current_code}\n```\n\n"
                    f"Fix the error strictly following MiniLang syntax and output ONLY the corrected code in ```minilang ... ```."
                )
            except Exception:
                # If API fails during generation, fall back to offline generator
                current_code = offline_generate_code(description)
                pipeline = pipeline_class()
                res = pipeline.compile(current_code, execute=True)
                return {
                    "code": current_code,
                    "valid": res.success,
                    "compilation_result": res.to_dict(),
                    "attempts": attempts,
                    "mode": "offline-fallback",
                }

        # Return best attempt if still failing
        return {
            "code": current_code,
            "valid": False,
            "compilation_result": res.to_dict() if 'res' in locals() else None,
            "attempts": attempts,
            "mode": "claude-ai",
        }

    def get_optimization_hints(self, code: str, ir: List[Dict[str, Any]], optimized_ir: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Suggests optimizations for the program."""
        if not self.is_online():
            return offline_optimization_hints(code)

        prompt = (
            f"Analyze this MiniLang program and its Intermediate Representation (IR):\n\n"
            f"MiniLang Code:\n```minilang\n{code}\n```\n\n"
            f"IR Instruction Count: {len(ir)}\n"
            f"Optimized IR Count: {len(optimized_ir)}\n\n"
            f"Provide 2-3 specific optimization hints for how the code or algorithm can be improved. "
            f"Format each with a category name and a 1-2 sentence actionable suggestion."
        )

        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            return [{"category": "AI Suggestion", "hint": text}]
        except Exception:
            return offline_optimization_hints(code)
