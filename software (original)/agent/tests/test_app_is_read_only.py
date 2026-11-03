"""The page must never be able to call the LLM or the ERP API: it only reads data/decisions.json."""
import ast
from pathlib import Path

FORBIDDEN = {"llm", "anthropic", "openai", "keelson_client", "httpx", "requests", "decision", "context",
             "triage", "build_decisions"}


def imported_modules(path: Path) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_app_imports_nothing_that_can_reach_the_llm_or_the_api():
    app = Path(__file__).parent.parent / "app.py"
    assert imported_modules(app) & FORBIDDEN == set()


def test_view_imports_nothing_that_can_reach_the_llm_or_the_api():
    view = Path(__file__).parent.parent / "view.py"
    assert imported_modules(view) & FORBIDDEN == set()
