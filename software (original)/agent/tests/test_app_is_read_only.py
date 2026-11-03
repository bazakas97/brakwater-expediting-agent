"""The page may write ONLY data/reviews.json, and only through reviews.py.
It must never be able to call the LLM, the ERP API or send email."""
import ast
from pathlib import Path

AGENT = Path(__file__).parent.parent

FORBIDDEN_IMPORTS = {"llm", "anthropic", "openai", "keelson_client", "httpx", "requests", "decision", "context",
                     "triage", "build_decisions", "memo_facts", "erp_proposals", "smtplib", "email", "socket", "urllib"}
WRITE_CALLS = {"open", "write_text", "write_bytes", "dump", "rename", "remove", "unlink", "mkdir"}
FILE_MODULES = {"os", "shutil", "tempfile"}  # how os.replace or copying would sneak in


def imported_modules(path: Path) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def called_names(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            func = node.func
            names.add(func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", ""))
    return names


def test_page_and_helpers_import_nothing_that_can_reach_the_llm_the_api_or_email():
    for name in ["app.py", "view.py", "reviews.py"]:
        assert imported_modules(AGENT / name) & FORBIDDEN_IMPORTS == set(), name


def test_the_page_does_not_write_files_itself():
    # All writing goes through reviews.save_review, which is tested to write only reviews.json.
    assert called_names(AGENT / "app.py") & WRITE_CALLS == set()


def test_the_page_does_not_import_file_modules():
    assert imported_modules(AGENT / "app.py") & FILE_MODULES == set()


def test_the_page_only_saves_through_reviews_save_review():
    imported = imported_modules(AGENT / "app.py")
    assert "reviews" in imported
    assert "save_review" in called_names(AGENT / "app.py")
