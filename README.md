# Repo-local MCP Server Demo

This repository is a minimal, intentionally small example of creating an **MCP (Model Context Protocol) server** inside a repository, so your repo can ship **repo-specific tools** that Copilot/agents can call.

This repo includes three demo MCP servers:

- **`demosquare`** — tiny math tools to validate end-to-end tool calling
- **`sem_ver`** — shows **Pydantic strict typing + Enums** for structured tool inputs
- **`repo_rg`** — performs **code-oriented search** using `ripgrep` with cascading strategies

The demo MCP servers expose these tools:

- `square(n)` → returns $n^2$
- `sqrt(n)` → returns the principal square root of $n$ (errors for negative inputs)
- `bump_version(args)` → structured SemVer bumping via Pydantic + Enums
- `compare_versions(args)` → structured SemVer comparisons via Pydantic + Enums
- `search(args)` → searches the repo using regex, literal, or multi-term AND strategies

The servers run over **stdio**, which is the transport VS Code’s MCP integration expects for local “command-based” MCP servers.

## Demo scope (what this is / isn’t)

This repository is intentionally a **demo**:

- It focuses on the *mechanics* of shipping an MCP server inside a repo (code + dependencies + VS Code wiring).
- The tools are deliberately trivial math so you can verify end-to-end tool calling without needing any repo context.

Non-goals for this demo:

- Not a production-ready tool suite (no auth, no telemetry, no complex error taxonomy).
- Not a security model reference (real tools should be more careful about filesystem/network side effects).
- Not a recommended project layout for all repos—just a minimal pattern you can adapt.

---

## What’s in this repo

Repository layout (current):

- [.vscode/mcp.json](.vscode/mcp.json) — VS Code workspace MCP server configuration (launches the servers via `uv` over stdio)
- [mcp/demosquare/demosquare.py](mcp/demosquare/demosquare.py) — the `demosquare` MCP server implementation (basic math)
- [mcp/demosquare/pyproject.toml](mcp/demosquare/pyproject.toml) — Python packaging metadata for `demosquare`
- `mcp/demosquare/uv.lock` — lockfile for `demosquare`
- `mcp/demosquare/.venv/` — local virtual environment folder (typically not committed)
- [mcp/sem_ver/sem_ver.py](mcp/sem_ver/sem_ver.py) — the `sem_ver` MCP server implementation (Pydantic + Enums)
- [mcp/sem_ver/pyproject.toml](mcp/sem_ver/pyproject.toml) — Python packaging metadata for `sem_ver` (adds `pydantic`)
- [mcp/sem_ver/tests/test_sem_ver.py](mcp/sem_ver/tests/test_sem_ver.py) — basic unit tests for `bump_version` and `compare_versions`
- `mcp/sem_ver/uv.lock` — lockfile for `uv`
- `mcp/sem_ver/.venv/` — local virtual environment folder (typically not committed)
- [mcp/repo_rg/repo_rg.py](mcp/repo_rg/repo_rg.py) — the `repo-rg` MCP server implementation (ripgrep wrapper)
- [mcp/repo_rg/pyproject.toml](mcp/repo_rg/pyproject.toml) — Python packaging metadata for `repo-rg`

---

## Prerequisites

- Python **3.10+** (matches `requires-python = ">=3.10"` in the project)
- `ripgrep` (required for `repo-rg`)
- Either:
  - `uv` (recommended if you want to use the included `uv.lock`), or
  - `pip`/`venv`
- VS Code with MCP server support enabled (this repo includes a workspace MCP config)

---

## Setup

### Option A: Using `uv` (recommended)

From the repo root:

```powershell
cd mcp\demosquare
uv sync
```

This creates/uses `mcp/demosquare/.venv` and installs the `mcp` dependency from the lockfile.

Then run the server:

```powershell
uv run python demosquare.py
```

To set up the `sem_ver` server:

```powershell
cd ..\sem_ver
uv sync
uv run python sem_ver.py
```

To set up the `repo-rg` server:

```powershell
cd ..\repo_rg
uv sync
uv run python repo_rg.py
```

### Option B: Using `venv` + `pip`

From the repo root:

```powershell
cd mcp\demosquare
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install "mcp>=1.0.0"
python demosquare.py
```

To set up the `sem_ver` server with `pip`:

```powershell
cd ..\sem_ver
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install "mcp>=1.0.0" "pydantic>=2.0.0"
python sem_ver.py
```

To set up the `repo-rg` server with `pip`:

```powershell
cd ..\repo_rg
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install "mcp>=1.0.0" "pydantic>=2.0.0"
python repo_rg.py
```

---

## Testing

The only included tests are for the `sem_ver` demo server.

From the repo root:

```powershell
cd mcp\sem_ver
uv run python -m unittest discover -s tests -p "test*.py" -v
```

---

## Running the MCP server

Run:

```powershell
cd mcp\demosquare
python demosquare.py
```

Or:

```powershell
cd mcp\sem_ver
python sem_ver.py
```

Or:

```powershell
cd mcp\repo_rg
python repo_rg.py
```

### What “stdio transport” means

These servers use:

- `mcp.run(transport="stdio")`

That means:

- The server reads requests from **standard input** and writes responses to **standard output**.
- You usually **don’t** interact with it manually in a terminal.
- A host (like VS Code / an agent runtime) launches the process and speaks MCP over stdio.

If you run it directly in a terminal, it will appear to “hang” — that’s normal; it’s waiting for MCP messages.

---

## The tools (API)

The server is created with:

- `mcp = FastMCP("demosquare")`

So the MCP server name is `demosquare`.

### Tool: `square`

- **Signature:** `square(n: int | float) -> float`
- **Behavior:** Returns $n^2$ as a Python `float`.
- **Notes:** Coerces inputs via `float(n)`.

Example:

- `square(135) = 18225.0`

### Tool: `sqrt`

- **Signature:** `sqrt(n: int | float) -> float`
- **Behavior:** Returns $\sqrt{n}$ as a Python `float`.
- **Errors:** Raises `ValueError` if `n < 0`.

Example:

- `sqrt(18225) = 135.0`

### Server: `sem_ver`

The second MCP server is created with:

- `mcp = FastMCP("sem_ver")`

It exists to demonstrate **strict, structured tool contracts** using Pydantic models and Enums.

### Tool: `bump_version`

- **Signature:** `bump_version(args: BumpVersionArgs) -> dict`
- **Behavior:** Bumps a SemVer 2.0.0 version (major/minor/patch) and returns `{old, new, dryRun}`.
- **Why it’s interesting:** The tool input is a Pydantic model with strict typing + enum-constrained fields.

### Tool: `compare_versions`

- **Signature:** `compare_versions(args: CompareVersionsArgs) -> dict`
- **Behavior:** Compares two SemVer 2.0.0 versions using an enum operator and returns `{left, right, op, result}`.
- **Why it’s interesting:** Enums constrain the allowed operators (`lt`, `lte`, `eq`, `gte`, `gt`), which typically renders as a fixed set of choices in tool UIs.

### Server: `repo-rg`

The third MCP server is created with:

- `mcp = FastMCP("repo-rg")`

It demonstrates wrapping a CLI tool (`ripgrep`) to provide code-optimized search with cascading strategies.

### Tool: `search`

- **Signature:** `search(args: SearchArgs) -> str`
- **Behavior:** Searches the repository for a query string.
- **Strategies:**
    1.  **Regex:** Tries to use the query as a regex.
    2.  **Literal:** Falls back to fixed-string matching if regex fails or is invalid.
    3.  **Multi-term AND:** If spaces are present, tries to find lines containing all terms.

---

## Using it from VS Code (repo-specific tools)

The main point of this repo is: **the MCP server lives alongside your code**, so the repo can provide specialized tools that match its own needs.

### 1) Workspace MCP config used by this repo

This repo includes a ready-to-use VS Code workspace MCP configuration at:

- [.vscode/mcp.json](.vscode/mcp.json)

This file is the “wiring” that tells VS Code how to launch the MCP server process.

Current contents:

```jsonc
{
  "servers": {
    "demosquare": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "${workspaceFolder}/mcp/demosquare",
        "python",
        "demosquare.py"
      ]
    },
    "sem_ver": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "${workspaceFolder}/mcp/sem_ver",
        "python",
        "sem_ver.py"
      ]
    },
    "repo-rg": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "${workspaceFolder}/mcp/repo_rg",
        "python",
        "repo_rg.py"
      ]
    }
  },
  "inputs": []
}
```

#### What each field means

(Using `demosquare` as the example; `sem_ver` and `repo-rg` are configured identically).

- `servers`
  - A map of server registrations by name.
  - The key (`"demosquare"`, `"sem_ver"`, `"repo-rg"`) is the server identifier VS Code uses in UI/logs.

- `servers.demosquare.type: "stdio"`
  - Declares the MCP transport.
  - `"stdio"` means VS Code will talk MCP over the process’s stdin/stdout.
  - This matches the server implementation in [mcp/demosquare/demosquare.py](mcp/demosquare/demosquare.py), which calls `mcp.run(transport="stdio")`.

- `servers.demosquare.command: "uv"`
  - The executable VS Code runs to start the server.
  - This setup intentionally uses `uv` so dependency resolution matches [mcp/demosquare/uv.lock](mcp/demosquare/uv.lock) and the environment is reproducible.
  - **Requirement:** `uv` must be installed and discoverable on your `PATH`.

- `servers.demosquare.args`
  - The arguments passed to `uv`.
  - Expanded, VS Code launches effectively:

    ```powershell
    uv run --directory "<workspace>/mcp/demosquare" python demosquare.py
    ```

  - Argument-by-argument:
    - `run` — runs a command inside the project environment managed by `uv`.
    - `--directory ${workspaceFolder}/mcp/demosquare` — tells `uv` which project to run from.
      - This matters because [mcp/demosquare/pyproject.toml](mcp/demosquare/pyproject.toml) lives there.
      - It also ensures `uv` uses that folder’s lockfile and virtual environment.
      - `${workspaceFolder}` is a VS Code variable that expands to the root of your opened workspace.
    - `python` — the command to execute inside the `uv` environment.
    - `demosquare.py` — the script to run (relative to `--directory`).

- `inputs: []`
  - Optional interactive inputs that some VS Code task/config systems support.
  - This demo doesn’t need any, so it’s empty.

#### Why this configuration is “repo-specific”

Because [.vscode/mcp.json](.vscode/mcp.json) lives in the repository:

- teammates can clone the repo and get the same MCP server wiring
- the server implementation and its launch configuration stay versioned together
- changes to tool APIs and changes to launch/setup can ship in the same PR

#### Creating this file from scratch (if you’re replicating the pattern)

1. Create the folder `.vscode/` at the repo root (if it doesn’t exist).
2. Create the file [.vscode/mcp.json](.vscode/mcp.json).
3. Add the JSON shown above.
4. Ensure `uv` and Python 3.10+ are installed.
5. Open the repo folder in VS Code so `${workspaceFolder}` resolves correctly.

### 2) Verify the server starts

Once configured, VS Code should:

- start the process (in this repo, via `uv run --directory ... python demosquare.py`)
- negotiate MCP over stdio
- discover the two tools (`square`, `sqrt`)

### 3) Call the tools from chat

Example prompts:

- “use demosquare to square 135”
- “use demosquare to find sqrt of the result”
- “use sem_ver to bump version 1.2.3 patch”
- “use sem_ver to compare 1.2.3 lt 2.0.0”
- “use repo-rg to search for 'TODO'”
- “use repo-rg to search for 'class User'”

Behind the scenes, the host selects a tool and sends a structured MCP tool call.

---

## Why this pattern is useful

A repo-local MCP server is a clean way to bundle automation that is:

- **close to the code it operates on** (no separate global install needed)
- **versioned with the repo** (tools evolve with the codebase)
- **python language-native** (write tools in Python)
- **safe by default** (tools do only what you implement)

This tiny demo is intentionally simple (math only), but the same structure works for “real” repo-specific needs, for example:

- generating files in repo-specific formats
- enforcing conventions (naming, folder structure, metadata)
- validating schemas
- running targeted checks
- converting/normalizing data
- wrapping and executing custom shell scripts, powershell, or CLI tools
- running builds, tests, or deployments with repo-specific flags
- interacting with repo-specific services or APIs
- more!

---

## Examples of useful repo-local MCP tools

In a real repository, MCP tools are most valuable when they encode **your repo’s conventions and workflows** (the things a generic assistant can’t reliably infer).

Below are examples of practical MCP tools you might expose using this same pattern. These are illustrative “command ideas” (not implemented in this demo).

### Repo navigation & context

- `find_owners(path: str) -> {team: str, slack: str}`
  - Resolve code ownership (e.g., from `CODEOWNERS`) for faster routing.
- `search_repo(query: str, include: str | None) -> list[match]`
  - Opinionated search with repo defaults (paths to include/exclude, ignore generated files).
- `explain_arch(area: str) -> str`
  - Return a curated architecture explainer from your internal docs (and keep it versioned).

### Quality gates (fast, consistent checks)

- `format_check() -> {ok: bool, changedFiles: list[str]}`
  - Run formatter(s) with repo flags and return a structured summary.
- `lint(paths: list[str] | None) -> report`
  - Run linters with the exact ruleset used in CI.
- `run_tests(scope: "unit" | "integration" | "smoke") -> report`
  - Standardize how tests are invoked locally vs CI.

### Code generation & scaffolding

- `scaffold_feature(name: str) -> {created: list[str]}`
  - Create a feature skeleton using your repo’s preferred module layout.
- `generate_client_from_openapi(specPath: str) -> {updated: list[str]}`
  - Generate/refresh typed clients with pinned generator versions.
- `update_docs_index() -> {updated: bool}`
  - Rebuild a docs index/sidebar from the filesystem.

### Release & dependency workflows

- `bump_version(part: "major" | "minor" | "patch") -> {old: str, new: str}`
  - Update version in the one true place (and any derived files).
- `changelog_from_git(sinceTag: str) -> str`
  - Produce a changelog using your conventions (scopes, ticket links, headings).
- `dependency_report() -> {outdated: list[dep], vulnerable: list[vuln]}`
  - Summarize dependency state in a consistent, machine-readable way.

### Data & schema safety

- `validate_schema() -> report`
  - Validate JSON schema / protobuf / migrations using your repo’s rules.
- `migrate_db(dryRun: bool = true) -> report`
  - Run migrations in a controlled way (often “dry-run by default”).

### Guardrails to consider for “real” tools

- Prefer read-only tools by default; make destructive tools require explicit parameters like `confirm: true`.
- Return structured outputs (objects/lists) so the host can render summaries reliably.
- Keep tool behavior deterministic and documented (inputs, outputs, side effects).
- Avoid leaking secrets in outputs; scrub logs/diagnostics.

---

## Extending the server (adding repo-specific tools)

To add a new tool:

1. Open [mcp/demosquare/demosquare.py](mcp/demosquare/demosquare.py)
2. Add a new Python function and decorate it with `@mcp.tool()`
3. Restart the MCP server in VS Code so it re-discovers tools

Example skeleton:

```python
@mcp.tool()
def my_tool(arg1: str) -> str:
    """Explain what the tool does."""
    return f"You passed: {arg1}"
```

### Tool metadata (docstrings & type hints)

FastMCP uses your Python function metadata to make tools easier (and safer) for hosts like VS Code to call:

- **Docstrings become tool helper text.** The function docstring is surfaced as the tool’s human-readable description in the host UI and/or tool picker. A clear first line (plus optional details) makes it much easier for an agent (and a human) to choose the right tool.
- **Type annotations shape the tool schema.** Parameter and return type hints (e.g. `arg1: str`, `-> str`) are used to infer the tool’s input schema so the host can validate/format tool calls and render nicer parameter hints.
  - If you omit annotations, the host may treat inputs as untyped/ambiguous, which can lead to worse tool-call reliability.

#### Enforcing structure with Pydantic models & enums

For non-trivial tools, prefer **explicit request/response models** so the tool contract stays stable and self-documenting.

- Use a **Pydantic `BaseModel`** for inputs (and optionally outputs) to enforce required fields, defaults, and validation.
- Use `typing.Annotated[..., Field(...)]` (or `Field(...)` directly) to attach constraints and descriptions to fields.
- Use `Enum` when callers should choose from a fixed set of values (hosts typically surface these as allowed options).

Example:

```python
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class Part(str, Enum):
  major = "major"
  minor = "minor"
  patch = "patch"


class BumpVersionArgs(BaseModel):
  part: Part = Field(description="Which part of the version to bump")
  dry_run: Annotated[bool, Field(description="Compute the change without writing", default=True)]


@mcp.tool()
def bump_version(args: BumpVersionArgs) -> dict:
  """Bump the repo version.

  Uses a structured schema so callers must pick a valid bump `part`.
  """
  return {"old": "1.2.3", "new": "1.2.4", "dryRun": args.dry_run}
```

Second example (Enums + structured inputs):

```python
from enum import Enum
from pydantic import BaseModel, Field


class CompareOp(str, Enum):
  lt = "lt"
  lte = "lte"
  eq = "eq"
  gte = "gte"
  gt = "gt"


class CompareArgs(BaseModel):
  left: str = Field(description="Left SemVer")
  right: str = Field(description="Right SemVer")
  op: CompareOp = Field(description="Comparison operator")


@mcp.tool()
def compare_versions(args: CompareArgs) -> dict:
  """Compare two semantic versions."""
  return {"left": args.left, "right": args.right, "op": args.op, "result": True}
```

Guidelines:

- Keep tool inputs/outputs JSON-serializable (numbers/strings/objects/lists)
- Raise clear exceptions for invalid input (hosts usually surface error text)
- Prefer deterministic, side-effect-limited tools unless you intentionally need filesystem/network changes

---

## Troubleshooting

### The server “hangs” when I run it

Expected. It’s an MCP server waiting for stdio messages. It’s meant to be launched by an MCP host.

### VS Code can’t start the server

Common causes:

- Wrong Python interpreter on PATH
- Missing dependency `mcp`
- Wrong working directory or script path

Try launching it the same way VS Code does:

```powershell
uv run --directory mcp/demosquare python demosquare.py
```

If you’re using `uv`, prefer:

```powershell
cd mcp\demosquare
uv run python demosquare.py
```

### `sqrt` fails

`sqrt` raises a `ValueError` for negative inputs by design.

---

## Notes

- This demo is intentionally minimal to focus on the MCP server pattern.
- If you plan to commit this repo, consider adding `.venv/` to `.gitignore`.
