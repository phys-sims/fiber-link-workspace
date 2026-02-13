# AGENTS (meta workspace)

## Purpose
This repo is a multi-repo workspace orchestrator for the phys-sims ecosystem.

It does NOT vendor or submodule other repositories. Instead, it uses:
- `repos.toml` (manifest)
- `tools/bootstrap.py` (workspace materialization)

The actual working copies live in `deps/<repo>/`.

## Repos in this workspace
Materialized into `deps/`:

- `abcdef-testbench` (private likely)
  - Depends on: `abcdef-sim`
- `abcdef-sim`
  - Depends on: `phys-pipeline`
- `phys-pipeline`
- `cpa-architecture`
  - Cross-repo ADRs and system-level docs

Dependency chain (direction of breakage risk):
`abcdef-testbench → abcdef-sim → phys-pipeline`

## Non-negotiable workspace rules
- Never commit `deps/` (it is generated and gitignored).
- Do not scan every repo by default. Only open files in the repo(s) relevant to the task.
- If you change an upstream API/contract, you must check downstream usages.

## First action in any task
1) Verify the workspace exists:
   - `ls deps/`
2) If `deps/` is missing:
   - Try: `python tools/bootstrap.py`
   - If that fails due to network restrictions, report that the environment setup must run the bootstrap step.

## Where to make changes
Make changes inside the correct repo directory:
- `deps/phys-pipeline/...`
- `deps/abcdef-sim/...`
- `deps/abcdef-testbench/...`
- `deps/cpa-architecture/...`

Avoid editing metarepo files unless you are:
- updating `repos.toml`
- updating `tools/bootstrap.py`
- adding workspace-level documentation or checklists

## Cross-repo change protocol (do this every time)
When you suspect an API/contract change:

1) Identify provider repo (upstream) and consumer repo(s) (downstream).
2) Search downstream usages BEFORE editing:
   - `rg "<SymbolName>" deps/abcdef-sim`
   - `rg "<SymbolName>" deps/abcdef-testbench`
3) Make upstream change.
4) Update downstream repo(s) to restore compatibility.
5) Add/adjust tests so the break would be caught next time.

If uncertain whether a change is breaking, assume it is and verify downstream.

## Running checks (minimum)
Run checks in each repo you changed (commands may vary by repo; prefer repo-local AGENTS.md if present):

- `pre-commit run -a`
- `pytest`
- `ruff check .`
- `mypy`

If a repo has its own `AGENTS.md`, follow it over this file.

## Git workflow expectations
- Create a branch in the repo you are modifying.
  - If the change is in a dependency repo, branch inside `deps/<repo>`.
  - If the change is in this meta repo (e.g., `repos.toml`, `tools/bootstrap.py`, or workspace docs), branch from the meta repo root.
- Keep commits scoped and message clearly.
- PR descriptions must include:
  - what changed
  - why it changed
  - impacted repos
  - exact test commands run
- After committing, push the branch to the repo’s `origin` and open a PR (use the agent’s PR tool if available).
  - For the meta repo, ensure `origin` is configured before pushing; if it is missing, note that a remote must be added to publish a PR.
- Verify the branch exists on the remote before reporting completion (e.g., `git push -u origin <branch>`).
- If multiple repos are modified, ensure each repo has its own branch/commit/PR; do not mix changes across repos.

## Token/context efficiency
- Use `rg`/`git grep` to narrow scope before opening lots of files.
- Avoid reading generated files, lockfiles, or large artifacts unless needed.

## Network expectations
Assume agent-phase network is unavailable.
Do not attempt to fetch remote content during agent work.
If additional repositories are needed, the environment setup must be updated to bootstrap them.

## Enabling authenticated pushes from agents
The bootstrap script can configure per-repo push URLs using a token from the
following environment variables (first match wins):
`BOOTSTRAP_GIT_TOKEN`, `GIT_TOKEN`, `GITHUB_TOKEN`, `GH_TOKEN`, `GH_TOKEN_2`.
To enable this behavior, ensure the token is present and (optionally) set
`BOOTSTRAP_CONFIGURE_PUSH_URL=1` (default). This updates each repo's
`origin` push URL so `git push` works from inside `deps/<repo>`.
If you do not want bootstrap to rewrite push URLs, set
`BOOTSTRAP_CONFIGURE_PUSH_URL=0`.
