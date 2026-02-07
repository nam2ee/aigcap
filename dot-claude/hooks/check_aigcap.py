#!/usr/bin/env python3
"""
AIGCAP PreToolUse Hook (for Write)
Runs BEFORE Claude writes a file. Checks if the content includes AIGCAP header.
If missing on a code file, blocks the write (exit 2) and tells Claude to fix it.

Also works as PostToolUse Hook (for Edit)
Runs AFTER Claude edits a file. Checks the file on disk for AIGCAP header.
If missing, outputs feedback so Claude re-edits to add it.

Usage in settings.json:
  PreToolUse matcher "Write"  → blocks write if no header in content
  PostToolUse matcher "Edit"  → warns after edit if file lacks header
"""
import json
import sys
import os

CODE_EXTENSIONS = {
    ".rs", ".c", ".h", ".cpp", ".hpp", ".java",
    ".js", ".jsx", ".ts", ".tsx",
    ".go", ".swift", ".kt", ".scala", ".cs",
    ".py", ".rb", ".sh", ".bash",
    ".css", ".scss",
    ".sql", ".lua", ".hs",
    ".html", ".xml", ".svg", ".vue",
}

SKIP_PATTERNS = [
    "node_modules", ".git", "__pycache__",
    "target/debug", "target/release", "dist/", "build/",
    "package.json", "package-lock.json", "Cargo.lock", "yarn.lock",
    "Cargo.toml", "pyproject.toml", "go.mod", "go.sum",
    "tsconfig.json", ".eslintrc", ".prettierrc",
    "CLAUDE.md", "AIGCAP_PROTOCOL.md", "README.md", "CHANGELOG.md", "LICENSE",
    ".env", ".gitignore", ".dockerignore",
    "Makefile", "Dockerfile", "docker-compose",
    "__init__.py",  # usually empty or trivial
]

BANNER = "THIS FILE INCLUDES AI GENERATED CODE"
PROTOCOL_PATH = "~/.claude/protocols/AIGCAP_PROTOCOL.md"


def should_check(file_path: str) -> bool:
    if not file_path:
        return False
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in CODE_EXTENSIONS:
        return False
    basename = os.path.basename(file_path)
    for pattern in SKIP_PATTERNS:
        if pattern in file_path or pattern == basename:
            return False
    return True


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path", "")

    if not should_check(file_path):
        sys.exit(0)

    # --- PreToolUse on Write: check content before it's written ---
    if tool_name == "Write":
        content = tool_input.get("content", "")
        if BANNER in content:
            sys.exit(0)  # header present, allow

        print(
            f"⚠️ AIGCAP BLOCKED: '{file_path}' is missing the AIGCAP header.\n"
            f"Read {PROTOCOL_PATH} and include the header at the top of the file.\n"
            f"Then retry the Write with the header included.",
            file=sys.stderr,
        )
        sys.exit(2)  # block the write

    # --- PostToolUse on Edit: check file on disk after edit ---
    if tool_name in ("Edit", "MultiEdit"):
        try:
            if not os.path.isfile(file_path):
                sys.exit(0)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                head = "".join(f.readline() for _ in range(50))
            if BANNER in head:
                sys.exit(0)

            # Output to stdout — Claude sees this as feedback
            print(
                f"⚠️ AIGCAP WARNING: '{file_path}' has no AIGCAP header after your edit.\n"
                f"Read {PROTOCOL_PATH} and add the AIGCAP header to the top of this file now."
            )
        except Exception:
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()
