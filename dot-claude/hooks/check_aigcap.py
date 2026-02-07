#!/usr/bin/env python3
"""
AIGCAP PreToolUse Hook (for Write)
Runs BEFORE Claude writes a file. Checks if the content includes AIGCAP header
and REVIEWED-BY-HUMAN: NO. Blocks if missing or if Claude tries to write YES.

Also works as PostToolUse Hook (for Edit)
Runs AFTER Claude edits a file. Checks the file on disk.
If REVIEWED-BY-HUMAN: YES remains after Claude's edit, tells Claude to reset to NO.

Usage in settings.json:
  PreToolUse matcher "Write"  → blocks write if no header or REVIEWED-BY-HUMAN issue
  PostToolUse matcher "Edit"  → warns after edit if header missing or YES not reset
"""
import json
import sys
import os
import re

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
    "__init__.py",
]

BANNER = "THIS FILE INCLUDES AI GENERATED CODE"
REVIEWED_NO = re.compile(r"REVIEWED-BY-HUMAN\s*:\s*NO", re.IGNORECASE)
REVIEWED_YES = re.compile(r"REVIEWED-BY-HUMAN\s*:\s*YES", re.IGNORECASE)
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

        # Check 1: AIGCAP banner must be present
        if BANNER not in content:
            print(
                f"⚠️ AIGCAP BLOCKED: '{file_path}' is missing the AIGCAP header.\n"
                f"Read {PROTOCOL_PATH} and include the header at the top of the file.\n"
                f"Then retry the Write with the header included.",
                file=sys.stderr,
            )
            sys.exit(2)

        # Check 2: Claude must NOT write REVIEWED-BY-HUMAN: YES
        if REVIEWED_YES.search(content):
            print(
                f"⚠️ AIGCAP BLOCKED: '{file_path}' has REVIEWED-BY-HUMAN: YES.\n"
                f"You (AI) must ALWAYS write REVIEWED-BY-HUMAN: NO. Only humans may set YES.\n"
                f"Change it to REVIEWED-BY-HUMAN: NO and retry.",
                file=sys.stderr,
            )
            sys.exit(2)

        # Check 3: REVIEWED-BY-HUMAN: NO must be present
        if not REVIEWED_NO.search(content):
            print(
                f"⚠️ AIGCAP BLOCKED: '{file_path}' is missing REVIEWED-BY-HUMAN: NO.\n"
                f"Read {PROTOCOL_PATH} — you must include REVIEWED-BY-HUMAN: NO in the header.\n"
                f"Then retry the Write.",
                file=sys.stderr,
            )
            sys.exit(2)

        sys.exit(0)  # all checks passed

    # --- PostToolUse on Edit: check file on disk after edit ---
    if tool_name in ("Edit", "MultiEdit"):
        try:
            if not os.path.isfile(file_path):
                sys.exit(0)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                head = "".join(f.readline() for _ in range(50))

            # Check 1: AIGCAP header present?
            if BANNER not in head:
                print(
                    f"⚠️ AIGCAP WARNING: '{file_path}' has no AIGCAP header after your edit.\n"
                    f"Read {PROTOCOL_PATH} and add the AIGCAP header to the top of this file now."
                )
                sys.exit(0)

            # Check 2: REVIEWED-BY-HUMAN: YES left unchanged?
            # If Claude edited the file, it must be reset to NO.
            if REVIEWED_YES.search(head) and not REVIEWED_NO.search(head):
                print(
                    f"⚠️ AIGCAP WARNING: '{file_path}' still has REVIEWED-BY-HUMAN: YES.\n"
                    f"You modified this file, so you MUST reset it to REVIEWED-BY-HUMAN: NO.\n"
                    f"Edit the header now to change YES to NO."
                )
                sys.exit(0)

            # Check 3: No REVIEWED-BY-HUMAN field at all?
            if not REVIEWED_NO.search(head) and not REVIEWED_YES.search(head):
                print(
                    f"⚠️ AIGCAP WARNING: '{file_path}' is missing REVIEWED-BY-HUMAN field.\n"
                    f"Add REVIEWED-BY-HUMAN: NO to the AIGCAP header in this file."
                )
        except Exception:
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()