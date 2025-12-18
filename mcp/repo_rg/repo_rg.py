from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Annotated, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("repo-rg")

class SearchArgs(BaseModel):
    query: Annotated[str, Field(description="The search query (regex or keywords)")]
    root: Annotated[Optional[str], Field(description="Root path to search (default: repository root)")] = None
    max_results: Annotated[int, Field(description="Maximum number of results", default=20)] = 20
    hidden: Annotated[bool, Field(description="Search hidden files/directories", default=False)] = False
    ignored: Annotated[bool, Field(description="Search ignored files (respect .gitignore by default)", default=False)] = False

def run_command(argv: list[str], cwd: str, stdin_text: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=cwd,
        input=stdin_text,
        text=True,
        capture_output=True,
        encoding="utf-8", 
        errors="replace"
    )

def _rg_available() -> bool:
    return shutil.which("rg") is not None

@mcp.tool()
def search(args: SearchArgs) -> str:
    """Code-oriented repo search using ripgrep (rg).
    
    Cascades through strategies:
    1. Regex (primary, code-style)
    2. Literal substring (fallback)
    3. Multi-term AND (all words must appear)
    """
    
    if not _rg_available():
        return "### Notes\n- `rg` is missing. Please install ripgrep (e.g. `choco install ripgrep` or `winget install BurntSushi.ripgrep.MSVC`)."

    if args.root:
        root = args.root
    else:
        # Default to repo root (assuming we are in mcp/repo_rg/repo_rg.py)
        # Go up two levels from this file: mcp/repo_rg/repo_rg.py -> mcp/repo_rg -> mcp -> repo_root
        current_file = os.path.abspath(__file__)
        root = os.path.abspath(os.path.join(os.path.dirname(current_file), "..", ".."))

    if not os.path.exists(root):
         return f"Error: Root path '{root}' does not exist."
    if not os.path.isdir(root):
         return f"Error: Root path '{root}' is not a directory."

    query = args.query
    max_results = args.max_results
    hidden = args.hidden
    ignored = args.ignored

    base_flags = [
        "--no-heading",
        "--color=never",
        "--line-number",
        "--column",
        "--smart-case",
    ]
    if ignored:
        base_flags.append("--no-ignore")
    if hidden:
        base_flags.append("--hidden")

    # Strategies
    strategies = []
    
    # A: regex
    strategies.append(("regex", [], query))
    
    # B: literal
    strategies.append(("literal", ["--fixed-strings"], query))
    
    # C: multi-term AND
    terms = [t for t in query.split() if t.strip()]
    if len(terms) >= 2:
        # PCRE2 lookahead for AND: (?=.*t1)(?=.*t2).*
        # We must escape terms if we treat them as literals inside the regex
        lookahead = "".join(f"(?=.*{re.escape(t)})" for t in terms) + ".*"
        strategies.append(("multi-term-AND", ["-P"], lookahead))

    chosen = "none"
    chosen_flags = []
    chosen_pattern = None
    line_matches = []
    notes = []

    # Execute line search strategies
    for name, flags, pattern in strategies:
        argv = ["rg"] + base_flags + flags + [pattern, root]
        
        p = run_command(argv, cwd=root)
        
        if p.returncode == 2:
            if name == "regex":
                continue
            notes.append(f"ripgrep error in strategy {name}: {p.stderr.strip()}")
            continue
            
        if p.returncode == 0 and p.stdout.strip():
            chosen = name
            chosen_flags = flags
            chosen_pattern = pattern
            line_matches = p.stdout.splitlines()
            break
    
    truncated = False
    if len(line_matches) > max_results:
        line_matches = line_matches[:max_results]
        truncated = True

    # Parse lines: path:line:col:text
    by_file = {}
    
    # Regex for parsing rg output: path:line:col:content
    # Handles Windows drive letters by ensuring line/col are digits surrounded by colons.
    line_pattern = re.compile(r"^(.*?):(\d+):(\d+):(.*)$")

    for line in line_matches:
        match = line_pattern.match(line)
        if not match:
            continue
        path, ln, col, text = match.groups()
        try:
            ln_i = int(ln)
            col_i = int(col)
        except ValueError:
            continue
            
        by_file.setdefault(path, []).append((ln_i, col_i, text.strip()))

    # Files with content matches (best matches)
    content_files = []
    if chosen != "none":
        files_argv = ["rg", "--smart-case", "-l"]
        if ignored:
            files_argv.append("--no-ignore")
        if hidden:
            files_argv.append("--hidden")
        
        files_argv += chosen_flags + [chosen_pattern, root]
        p_files = run_command(files_argv, cwd=root)
        if p_files.returncode == 0 and p_files.stdout.strip():
            content_files = p_files.stdout.splitlines()[:max_results]

    # Filenames/paths matching query (secondary)
    name_files = []
    # rg --files
    files_list_argv = ["rg", "--files", root]
    if ignored:
        files_list_argv.append("--no-ignore")
    if hidden:
        files_list_argv.append("--hidden")

    p_list = run_command(files_list_argv, cwd=root)
    if p_list.returncode == 0 and p_list.stdout:
        # filter via rg -F on the file list
        filter_argv = ["rg", "--fixed-strings", "--smart-case", query]
        
        p_filter = run_command(filter_argv, cwd=root, stdin_text=p_list.stdout)
        if p_filter.returncode == 0 and p_filter.stdout.strip():
            name_files = p_filter.stdout.splitlines()[:max_results]

    # Merge content_files and name_files, preserving order, deduping
    seen = set()
    merged_files = []
    for pth in content_files + name_files:
        if pth not in seen:
            merged_files.append(pth)
            seen.add(pth)
        if len(merged_files) >= max_results:
            break

    # Construct Markdown Output
    output = []
    output.append("### Search")
    output.append(f"- Query: {query}")
    output.append(f"- Root: {root}")
    output.append(f"- Max: {max_results}")
    output.append(f"- Ignore: {'no-ignore' if ignored else 'respect'}")
    output.append(f"- Hidden: {'included' if hidden else 'excluded'}")
    output.append(f"- Tools: rg")
    output.append(f"- Strategy: {chosen}")
    
    output.append("\n### Results")
    output.append("Lines (group by file, sorted by path):")
    
    if not by_file:
        output.append("- (0 matches)")
    else:
        for path in sorted(by_file.keys()):
            items = by_file[path]
            output.append(f"- `{path}` ({len(items)} matches)")
            for ln_i, col_i, text in items:
                output.append(f"  - `L{ln_i}:C{col_i}` — `{text}`")
    
    output.append("\nFiles (best matches):")
    if not merged_files:
        output.append("- (0 files)")
    else:
        for pth in merged_files:
            output.append(f"- `{pth}`")

    # Notes
    notes_section = []
    if chosen == "literal":
        notes_section.append("Fallback used: literal substring search (fixed strings).")
    elif chosen == "multi-term-AND":
        notes_section.append("Fallback used: multi-term AND (PCRE2 lookaheads).")
    
    if truncated:
        notes_section.append(f"Results truncated to first {max_results} matches; narrow the query or increase `max`.")
    
    for n in notes:
        notes_section.append(n)
        
    if truncated or (chosen != "regex" and chosen != "none") or notes:
        output.append("\n### Notes")
        for n in notes_section:
            output.append(f"- {n}")

    return "\n".join(output)

if __name__ == "__main__":
    mcp.run(transport="stdio")
