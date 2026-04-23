import os
import shutil
import subprocess
from x.utils.colors import error, info, success, command

DEFAULT_DEST = os.path.expanduser("~/repos/github")

def _check_gh():
    if shutil.which("gh") is None:
        print(error("gh CLI is not installed."))
        print(info("Install it with: sudo apt install gh"))
        raise SystemExit(1)

def _ensure_dest(dest):
    expanded = os.path.expanduser(dest)
    if not os.path.isdir(expanded):
        print(info(f"Creating {expanded}..."))
        os.makedirs(expanded, exist_ok=True)
    return expanded

def _clone(repo, dest):
    print(command(f"Cloning {repo}..."))
    result = subprocess.run(["gh", "repo", "clone", repo], cwd=dest)
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

def run(single=None, language=None, all_repos=False, dest=DEFAULT_DEST):
    _check_gh()
    dest = _ensure_dest(dest)

    if single:
        _clone(single, dest)

    elif language:
        repos = _list_repos(["--language", language])
        if not repos:
            print(info(f"No repos found for language: {language}"))
            return
        for repo in repos:
            _clone(repo, dest)

    elif all_repos:
        repos = _list_repos()
        if not repos:
            print(info("No repos found."))
            return
        for repo in repos:
            _clone(repo, dest)
