"""
MiniLang Visual Compiler Pipeline - Entrypoint Script.
Launches the Flask web server or runs CLI compilation.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from compiler.pipeline import CompilerPipeline
from web.app import app


def run_cli(source_file: str):
    path = Path(source_file)
    if not path.exists():
        print(f"Error: File '{source_file}' does not exist.")
        sys.exit(1)

    code = path.read_text(encoding="utf-8")
    print(f"--- Compiling {path.name} ---")
    pipeline = CompilerPipeline()
    res = pipeline.compile(code, execute=True)

    if not res.success:
        print(f"\n[COMPILATION FAILED at {res.first_error.get('stage').upper()} STAGE]")
        print(f"Message: {res.first_error.get('message')}")
        print(f"Line: {res.first_error.get('line')}, Column: {res.first_error.get('column')}")
        sys.exit(1)

    print("\n[ALL 7 STAGES COMPLETED SUCCESSFULLY]")
    print(f"- Tokens scanned: {len(res.tokens)}")
    print(f"- IR Instructions: {len(res.ir)} (Optimized down to: {len(res.optimized_ir)})")
    print(f"- Bytecode instructions: {len(res.bytecode)}")
    print(f"- Fired optimization rules: {len(res.optimization_logs)}")

    print("\n--- Program Output ---")
    if res.execution and res.execution.get("output"):
        for line in res.execution["output"]:
            print(line)
    else:
        print("(No stdout)")


def main():
    parser = argparse.ArgumentParser(description="MiniLang AI-Assisted Visual Compiler Pipeline")
    parser.add_argument("--cli", type=str, help="Path to a .mlang file to compile and run via terminal")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)), help="Port for the web server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address for web server")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")

    args = parser.parse_args()

    if args.cli:
        run_cli(args.cli)
    else:
        print("=" * 65)
        print(" MiniLang - AI-Assisted Compiler with Visual Pipeline")
        print("=" * 65)
        print(f" Web IDE Server running at: http://{args.host}:{args.port}/")
        print(" Press Ctrl+C to terminate.")
        print("=" * 65)
        app.run(host=args.host, port=args.port, debug=not args.no_debug)


if __name__ == "__main__":
    main()
