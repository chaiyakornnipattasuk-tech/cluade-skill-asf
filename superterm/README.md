# Super Terminal

An AI-augmented terminal you run locally. It's a normal shell (plain commands
run as-is), plus an AI that can navigate, tag, and organize your files, preview
old PHP/Python 2 code, and query multiple data sources as if they were one
database.

Prior art this borrows ideas from: [Open Interpreter](https://www.openinterpreter.com/cli)
(local, tool-using AI with pluggable hosted/local models) for the agent loop, and
[Airbyte](https://airbyte.com/)'s "many connectors → one normalized store" model
for the data layer, scaled down to a single local DuckDB file instead of a full
data platform.

## What it actually does

- **Pick your AI**: Anthropic/OpenAI API key, or a fully local open-source model
  via [Ollama](https://ollama.com) — no key, no network call.
- **Scoped file access**: you set a workspace root ("the drive" — any local
  folder, including a Google Drive/Dropbox/OneDrive sync folder that already
  looks like a normal directory once synced to disk). The AI can only read/move
  files inside it.
- **Navigate, tag, search, organize**: tags live in a sidecar SQLite DB, never
  touching your files. `organize_plan` always previews moves before
  `organize_apply` (or a real move) touches disk.
- **Legacy file preview**: syntax-highlighted PHP/Python rendering, with a
  heuristic flag for Python 2 syntax (`print` statements, `except X, e:`,
  `xrange`, etc.) so you know why an old script won't just run under Python 3.
- **Cross-source data queries**: describe CSV exports, SQLite/Postgres
  databases, and REST APIs in one YAML file; `sync` loads them all into a local
  DuckDB warehouse as `<source>__<table>`, so one SQL query — or one AI request
  — can join data that started out in completely unrelated systems.

## On the "different government departments" use case

This does **not** grant access to any agency's system — nothing can. What it
gives you is a single place to point at whatever each department is *already*
willing to export or expose (a CSV drop, a read-only DB replica, an open-data
REST API) and query them together instead of stitching spreadsheets by hand.
Getting the actual data access is still a people/policy problem; this tool
only removes the "now what, six incompatible formats" step after that.

## Install

```bash
cd superterm
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[anthropic]"     # or "[openai]", or neither for Ollama-only use
```

## Configure

```bash
# pick a backend
superterm config set-backend anthropic   # | openai | ollama
superterm config set-model claude-sonnet-5

# point it at the folder you want it to have access to
superterm config set-workspace ~/Documents

# API key: prefer an env var...
export ANTHROPIC_API_KEY=sk-...
# ...or store one locally (chmod 600, ~/.superterm/keys.yaml)
superterm config set-key anthropic sk-...

# for Ollama: nothing to set beyond `ollama serve` running locally
superterm config set-backend ollama
superterm config set-model llama3.1
```

## Use

```bash
superterm start                 # interactive shell: normal commands + AI chat
superterm ask "tag all PDFs in ~/Documents/taxes with '2025'"
superterm preview legacy/report.php
superterm sync                  # reload all configured data sources
superterm query "SELECT * FROM hr__employees LIMIT 10"
```

Inside `superterm start`, anything typed is tried as a real shell command
first; if it's not one, it's sent to the AI as a natural-language request.

## Data sources

Copy `config/connectors.example.yaml` to `~/.superterm/connectors.yaml` and
describe your sources:

```yaml
sources:
  permits_dept:
    type: csv
    path: "./data/permits/*.csv"
    table: permits
  finance_dept:
    type: sqlite
    path: "./data/finance/budgets.sqlite"
```

Then `superterm sync` and `superterm query "SELECT ... FROM permits_dept__permits JOIN finance_dept__budgets ON ..."`.
Secrets in the YAML (API tokens, DB passwords) can use `${ENV_VAR}` and are
expanded from your shell environment, never stored in the file.

## Safety notes

- File moves/deletes and applying an organize plan require an explicit
  confirmation prompt — the AI can propose, a human approves.
- `query_data` rejects non-`SELECT` statements (no `DROP`/`INSERT`/etc. through
  that tool).
- All file tools are hard-scoped to the configured workspace root; paths that
  resolve outside it are rejected before any I/O happens.

## Run the tests

```bash
pip install -e ".[dev]"
pytest
```
