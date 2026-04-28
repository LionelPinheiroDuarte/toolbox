import os
import re
import getpass
import keyring
import requests
from x.utils.colors import error, info, success, command

SERVICE_NAME = "toolbox-nextcloud"

_HOME = os.path.expanduser("~")
_CLAUDE_DIR = os.path.join(_HOME, ".claude")
_PROJECT_SLUG = _HOME.replace("/", "-")
CLAUDE_MEMORY_DIR = os.path.join(_CLAUDE_DIR, "projects", _PROJECT_SLUG, "memory")
CLAUDE_MD = os.path.join(_CLAUDE_DIR, "CLAUDE.md")
JOURNAL_DIR = os.path.expanduser("~/documents/journal")

REMOTE_CLAUDE = "backups/claude-memory"
REMOTE_JOURNAL = "backups/journal"


def _get_credentials():
    creds = {}
    for key in ["url", "user", "password"]:
        val = keyring.get_password(SERVICE_NAME, key)
        if not val:
            print(error(f"Missing credential '{key}'. Run: x sync --configure"))
            raise SystemExit(1)
        creds[key] = val
    return creds


def _webdav_base(url, user):
    return f"{url.rstrip('/')}/remote.php/dav/files/{user}"


def _ensure_remote_dir(base_url, auth, remote_path):
    parts = remote_path.strip("/").split("/")
    for i in range(1, len(parts) + 1):
        partial = "/".join(parts[:i])
        requests.request("MKCOL", f"{base_url}/{partial}", auth=auth)


def _upload(base_url, auth, local_path, remote_dir):
    filename = os.path.basename(local_path)
    with open(local_path, "rb") as f:
        r = requests.put(f"{base_url}/{remote_dir}/{filename}", data=f, auth=auth)
    r.raise_for_status()
    print(success(f"  {filename}"))


def _claude_files():
    files = []
    if os.path.exists(CLAUDE_MD):
        files.append(CLAUDE_MD)
    if os.path.isdir(CLAUDE_MEMORY_DIR):
        for f in sorted(os.listdir(CLAUDE_MEMORY_DIR)):
            files.append(os.path.join(CLAUDE_MEMORY_DIR, f))
    return files


def _journal_files():
    if not os.path.isdir(JOURNAL_DIR):
        return []
    return sorted([
        os.path.join(JOURNAL_DIR, f)
        for f in os.listdir(JOURNAL_DIR)
        if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", f)
    ])


def configure():
    print(info("Configure Nextcloud credentials (stored in system keyring)"))
    url = input("Nextcloud URL (e.g. https://cloud.example.com): ").strip()
    user = input("Username: ").strip()
    password = getpass.getpass("App password: ")
    for key, val in [("url", url), ("user", user), ("password", password)]:
        keyring.set_password(SERVICE_NAME, key, val)
    print(success("Credentials saved."))


def run(claude=False, journal=False):
    creds = _get_credentials()
    base_url = _webdav_base(creds["url"], creds["user"])
    auth = (creds["user"], creds["password"])

    sync_claude = claude or not (claude or journal)
    sync_journal = journal or not (claude or journal)

    total = 0

    if sync_claude:
        print(info("Claude memory:"))
        files = _claude_files()
        if not files:
            print(error("  No Claude files found."))
        else:
            _ensure_remote_dir(base_url, auth, REMOTE_CLAUDE)
            for path in files:
                _upload(base_url, auth, path, REMOTE_CLAUDE)
                total += 1

    if sync_journal:
        print(info("Journal:"))
        files = _journal_files()
        if not files:
            print(error("  No journal notes found."))
        else:
            _ensure_remote_dir(base_url, auth, REMOTE_JOURNAL)
            for path in files:
                _upload(base_url, auth, path, REMOTE_JOURNAL)
                total += 1

    print(success(f"\n{total} file(s) synced to Nextcloud."))
