import os
import re
import shutil
import subprocess

import click

from x.utils.colors import error, info, success, command, warning

GITHUB_USER = "LionelPinheiroDuarte"
DEFAULT_DIR = os.environ.get("GITHUB") or os.path.expanduser("~/repos/github")

# origin must be one of my own GitHub repos, over https or ssh
_GITHUB_ORIGIN = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    + GITHUB_USER + r"/[^/]+?(?:\.git)?/?$",
    re.IGNORECASE,
)

OK, FAILED, SKIPPED = "ok", "failed", "skipped"


# --- clone -----------------------------------------------------------------

def _check_gh():
    if shutil.which("gh") is None:
        print(error("gh CLI is not installed."))
        print(info("Install it with: sudo apt install gh"))
        raise SystemExit(1)

def _ensure_dir(directory):
    expanded = os.path.expanduser(directory)
    if not os.path.isdir(expanded):
        print(info(f"Creating {expanded}..."))
        os.makedirs(expanded, exist_ok=True)
    return expanded

def _clone(repo, directory):
    print(command(f"Cloning {repo}..."))
    result = subprocess.run(["gh", "repo", "clone", repo], cwd=directory)
    if result.returncode == 0:
        print(success(f"Done: {repo}"))
    else:
        print(error(f"Failed: {repo}"))

def _list_repos(flags=None):
    cmd = ["gh", "repo", "list", "--source", "--json", "nameWithOwner", "--jq", ".[].nameWithOwner"]
    if flags:
        cmd.extend(flags)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(error(result.stderr.strip()))
        raise SystemExit(1)
    return [r for r in result.stdout.strip().splitlines() if r]

def clone(name=None, language=None, all_repos=False, directory=DEFAULT_DIR):
    _check_gh()
    directory = _ensure_dir(directory)

    if name:
        _clone(name if "/" in name else f"{GITHUB_USER}/{name}", directory)

    elif language:
        repos = _list_repos(["--language", language])
        if not repos:
            print(info(f"No repos found for language: {language}"))
            return
        for repo in repos:
            _clone(repo, directory)

    elif all_repos:
        repos = _list_repos()
        if not repos:
            print(info("No repos found."))
            return
        for repo in repos:
            _clone(repo, directory)


# --- pull / push -----------------------------------------------------------

def _git(path, *args):
    return subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)

def _inspect(path):
    """Return (branch, skip_reason). skip_reason is None when the repo is usable."""
    if not os.path.isdir(os.path.join(path, ".git")):
        return None, "not a git repo"

    origin = _git(path, "remote", "get-url", "origin").stdout.strip()
    if not _GITHUB_ORIGIN.match(origin):
        return None, "no GitHub origin"

    branch = _git(path, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip()
    if not branch:
        return None, "detached HEAD"

    upstream = _git(path, "rev-parse", "--abbrev-ref", "@{u}").stdout.strip()
    if not upstream:
        return branch, f"no upstream (git push -u origin {branch})"
    if not upstream.startswith("origin/"):
        return branch, f"upstream is not on origin: {upstream} (git branch -u origin/{branch})"

    return branch, None

def _is_dirty(path):
    return bool(_git(path, "status", "--porcelain").stdout.strip())

def _git_error(result):
    lines = [l for l in result.stderr.strip().splitlines() if l.strip()]
    return lines[-1] if lines else f"git exited with {result.returncode}"

def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"

def pull_repo(path):
    """Fast-forward the current branch of one repo. Return (status, branch, message)."""
    branch, skip = _inspect(path)
    if skip:
        return SKIPPED, branch, f"skipped: {skip}"

    dirty = " (dirty)" if _is_dirty(path) else ""
    before = _git(path, "rev-parse", "HEAD").stdout.strip()
    # --no-rebase: a repo-level pull.rebase=true would otherwise override --ff-only
    result = _git(path, "pull", "--no-rebase", "--ff-only")
    if result.returncode != 0:
        err = result.stderr
        if "fast-forward" in err:
            return FAILED, branch, "diverged: resolve manually" + dirty
        if "would be overwritten" in err:
            return FAILED, branch, "local changes would be overwritten" + dirty
        return FAILED, branch, _git_error(result) + dirty

    count = int(_git(path, "rev-list", "--count", f"{before}..HEAD").stdout.strip() or 0)
    if count == 0:
        return OK, branch, "up to date" + dirty
    return OK, branch, f"pulled {_plural(count, 'commit')}" + dirty

def _ahead(path):
    """Commits on the current branch not yet on its upstream, as 'sha subject' lines."""
    out = _git(path, "log", "--format=%h %s", "@{u}..HEAD").stdout.strip()
    return out.splitlines() if out else []

def _push_repo(path):
    result = _git(path, "push")
    if result.returncode != 0:
        if "rejected" in result.stderr:
            return FAILED, "rejected: pull first"
        return FAILED, _git_error(result)
    return OK, "pushed"


# --- reporting -------------------------------------------------------------

_MARKS = {OK: success("✓"), FAILED: error("✗"), SKIPPED: warning("-")}
_COLORS = {OK: success, FAILED: error, SKIPPED: warning}

def _report(results):
    """Print one line per repo, then a summary. Exit 1 if any repo failed."""
    rows = [(s, n, f"({b})" if b else "", m) for s, n, b, m in results]
    name_w = max(len(r[1]) for r in rows)
    branch_w = max(len(r[2]) for r in rows)
    for status, name, where, message in rows:
        print(f"{_MARKS[status]} {name:<{name_w}} {where:<{branch_w}}  {_COLORS[status](message)}")

    counts = {s: sum(1 for r in results if r[0] == s) for s in (OK, FAILED, SKIPPED)}
    print()
    print(info(f"{counts[OK]} ok · {counts[FAILED]} failed · {counts[SKIPPED]} skipped"))
    if counts[FAILED]:
        raise SystemExit(1)

def _targets(name, directory):
    """Paths to act on: one named repo, or every directory under `directory`."""
    directory = os.path.expanduser(directory)
    if name:
        path = os.path.join(directory, name)
        if not os.path.isdir(path):
            print(error(f"No repo named {name} in {directory}."))
            raise SystemExit(1)
        return [path]
    return sorted(
        os.path.join(directory, d) for d in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, d)) and not d.startswith(".")
    )

def pull(name=None, directory=DEFAULT_DIR):
    results = []
    for path in _targets(name, directory):
        status, branch, message = pull_repo(path)
        results.append((status, os.path.basename(path), branch, message))
    _report(results)

def push(name=None, directory=DEFAULT_DIR, yes=False):
    results, pending = [], []
    for path in _targets(name, directory):
        repo = os.path.basename(path)
        branch, skip = _inspect(path)
        if skip:
            results.append((SKIPPED, repo, branch, f"skipped: {skip}"))
            continue
        commits = _ahead(path)
        if commits:
            pending.append((path, repo, branch, commits))
        else:
            results.append((OK, repo, branch, "up to date"))

    # pushing everything publishes work I may have forgotten: show it first
    if pending and not name and not yes:
        width = max(len(p[1]) for p in pending)
        for _, repo, branch, commits in pending:
            print(f"{command(f'{repo:<{width}}')} ({branch})  {_plural(len(commits), 'commit')}")
            for c in commits:
                print(f"  {c}")
        print()
        if not click.confirm(f"Push {_plural(len(pending), 'repo')}?", default=False):
            print(info("Aborted."))
            return
        print()

    for path, repo, branch, commits in pending:
        status, message = _push_repo(path)
        if status == OK:
            message = f"pushed {_plural(len(commits), 'commit')}"
        results.append((status, repo, branch, message))

    results.sort(key=lambda r: r[1])
    _report(results)
