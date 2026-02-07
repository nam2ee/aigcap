#!/usr/bin/env python3
"""
AIGCAP Parser — AI-Generated Code Annotation Protocol Parser & Dashboard Generator
Scans source files for AIGCAP headers and generates an HTML coverage dashboard.

Usage:
    python ai_coverage.py [OPTIONS] [DIRECTORY]

Examples:
    python ai_coverage.py .                          # Scan current directory
    python ai_coverage.py ./src --output report.html  # Custom output
    python ai_coverage.py ./src --exclude vendor,dist  # Exclude directories
    python ai_coverage.py ./src --json coverage.json   # Also export JSON
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── Language Detection ─────────────────────────────────────────────────────

LANG_MAP: dict[str, dict] = {
    # Block comment languages: /* ... */
    ".rs":    {"name": "Rust",       "family": "block", "prefix": " *"},
    ".c":     {"name": "C",          "family": "block", "prefix": " *"},
    ".h":     {"name": "C Header",   "family": "block", "prefix": " *"},
    ".cpp":   {"name": "C++",        "family": "block", "prefix": " *"},
    ".hpp":   {"name": "C++ Header", "family": "block", "prefix": " *"},
    ".java":  {"name": "Java",       "family": "block", "prefix": " *"},
    ".js":    {"name": "JavaScript", "family": "block", "prefix": " *"},
    ".jsx":   {"name": "JSX",        "family": "block", "prefix": " *"},
    ".ts":    {"name": "TypeScript", "family": "block", "prefix": " *"},
    ".tsx":   {"name": "TSX",        "family": "block", "prefix": " *"},
    ".go":    {"name": "Go",         "family": "block", "prefix": " *"},
    ".swift": {"name": "Swift",      "family": "block", "prefix": " *"},
    ".kt":    {"name": "Kotlin",     "family": "block", "prefix": " *"},
    ".scala": {"name": "Scala",      "family": "block", "prefix": " *"},
    ".cs":    {"name": "C#",         "family": "block", "prefix": " *"},
    ".css":   {"name": "CSS",        "family": "block", "prefix": " *"},
    ".scss":  {"name": "SCSS",       "family": "block", "prefix": " *"},
    # Hash comment languages: #
    ".py":    {"name": "Python",     "family": "hash",  "prefix": "#"},
    ".rb":    {"name": "Ruby",       "family": "hash",  "prefix": "#"},
    ".sh":    {"name": "Shell",      "family": "hash",  "prefix": "#"},
    ".bash":  {"name": "Bash",       "family": "hash",  "prefix": "#"},
    ".yaml":  {"name": "YAML",       "family": "hash",  "prefix": "#"},
    ".yml":   {"name": "YAML",       "family": "hash",  "prefix": "#"},
    ".toml":  {"name": "TOML",       "family": "hash",  "prefix": "#"},
    ".r":     {"name": "R",          "family": "hash",  "prefix": "#"},
    # Dash comment languages: --
    ".sql":   {"name": "SQL",        "family": "dash",  "prefix": "--"},
    ".lua":   {"name": "Lua",        "family": "dash",  "prefix": "--"},
    ".hs":    {"name": "Haskell",    "family": "dash",  "prefix": "--"},
    # HTML-style: <!-- -->
    ".html":  {"name": "HTML",       "family": "html",  "prefix": ""},
    ".xml":   {"name": "XML",        "family": "html",  "prefix": ""},
    ".svg":   {"name": "SVG",        "family": "html",  "prefix": ""},
    ".vue":   {"name": "Vue",        "family": "html",  "prefix": ""},
}

DEFAULT_EXCLUDE = {
    "node_modules", ".git", ".svn", "__pycache__", ".mypy_cache",
    ".pytest_cache", "target", "build", "dist", ".next", ".nuxt",
    "vendor", ".venv", "venv", "env", ".env", ".idea", ".vscode",
    "coverage", ".coverage", "htmlcov",
}

BANNER = "THIS FILE INCLUDES AI GENERATED CODE"


# ─── Data Models ────────────────────────────────────────────────────────────

@dataclass
class MethodEntry:
    name: str
    coverage: str          # "WHOLE" or "PARTIAL"
    start_line: Optional[int] = None
    end_line: Optional[int] = None

@dataclass
class StructEntry:
    name: str
    coverage: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None

@dataclass
class TraitEntry:
    name: str
    coverage: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None

@dataclass
class LibraryEntry:
    name: str
    reason: str

@dataclass
class FileReport:
    path: str
    language: str
    type_coverage: str          # "WHOLE", "ABOVE_50", "DOWN_50"
    methods: list[MethodEntry] = field(default_factory=list)
    structs: list[StructEntry] = field(default_factory=list)
    traits: list[TraitEntry] = field(default_factory=list)
    libraries: list[LibraryEntry] = field(default_factory=list)
    total_lines: int = 0
    ai_lines_estimate: int = 0

@dataclass
class ProjectReport:
    scan_directory: str
    scan_time: str
    total_files_scanned: int = 0
    total_files_with_aigcap: int = 0
    total_files_without_aigcap: int = 0
    files: list[FileReport] = field(default_factory=list)
    files_without_header: list[str] = field(default_factory=list)
    language_breakdown: dict = field(default_factory=dict)


# ─── Parser ─────────────────────────────────────────────────────────────────

# Regex patterns for parsing entries
RE_METHOD_WHOLE = re.compile(
    r"WHOLE\s+CODE\s+IN\s+THE\s+METHOD\s+[`'\"]?(\w+)[`'\"]?", re.IGNORECASE
)
RE_METHOD_PARTIAL = re.compile(
    r"(\d+)\s*~\s*(\d+)\s+LINE\s+CODE\s+IN\s+THE\s+METHOD\s+[`'\"]?(\w+)[`'\"]?", re.IGNORECASE
)
RE_STRUCT_WHOLE = re.compile(
    r"WHOLE\s+CODE\s+IN\s+THE\s+STRUCT\s+[`'\"]?(\w+)[`'\"]?", re.IGNORECASE
)
RE_STRUCT_PARTIAL = re.compile(
    r"(\d+)\s*~\s*(\d+)\s+LINE\s+CODE\s+IN\s+THE\s+STRUCT\s+[`'\"]?(\w+)[`'\"]?", re.IGNORECASE
)
RE_TRAIT_WHOLE = re.compile(
    r"WHOLE\s+CODE\s+IN\s+THE\s+TRAIT\s+[`'\"]?(\w+)[`'\"]?", re.IGNORECASE
)
RE_TRAIT_PARTIAL = re.compile(
    r"(\d+)\s*~\s*(\d+)\s+LINE\s+CODE\s+IN\s+THE\s+TRAIT\s+[`'\"]?(\w+)[`'\"]?", re.IGNORECASE
)
RE_LIBRARY = re.compile(
    r"-\s*(\S+?):\s*(.+)", re.IGNORECASE
)
RE_TYPE = re.compile(
    r"TYPE:\s*(WHOLE\s+CODE\s+IN\s+THIS\s+FILE|ABOVE\s+50%?\s+IN\s+THIS\s+FILE|DOWN\s+50%?\s+IN\s+THIS\s+FILE)",
    re.IGNORECASE,
)


def strip_comment_prefix(line: str, lang_info: dict) -> str:
    """Remove comment prefix characters from a line."""
    stripped = line.strip()
    family = lang_info["family"]

    if family == "block":
        # Remove leading /*, */, *
        stripped = re.sub(r"^/\*+\s?", "", stripped)
        stripped = re.sub(r"\*+/$", "", stripped)
        stripped = re.sub(r"^\*+\s?", "", stripped)
    elif family == "hash":
        stripped = re.sub(r"^#+\s?", "", stripped)
    elif family == "dash":
        stripped = re.sub(r"^--+\s?", "", stripped)
    elif family == "html":
        stripped = re.sub(r"^<!--\s?", "", stripped)
        stripped = re.sub(r"\s?-->$", "", stripped)

    return stripped.strip()


def extract_header_block(content: str, lang_info: dict) -> Optional[str]:
    """Extract the AIGCAP header block from file content."""
    if BANNER not in content:
        return None

    lines = content.split("\n")
    header_lines = []
    in_header = False
    banner_count = 0

    for line in lines:
        cleaned = strip_comment_prefix(line, lang_info)

        if "========" in cleaned and not in_header:
            in_header = True
            continue

        if BANNER in cleaned:
            banner_count += 1
            continue

        if in_header:
            if "========" in cleaned:
                # Check if this is a closing separator
                # A closing separator comes after we've seen content
                if header_lines:
                    break
                continue

            header_lines.append(cleaned)

    return "\n".join(header_lines) if header_lines else None


def parse_header(header_text: str) -> dict:
    """Parse the extracted header text into structured data."""
    result = {
        "type": None,
        "methods": [],
        "structs": [],
        "traits": [],
        "libraries": [],
    }

    # Parse TYPE
    type_match = RE_TYPE.search(header_text)
    if type_match:
        raw = type_match.group(1).upper().strip()
        if "WHOLE" in raw:
            result["type"] = "WHOLE"
        elif "ABOVE" in raw:
            result["type"] = "ABOVE_50"
        elif "DOWN" in raw:
            result["type"] = "DOWN_50"

    current_section = None
    for line in header_text.split("\n"):
        line = line.strip()

        # Detect section headers
        if line.startswith("METHOD") or line.startswith("FUNCTION"):
            current_section = "methods"
            continue
        elif line.startswith("STRUCT") or line.startswith("OBJECT"):
            current_section = "structs"
            continue
        elif line.startswith("TRAIT") or line.startswith("INTERFACE"):
            current_section = "traits"
            continue
        elif line.startswith("IMPORTED"):
            current_section = "libraries"
            continue

        if not line.startswith("-"):
            continue

        entry_text = line.lstrip("- ").strip()

        if current_section == "methods":
            m = RE_METHOD_WHOLE.search(entry_text)
            if m:
                result["methods"].append(MethodEntry(name=m.group(1), coverage="WHOLE"))
                continue
            m = RE_METHOD_PARTIAL.search(entry_text)
            if m:
                result["methods"].append(MethodEntry(
                    name=m.group(3), coverage="PARTIAL",
                    start_line=int(m.group(1)), end_line=int(m.group(2))
                ))

        elif current_section == "structs":
            m = RE_STRUCT_WHOLE.search(entry_text)
            if m:
                result["structs"].append(StructEntry(name=m.group(1), coverage="WHOLE"))
                continue
            m = RE_STRUCT_PARTIAL.search(entry_text)
            if m:
                result["structs"].append(StructEntry(
                    name=m.group(3), coverage="PARTIAL",
                    start_line=int(m.group(1)), end_line=int(m.group(2))
                ))

        elif current_section == "traits":
            m = RE_TRAIT_WHOLE.search(entry_text)
            if m:
                result["traits"].append(TraitEntry(name=m.group(1), coverage="WHOLE"))
                continue
            m = RE_TRAIT_PARTIAL.search(entry_text)
            if m:
                result["traits"].append(TraitEntry(
                    name=m.group(3), coverage="PARTIAL",
                    start_line=int(m.group(1)), end_line=int(m.group(2))
                ))

        elif current_section == "libraries":
            m = RE_LIBRARY.search(line)
            if m:
                result["libraries"].append(LibraryEntry(
                    name=m.group(1), reason=m.group(2).strip()
                ))

    return result


def count_lines(filepath: str) -> int:
    """Count non-empty, non-comment lines in a file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return len([l for l in lines if l.strip()])
    except Exception:
        return 0


def estimate_ai_lines(total_lines: int, type_coverage: str, methods: list, structs: list, traits: list) -> int:
    """Estimate AI-generated lines based on TYPE and entries."""
    if type_coverage == "WHOLE":
        return total_lines
    elif type_coverage == "ABOVE_50":
        # Use 75% as default estimate, refine with partial entries
        base = int(total_lines * 0.75)
    elif type_coverage == "DOWN_50":
        base = int(total_lines * 0.25)
    else:
        return 0

    # If we have partial line ranges, calculate more precisely
    partial_lines = 0
    whole_items = 0
    for items in [methods, structs, traits]:
        for item in items:
            if item.coverage == "PARTIAL" and item.start_line and item.end_line:
                partial_lines += (item.end_line - item.start_line + 1)
            elif item.coverage == "WHOLE":
                whole_items += 1

    if partial_lines > 0:
        return min(partial_lines + (whole_items * 20), total_lines)  # rough estimate

    return base


# ─── Scanner ────────────────────────────────────────────────────────────────

def scan_directory(directory: str, exclude_dirs: set[str]) -> ProjectReport:
    """Scan directory tree and parse all AIGCAP headers."""
    report = ProjectReport(
        scan_directory=os.path.abspath(directory),
        scan_time=datetime.now().isoformat(),
    )

    for root, dirs, files in os.walk(directory):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for filename in files:
            filepath = os.path.join(root, filename)
            ext = Path(filename).suffix.lower()

            if ext not in LANG_MAP:
                continue

            report.total_files_scanned += 1
            lang_info = LANG_MAP[ext]
            rel_path = os.path.relpath(filepath, directory)

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            header_block = extract_header_block(content, lang_info)

            if header_block is None:
                report.total_files_without_aigcap += 1
                report.files_without_header.append(rel_path)
                # Track language even for non-AIGCAP files
                lang_name = lang_info["name"]
                if lang_name not in report.language_breakdown:
                    report.language_breakdown[lang_name] = {"total": 0, "ai": 0, "ai_lines": 0, "total_lines": 0}
                report.language_breakdown[lang_name]["total"] += 1
                report.language_breakdown[lang_name]["total_lines"] += count_lines(filepath)
                continue

            report.total_files_with_aigcap += 1
            parsed = parse_header(header_block)
            total_lines = count_lines(filepath)
            ai_lines = estimate_ai_lines(
                total_lines,
                parsed["type"] or "DOWN_50",
                parsed["methods"], parsed["structs"], parsed["traits"]
            )

            file_report = FileReport(
                path=rel_path,
                language=lang_info["name"],
                type_coverage=parsed["type"] or "UNKNOWN",
                methods=parsed["methods"],
                structs=parsed["structs"],
                traits=parsed["traits"],
                libraries=parsed["libraries"],
                total_lines=total_lines,
                ai_lines_estimate=ai_lines,
            )
            report.files.append(file_report)

            # Language breakdown
            lang_name = lang_info["name"]
            if lang_name not in report.language_breakdown:
                report.language_breakdown[lang_name] = {"total": 0, "ai": 0, "ai_lines": 0, "total_lines": 0}
            report.language_breakdown[lang_name]["total"] += 1
            report.language_breakdown[lang_name]["ai"] += 1
            report.language_breakdown[lang_name]["ai_lines"] += ai_lines
            report.language_breakdown[lang_name]["total_lines"] += total_lines

    return report


# ─── HTML Dashboard Generator ──────────────────────────────────────────────

def generate_html(report: ProjectReport) -> str:
    """Generate a complete HTML dashboard from the report."""

    # Calculate summary stats
    total_ai_lines = sum(f.ai_lines_estimate for f in report.files)
    total_all_lines = sum(
        v["total_lines"] for v in report.language_breakdown.values()
    )
    overall_pct = (total_ai_lines / total_all_lines * 100) if total_all_lines > 0 else 0

    whole_files = sum(1 for f in report.files if f.type_coverage == "WHOLE")
    above50_files = sum(1 for f in report.files if f.type_coverage == "ABOVE_50")
    down50_files = sum(1 for f in report.files if f.type_coverage == "DOWN_50")

    all_methods = []
    all_structs = []
    all_traits = []
    all_libraries: dict[str, set] = {}

    for f in report.files:
        for m in f.methods:
            all_methods.append({"file": f.path, **_entry_dict(m)})
        for s in f.structs:
            all_structs.append({"file": f.path, **_entry_dict(s)})
        for t in f.traits:
            all_traits.append({"file": f.path, **_entry_dict(t)})
        for lib in f.libraries:
            if lib.name not in all_libraries:
                all_libraries[lib.name] = set()
            all_libraries[lib.name].add(lib.reason)

    # Language chart data
    lang_labels = json.dumps(list(report.language_breakdown.keys()))
    lang_ai_lines = json.dumps([v["ai_lines"] for v in report.language_breakdown.values()])
    lang_total_lines = json.dumps([v["total_lines"] for v in report.language_breakdown.values()])
    lang_ai_files = json.dumps([v["ai"] for v in report.language_breakdown.values()])
    lang_total_files = json.dumps([v["total"] for v in report.language_breakdown.values()])

    # File table rows
    file_rows = ""
    for f in sorted(report.files, key=lambda x: x.ai_lines_estimate, reverse=True):
        pct = (f.ai_lines_estimate / f.total_lines * 100) if f.total_lines > 0 else 0
        type_badge = _type_badge(f.type_coverage)
        methods_str = ", ".join(
            f'<span class="tag tag-method" title="{_coverage_label(m)}">{m.name}</span>'
            for m in f.methods
        ) or '<span class="tag tag-none">—</span>'
        structs_str = ", ".join(
            f'<span class="tag tag-struct" title="{_coverage_label(s)}">{s.name}</span>'
            for s in f.structs
        ) or '<span class="tag tag-none">—</span>'
        traits_str = ", ".join(
            f'<span class="tag tag-trait" title="{_coverage_label(t)}">{t.name}</span>'
            for t in f.traits
        ) or '<span class="tag tag-none">—</span>'
        libs_str = ", ".join(
            f'<span class="tag tag-lib">{lib.name}</span>'
            for lib in f.libraries
        ) or '<span class="tag tag-none">—</span>'

        file_rows += f"""
        <tr>
          <td class="file-path" title="{f.path}">{f.path}</td>
          <td>{f.language}</td>
          <td>{type_badge}</td>
          <td class="num">{f.total_lines}</td>
          <td class="num">{f.ai_lines_estimate}</td>
          <td>
            <div class="bar-container">
              <div class="bar-fill" style="width:{pct:.1f}%"></div>
              <span class="bar-label">{pct:.1f}%</span>
            </div>
          </td>
          <td>{methods_str}</td>
          <td>{structs_str}</td>
          <td>{traits_str}</td>
          <td>{libs_str}</td>
        </tr>"""

    # Library summary rows
    lib_rows = ""
    for name, reasons in sorted(all_libraries.items()):
        files_using = [f.path for f in report.files if any(l.name == name for l in f.libraries)]
        lib_rows += f"""
        <tr>
          <td><strong>{name}</strong></td>
          <td>{"; ".join(reasons)}</td>
          <td>{len(files_using)}</td>
          <td>{", ".join(files_using[:5])}{"..." if len(files_using) > 5 else ""}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AIGCAP Coverage Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');

  :root {{
    --bg-primary: #0a0a0f;
    --bg-secondary: #12121a;
    --bg-card: #1a1a27;
    --bg-card-hover: #222235;
    --border: #2a2a40;
    --text-primary: #e8e8f0;
    --text-secondary: #8888a8;
    --text-muted: #555570;
    --accent-blue: #4d8eff;
    --accent-green: #34d399;
    --accent-amber: #fbbf24;
    --accent-red: #f87171;
    --accent-purple: #a78bfa;
    --accent-cyan: #22d3ee;
    --whole: #f87171;
    --above50: #fbbf24;
    --down50: #34d399;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
  }}

  .dashboard {{
    max-width: 1600px;
    margin: 0 auto;
    padding: 32px 24px;
  }}

  /* Header */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 40px;
    padding-bottom: 24px;
    border-bottom: 1px solid var(--border);
  }}
  .header h1 {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
  }}
  .header .meta {{
    text-align: right;
    color: var(--text-secondary);
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
  }}

  /* Stat Cards */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }}
  .stat-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    transition: background 0.2s;
  }}
  .stat-card:hover {{ background: var(--bg-card-hover); }}
  .stat-card .label {{
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }}
  .stat-card .value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 32px;
    font-weight: 700;
  }}
  .stat-card .sub {{
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 4px;
  }}
  .color-blue .value {{ color: var(--accent-blue); }}
  .color-green .value {{ color: var(--accent-green); }}
  .color-amber .value {{ color: var(--accent-amber); }}
  .color-red .value {{ color: var(--accent-red); }}
  .color-purple .value {{ color: var(--accent-purple); }}
  .color-cyan .value {{ color: var(--accent-cyan); }}

  /* Big coverage gauge */
  .gauge-section {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 32px;
    text-align: center;
  }}
  .gauge-section h2 {{
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-secondary);
    margin-bottom: 20px;
  }}
  .gauge-big {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 72px;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent-red), var(--accent-amber));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .gauge-bar {{
    height: 12px;
    background: var(--bg-secondary);
    border-radius: 6px;
    margin: 20px auto 0;
    max-width: 600px;
    overflow: hidden;
  }}
  .gauge-bar-fill {{
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, var(--accent-green), var(--accent-amber), var(--accent-red));
    transition: width 1s ease;
  }}

  /* Charts Section */
  .charts-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 32px;
  }}
  .chart-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
  }}
  .chart-card h3 {{
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary);
    margin-bottom: 16px;
  }}

  /* Section titles */
  .section-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 32px 0 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}

  /* Table */
  .table-container {{
    overflow-x: auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 32px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  th {{
    text-align: left;
    padding: 12px 14px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    white-space: nowrap;
  }}
  td {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: var(--bg-card-hover); }}

  .file-path {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .num {{
    font-family: 'JetBrains Mono', monospace;
    text-align: right;
  }}

  /* Tags */
  .tag {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    margin: 1px 2px;
  }}
  .tag-method {{ background: rgba(77, 142, 255, 0.15); color: var(--accent-blue); }}
  .tag-struct {{ background: rgba(167, 139, 250, 0.15); color: var(--accent-purple); }}
  .tag-trait  {{ background: rgba(34, 211, 238, 0.15); color: var(--accent-cyan); }}
  .tag-lib    {{ background: rgba(251, 191, 36, 0.15); color: var(--accent-amber); }}
  .tag-none   {{ color: var(--text-muted); }}

  /* Type badges */
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    white-space: nowrap;
  }}
  .badge-whole  {{ background: rgba(248, 113, 113, 0.15); color: var(--whole); }}
  .badge-above  {{ background: rgba(251, 191, 36, 0.15); color: var(--above50); }}
  .badge-down   {{ background: rgba(52, 211, 153, 0.15); color: var(--down50); }}

  /* Progress bar */
  .bar-container {{
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 120px;
  }}
  .bar-fill {{
    height: 6px;
    background: linear-gradient(90deg, var(--accent-green), var(--accent-amber));
    border-radius: 3px;
    flex-shrink: 0;
  }}
  .bar-container {{
    position: relative;
    height: 22px;
    background: rgba(255,255,255,0.05);
    border-radius: 4px;
    overflow: hidden;
  }}
  .bar-fill {{
    position: absolute;
    top: 0; left: 0; bottom: 0;
    background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
    border-radius: 4px;
  }}
  .bar-label {{
    position: relative;
    z-index: 1;
    padding: 0 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    line-height: 22px;
    color: var(--text-primary);
  }}

  /* Footer */
  .footer {{
    text-align: center;
    padding: 24px;
    color: var(--text-muted);
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
  }}

  /* Responsive */
  @media (max-width: 900px) {{
    .charts-grid {{ grid-template-columns: 1fr; }}
    .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .gauge-big {{ font-size: 48px; }}
  }}
</style>
</head>
<body>
<div class="dashboard">

  <div class="header">
    <div>
      <h1>⚡ AIGCAP Coverage Dashboard</h1>
      <p style="color:var(--text-secondary); font-size:14px; margin-top:4px;">
        AI-Generated Code Annotation Protocol — Coverage Report
      </p>
    </div>
    <div class="meta">
      <div>📁 {report.scan_directory}</div>
      <div>🕐 {report.scan_time[:19]}</div>
    </div>
  </div>

  <!-- Big Gauge -->
  <div class="gauge-section">
    <h2>Overall AI Code Coverage</h2>
    <div class="gauge-big">{overall_pct:.1f}%</div>
    <div class="gauge-bar">
      <div class="gauge-bar-fill" style="width:{min(overall_pct, 100):.1f}%"></div>
    </div>
    <p style="color:var(--text-secondary); margin-top:12px; font-size:14px;">
      {total_ai_lines:,} AI-generated lines / {total_all_lines:,} total lines across {report.total_files_scanned} files
    </p>
  </div>

  <!-- Stat Cards -->
  <div class="stats-grid">
    <div class="stat-card color-blue">
      <div class="label">Total Files Scanned</div>
      <div class="value">{report.total_files_scanned}</div>
    </div>
    <div class="stat-card color-red">
      <div class="label">Files with AI Code</div>
      <div class="value">{report.total_files_with_aigcap}</div>
      <div class="sub">{(report.total_files_with_aigcap / report.total_files_scanned * 100) if report.total_files_scanned > 0 else 0:.1f}% of all files</div>
    </div>
    <div class="stat-card color-green">
      <div class="label">Human-Only Files</div>
      <div class="value">{report.total_files_without_aigcap}</div>
    </div>
    <div class="stat-card color-amber">
      <div class="label">100% AI Files</div>
      <div class="value">{whole_files}</div>
    </div>
    <div class="stat-card color-purple">
      <div class="label">&gt;50% AI Files</div>
      <div class="value">{above50_files}</div>
    </div>
    <div class="stat-card color-cyan">
      <div class="label">&lt;50% AI Files</div>
      <div class="value">{down50_files}</div>
    </div>
  </div>

  <!-- Charts -->
  <div class="charts-grid">
    <div class="chart-card">
      <h3>AI Lines by Language</h3>
      <canvas id="langLinesChart"></canvas>
    </div>
    <div class="chart-card">
      <h3>AI Files by Language</h3>
      <canvas id="langFilesChart"></canvas>
    </div>
  </div>

  <!-- Detailed File Table -->
  <h2 class="section-title">📋 File-Level Detail</h2>
  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th>File</th>
          <th>Lang</th>
          <th>Type</th>
          <th>Total Lines</th>
          <th>AI Lines</th>
          <th style="min-width:130px">Coverage</th>
          <th>Methods</th>
          <th>Structs</th>
          <th>Traits</th>
          <th>Libraries</th>
        </tr>
      </thead>
      <tbody>
        {file_rows if file_rows else '<tr><td colspan="10" style="text-align:center;padding:24px;color:var(--text-muted);">No AIGCAP headers found</td></tr>'}
      </tbody>
    </table>
  </div>

  <!-- Library Summary -->
  {"" if not lib_rows else f'''
  <h2 class="section-title">📦 AI-Selected Libraries</h2>
  <div class="table-container">
    <table>
      <thead>
        <tr><th>Library</th><th>Reason</th><th>Files Using</th><th>Locations</th></tr>
      </thead>
      <tbody>{lib_rows}</tbody>
    </table>
  </div>
  '''}

  <!-- Files Without Header -->
  {"" if not report.files_without_header else f'''
  <h2 class="section-title">🔍 Files Without AIGCAP Header ({len(report.files_without_header)})</h2>
  <div class="table-container" style="max-height:300px; overflow-y:auto;">
    <table>
      <thead><tr><th>File Path</th></tr></thead>
      <tbody>
        {"".join(f'<tr><td class="file-path">{p}</td></tr>' for p in sorted(report.files_without_header)[:100])}
        {"<tr><td style='color:var(--text-muted)'>... and " + str(len(report.files_without_header) - 100) + " more</td></tr>" if len(report.files_without_header) > 100 else ""}
      </tbody>
    </table>
  </div>
  '''}

  <div class="footer">
    AIGCAP v1.0 — AI-Generated Code Annotation Protocol — Report generated by ai_coverage.py
  </div>

</div>

<script>
const colors = ['#4d8eff','#a78bfa','#22d3ee','#34d399','#fbbf24','#f87171','#fb923c','#e879f9','#6ee7b7','#fca5a5'];

// Language Lines Chart
new Chart(document.getElementById('langLinesChart'), {{
  type: 'bar',
  data: {{
    labels: {lang_labels},
    datasets: [
      {{
        label: 'AI Lines',
        data: {lang_ai_lines},
        backgroundColor: 'rgba(77, 142, 255, 0.7)',
        borderColor: '#4d8eff',
        borderWidth: 1,
        borderRadius: 4,
      }},
      {{
        label: 'Total Lines',
        data: {lang_total_lines},
        backgroundColor: 'rgba(255, 255, 255, 0.08)',
        borderColor: 'rgba(255,255,255,0.15)',
        borderWidth: 1,
        borderRadius: 4,
      }}
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ labels: {{ color: '#8888a8', font: {{ family: 'JetBrains Mono' }} }} }}
    }},
    scales: {{
      x: {{ ticks: {{ color: '#8888a8', font: {{ family: 'JetBrains Mono', size: 11 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
      y: {{ ticks: {{ color: '#8888a8', font: {{ family: 'JetBrains Mono', size: 11 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
    }}
  }}
}});

// Language Files Chart
new Chart(document.getElementById('langFilesChart'), {{
  type: 'doughnut',
  data: {{
    labels: {lang_labels},
    datasets: [{{
      data: {lang_ai_files},
      backgroundColor: colors.slice(0, {len(report.language_breakdown)}),
      borderWidth: 0,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position: 'right', labels: {{ color: '#8888a8', font: {{ family: 'JetBrains Mono', size: 11 }}, padding: 12 }} }}
    }}
  }}
}});
</script>
</body>
</html>"""
    return html


def _type_badge(coverage: str) -> str:
    if coverage == "WHOLE":
        return '<span class="badge badge-whole">WHOLE</span>'
    elif coverage == "ABOVE_50":
        return '<span class="badge badge-above">&gt;50%</span>'
    elif coverage == "DOWN_50":
        return '<span class="badge badge-down">&lt;50%</span>'
    return f'<span class="badge">{coverage}</span>'


def _coverage_label(entry) -> str:
    if entry.coverage == "WHOLE":
        return "AI wrote entire code"
    return f"AI wrote lines {entry.start_line}~{entry.end_line}"


def _entry_dict(entry) -> dict:
    return {
        "name": entry.name,
        "coverage": entry.coverage,
        "start_line": getattr(entry, "start_line", None),
        "end_line": getattr(entry, "end_line", None),
    }


# ─── JSON Export ────────────────────────────────────────────────────────────

def export_json(report: ProjectReport) -> str:
    """Export report as JSON."""
    def serialize(obj):
        if hasattr(obj, "__dict__"):
            d = {}
            for k, v in obj.__dict__.items():
                d[k] = serialize(v)
            return d
        elif isinstance(obj, list):
            return [serialize(i) for i in obj]
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        return obj
    return json.dumps(serialize(report), indent=2, ensure_ascii=False)


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AIGCAP Parser — Scan for AI-Generated Code Annotations and generate coverage reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s .                              Scan current directory
  %(prog)s ./src -o dashboard.html        Custom output path
  %(prog)s . --exclude vendor,dist,test   Exclude specific dirs
  %(prog)s . --json coverage.json         Also export JSON data
        """,
    )
    parser.add_argument("directory", nargs="?", default=".", help="Directory to scan (default: current)")
    parser.add_argument("-o", "--output", default="ai_coverage_report.html", help="HTML output path (default: ai_coverage_report.html)")
    parser.add_argument("--json", dest="json_path", help="Also export raw data as JSON")
    parser.add_argument("--exclude", default="", help="Comma-separated additional dirs to exclude")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open the report")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress console output")
    args = parser.parse_args()

    exclude = DEFAULT_EXCLUDE.copy()
    if args.exclude:
        exclude.update(d.strip() for d in args.exclude.split(",") if d.strip())

    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"🔍 Scanning {os.path.abspath(args.directory)} ...")

    report = scan_directory(args.directory, exclude)

    # Generate HTML
    html = generate_html(report)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    if not args.quiet:
        total_ai_lines = sum(f.ai_lines_estimate for f in report.files)
        total_all_lines = sum(v["total_lines"] for v in report.language_breakdown.values())
        pct = (total_ai_lines / total_all_lines * 100) if total_all_lines > 0 else 0
        print(f"\n📊 Results:")
        print(f"   Files scanned:     {report.total_files_scanned}")
        print(f"   Files with AIGCAP: {report.total_files_with_aigcap}")
        print(f"   AI coverage:       {pct:.1f}% ({total_ai_lines:,} / {total_all_lines:,} lines)")
        print(f"\n✅ Dashboard saved to: {args.output}")

    # JSON export
    if args.json_path:
        json_data = export_json(report)
        with open(args.json_path, "w", encoding="utf-8") as f:
            f.write(json_data)
        if not args.quiet:
            print(f"📄 JSON exported to:  {args.json_path}")

    # Auto-open
    if not args.no_open:
        import webbrowser
        try:
            webbrowser.open(f"file://{os.path.abspath(args.output)}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
