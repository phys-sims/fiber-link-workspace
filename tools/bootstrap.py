#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from urllib.parse import quote, urlparse, urlunparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Python 3.11+: tomllib
# Python <=3.10: use tomli (already commonly installed via pytest deps)
try:
    import tomllib  # type: ignore[attr-defined]
    _toml_loads = tomllib.loads
except ModuleNotFoundError:
    import tomli  # type: ignore[import-not-found]
    _toml_loads = tomli.loads


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "repos.toml"
DEPS_DIR = ROOT / "deps"

# Make git fail fast instead of hanging on interactive prompts
_GIT_ENV = {
    **os.environ,
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_ASKPASS": "/bin/true",
}

# Tunables via env vars (override in setup script if desired)
DEFAULT_TIMEOUT_S = int(os.environ.get("BOOTSTRAP_GIT_TIMEOUT_S", "1800"))  # 30 min
CLONE_DEPTH = os.environ.get("BOOTSTRAP_CLONE_DEPTH", "1")  # "1" or "0" (0 means full)
USE_PARTIAL_CLONE = os.environ.get("BOOTSTRAP_USE_PARTIAL_CLONE", "1") == "1"  # uses --filter=blob:none
PRESERVE_LOCAL = os.environ.get("BOOTSTRAP_PRESERVE_LOCAL", "0") == "1"  # skip reset/clean for local work
PUSH_TOKEN_ENV_VARS = (
    "BOOTSTRAP_GIT_TOKEN",
    "GIT_TOKEN",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GH_TOKEN_2",
)
CONFIGURE_PUSH_URL = os.environ.get("BOOTSTRAP_CONFIGURE_PUSH_URL", "1") == "1"


@dataclass(frozen=True)
class RepoSpec:
    name: str
    url: str
    ref: str = "main"


def log(msg: str) -> None:
    print(msg, flush=True)


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    env: dict[str, str] | None = None,
    log_cmd: list[str] | None = None,
) -> None:
    where = f" (cwd={cwd})" if cwd else ""
    log(f"+ {' '.join(log_cmd or cmd)}{where}")
    subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        timeout=timeout_s,
        env=env,
    )


def resolve_push_token() -> str | None:
    for key in PUSH_TOKEN_ENV_VARS:
        value = os.environ.get(key)
        if value:
            return value
    return None


def build_push_url(url: str, token: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    netloc = parsed.netloc
    userinfo = f"x-access-token:{quote(token, safe='')}"
    return urlunparse(parsed._replace(netloc=f"{userinfo}@{netloc}"))


def configure_push_url(spec: RepoSpec) -> None:
    if not CONFIGURE_PUSH_URL:
        return
    token = resolve_push_token()
    if not token:
        return
    push_url = build_push_url(spec.url, token)
    if not push_url:
        log(f"Skipping push URL config for {spec.name}; unsupported URL scheme.")
        return
    redacted = push_url.replace(token, "****")
    run(
        ["git", "remote", "set-url", "--push", "origin", push_url],
        cwd=repo_dir(spec),
        env=_GIT_ENV,
        log_cmd=["git", "remote", "set-url", "--push", "origin", redacted],
    )
    log(f"Configured push URL for {spec.name} (token from env).")


def load_manifest() -> list[RepoSpec]:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST}")

    data: dict[str, Any] = _toml_loads(MANIFEST.read_text(encoding="utf-8"))
    repos = data.get("repo", [])
    if not isinstance(repos, list) or not repos:
        raise ValueError("repos.toml must contain at least one [[repo]] entry")

    specs: list[RepoSpec] = []
    for r in repos:
        if not isinstance(r, dict):
            raise ValueError(f"Invalid [[repo]] entry (not a table): {r!r}")
        if "name" not in r or "url" not in r:
            raise ValueError(f"Invalid [[repo]] entry (needs name + url): {r!r}")
        name = str(r["name"])
        url = str(r["url"])
        ref = str(r.get("ref", "main"))
        specs.append(RepoSpec(name=name, url=url, ref=ref))
    return specs


def repo_dir(spec: RepoSpec) -> Path:
    return DEPS_DIR / spec.name


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def has_submodules(path: Path) -> bool:
    return (path / ".gitmodules").exists()


def is_dirty_repo(path: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(path),
        stdout=subprocess.PIPE,
        text=True,
        env=_GIT_ENV,
        check=False,
    )
    return bool(result.stdout.strip())


def clone_repo(spec: RepoSpec) -> None:
    dest = repo_dir(spec)
    DEPS_DIR.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = ["git", "clone"]

    # Partial clone speeds things up; can be disabled if it causes trouble
    if USE_PARTIAL_CLONE:
        cmd += ["--filter=blob:none"]

    # Depth=1 for speed; set BOOTSTRAP_CLONE_DEPTH=0 for full history
    if CLONE_DEPTH != "0":
        cmd += ["--depth", CLONE_DEPTH]

    # Single branch checkout for the requested ref
    cmd += ["--single-branch", "--branch", spec.ref, spec.url, str(dest)]
    run(cmd, timeout_s=DEFAULT_TIMEOUT_S, env=_GIT_ENV)


def update_repo(spec: RepoSpec) -> None:
    dest = repo_dir(spec)

    # Keep origin URL correct in case you changed it in repos.toml
    run(["git", "remote", "set-url", "origin", spec.url], cwd=dest, env=_GIT_ENV)

    # Fetch latest for the branch (depth-limited if requested)
    fetch_cmd = ["git", "fetch", "--prune"]
    if CLONE_DEPTH != "0":
        fetch_cmd += ["--depth", CLONE_DEPTH]
    fetch_cmd += ["origin", spec.ref]
    run(fetch_cmd, cwd=dest, timeout_s=DEFAULT_TIMEOUT_S, env=_GIT_ENV)

    if PRESERVE_LOCAL or is_dirty_repo(dest):
        log(f"Skipping reset/clean for {spec.name} (preserve local work).")
        return

    # Hard reset to origin/<ref> so repeated runs are deterministic
    run(["git", "reset", "--hard", f"origin/{spec.ref}"], cwd=dest, env=_GIT_ENV)

    # Remove untracked files from previous runs (keeps workspace clean)
    run(["git", "clean", "-ffd"], cwd=dest, env=_GIT_ENV)


def update_submodules_if_any(spec: RepoSpec) -> None:
    dest = repo_dir(spec)
    if not has_submodules(dest):
        return

    log(f"--- submodules: {spec.name} ---")
    run(["git", "submodule", "sync", "--recursive"], cwd=dest, env=_GIT_ENV)

    cmd = ["git", "submodule", "update", "--init", "--recursive"]
    if CLONE_DEPTH != "0":
        cmd += ["--depth", CLONE_DEPTH]
    run(cmd, cwd=dest, timeout_s=DEFAULT_TIMEOUT_S, env=_GIT_ENV)


def ensure_repo(spec: RepoSpec) -> None:
    dest = repo_dir(spec)
    log(f"\n=== {spec.name} @ {spec.ref} ===")
    log(f"URL : {spec.url}")
    log(f"DEST: {dest}")

    if not is_git_repo(dest):
        clone_repo(spec)
    else:
        update_repo(spec)

    configure_push_url(spec)
    update_submodules_if_any(spec)
    log(f"=== OK {spec.name} ===")


def main() -> int:
    log(f"Python: {sys.executable}")
    log(f"Version: {sys.version.split()[0]}")
    log(f"Root: {ROOT}")
    log(f"Manifest: {MANIFEST}")
    log(f"Deps dir: {DEPS_DIR}")
    log(f"Timeout: {DEFAULT_TIMEOUT_S}s | Depth: {CLONE_DEPTH} | Partial: {USE_PARTIAL_CLONE}")
    log(f"Preserve local: {PRESERVE_LOCAL}")

    try:
        specs = load_manifest()
    except Exception as e:
        log(f"ERROR: {e}")
        return 2

    # Continue-on-failure and summarize at end
    failures: list[str] = []

    # Deterministic order for stable logs
    for spec in sorted(specs, key=lambda s: s.name):
        try:
            ensure_repo(spec)
        except subprocess.TimeoutExpired as e:
            failures.append(f"{spec.name}: TIMEOUT running {' '.join(e.cmd) if e.cmd else 'git'}")
        except subprocess.CalledProcessError as e:
            failures.append(f"{spec.name}: FAILED (exit {e.returncode}) running: {' '.join(e.cmd)}")
        except Exception as e:
            failures.append(f"{spec.name}: ERROR {type(e).__name__}: {e}")

    if failures:
        log("\n=== BOOTSTRAP SUMMARY: PARTIAL FAILURE ===")
        for f in failures:
            log(f" - {f}")
        log(f"\nWorkspace is partial. See deps/: {DEPS_DIR}")
        return 4

    log("\n=== BOOTSTRAP SUMMARY: SUCCESS ===")
    log(f"Workspace ready: {DEPS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
