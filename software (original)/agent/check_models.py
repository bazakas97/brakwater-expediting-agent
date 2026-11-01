"""List the model ids your Anthropic key can use, and check the model we would use.

Needs ANTHROPIC_API_KEY in your shell. Calls models.list() only, no messages. Never prints the key.

Usage:
    python check_models.py
"""
import os
import sys

import anthropic

from llm import model_name


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set in the environment.")

    available = [m.id for m in anthropic.Anthropic().models.list()]
    print("Available model ids:")
    for model_id in available:
        print(f"  {model_id}")

    wanted = model_name()
    status = "available" if wanted in available else "NOT in the list above"
    print(f"\nModel we would use: {wanted} -> {status}")


if __name__ == "__main__":
    main()
