import os
import re
import getpass
import keyring
import requests
from urllib.parse import urlparse, unquote
from x.utils.colors import error, info, success, command

SERVICE_NAME = "toolbox-nextcloud"

_HOME = os.path.expanduser("~")
_CLAUDE_DIR = os.path.join(_HOME, ".claude")
_PROJECT_SLUG = _HOME.replace("/", "-")
CLAUDE_MEMORY_DIR = os.path.join(_CLAUDE_DIR, "projects", _PROJECT_SLUG, "memory")
CLAUDE_MD = os.path.join(_CLAUDE_DIR, "CLAUDE.md")
JOURNAL_DIR = os.path.expanduser("~/documents/journal")
CV_DIR = os.path.expanduser("~/documents/cv")
CV_AGENTS_DIR = os.path.join(_CLAUDE_DIR, "agents")
CV_AGENT_NAMES = ["cv-generator.md", "ats-advisor.md"]
SKILLS_DIR = os.path.join(_CLAUDE_DIR, "skills")

REMOTE_CLAUDE = "backups/claude-memory"
REMOTE_JOURNAL = "backups/journal"
REMOTE_CV = "backups/cv"
REMOTE_CV_AGENTS = "backups/cv/agents"
REMOTE_SKILLS = "backups/skills"


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


def _cv_files():
    files = []
    if os.path.isdir(CV_DIR):
        for f in sorted(os.listdir(CV_DIR)):
            path = os.path.join(CV_DIR, f)
            if os.path.isfile(path):
                files.append(path)
    return files


def _cv_agent_files():
    return [
        os.path.join(CV_AGENTS_DIR, name)
        for name in CV_AGENT_NAMES
        if os.path.exists(os.path.join(CV_AGENTS_DIR, name))
    ]


def _skills_files():
    """Return (local_path, remote_subdir) pairs for every file under
    ~/.claude/skills, walked recursively so nested folders (e.g. references/)
    are preserved on the remote."""
    files = []
    if not os.path.isdir(SKILLS_DIR):
        return files
    for root, _dirs, filenames in sorted(os.walk(SKILLS_DIR)):
        rel_dir = os.path.relpath(root, SKILLS_DIR)
        remote_dir = REMOTE_SKILLS if rel_dir == "." else f"{REMOTE_SKILLS}/{rel_dir}"
        for f in sorted(filenames):
            files.append((os.path.join(root, f), remote_dir))
    return files


def _list_remote_files(base_url, auth, remote_dir):
    url = f"{base_url}/{remote_dir}/"
    r = requests.request(
        "PROPFIND", url, auth=auth,
        headers={"Depth": "1", "Content-Type": "application/xml"},
    )
    r.raise_for_status()
    # Extract <d:href> paths; collections end with "/" (the dir itself
    # and any subdirectories), keep only plain files
    hrefs = re.findall(r"<d:href>([^<]+)</d:href>", r.text)
    files = []
    for href in hrefs:
        if href.endswith("/"):
            continue
        name = href.split("/")[-1]
        if name:
            files.append(name)
    return files


def _list_remote_tree(base_url, auth, remote_dir):
    """Recursively list files under remote_dir. Returns (filename, remote_subdir)
    pairs, where remote_subdir is the full remote path the file lives in."""
    url = f"{base_url}/{remote_dir}/"
    r = requests.request(
        "PROPFIND", url, auth=auth,
        headers={"Depth": "1", "Content-Type": "application/xml"},
    )
    r.raise_for_status()
    hrefs = re.findall(r"<d:href>([^<]+)</d:href>", r.text)
    self_path = urlparse(url).path.rstrip("/")
    results = []
    for href in hrefs:
        href_path = unquote(href).rstrip("/")
        if href_path == self_path:
            continue
        name = href_path.split("/")[-1]
        if not name:
            continue
        if href.endswith("/"):
            sub_remote = f"{remote_dir}/{name}"
            results.extend(_list_remote_tree(base_url, auth, sub_remote))
        else:
            results.append((name, remote_dir))
    return results


def _download(base_url, auth, remote_dir, filename, local_path):
    r = requests.get(f"{base_url}/{remote_dir}/{filename}", auth=auth)
    r.raise_for_status()
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(r.content)
    print(success(f"  {filename}"))


def restore(claude=False, journal=False, cv=False, skills=False):
    creds = _get_credentials()
    base_url = _webdav_base(creds["url"], creds["user"])
    auth = (creds["user"], creds["password"])

    all_sources = not (claude or journal or cv or skills)
    restore_claude = claude or all_sources
    restore_journal = journal or all_sources
    restore_cv = cv or all_sources
    restore_skills = skills or all_sources

    total = 0

    if restore_claude:
        print(info("Claude memory:"))
        try:
            files = _list_remote_files(base_url, auth, REMOTE_CLAUDE)
        except requests.HTTPError as e:
            print(error(f"  Failed to list remote files: {e}"))
            files = []
        for filename in files:
            if filename == "CLAUDE.md":
                local_path = CLAUDE_MD
            else:
                local_path = os.path.join(CLAUDE_MEMORY_DIR, filename)
            _download(base_url, auth, REMOTE_CLAUDE, filename, local_path)
            total += 1

    if restore_journal:
        print(info("Journal:"))
        try:
            files = _list_remote_files(base_url, auth, REMOTE_JOURNAL)
        except requests.HTTPError as e:
            print(error(f"  Failed to list remote files: {e}"))
            files = []
        for filename in files:
            local_path = os.path.join(JOURNAL_DIR, filename)
            _download(base_url, auth, REMOTE_JOURNAL, filename, local_path)
            total += 1

    if restore_cv:
        print(info("CV:"))
        for remote_dir, local_dir in [
            (REMOTE_CV, CV_DIR),
            (REMOTE_CV_AGENTS, CV_AGENTS_DIR),
        ]:
            try:
                files = _list_remote_files(base_url, auth, remote_dir)
            except requests.HTTPError as e:
                print(error(f"  Failed to list remote files: {e}"))
                files = []
            for filename in files:
                local_path = os.path.join(local_dir, filename)
                _download(base_url, auth, remote_dir, filename, local_path)
                total += 1

    if restore_skills:
        print(info("Skills:"))
        try:
            entries = _list_remote_tree(base_url, auth, REMOTE_SKILLS)
        except requests.HTTPError as e:
            print(error(f"  Failed to list remote files: {e}"))
            entries = []
        for filename, remote_dir in entries:
            rel_dir = os.path.relpath(remote_dir, REMOTE_SKILLS)
            local_dir = SKILLS_DIR if rel_dir == "." else os.path.join(SKILLS_DIR, rel_dir)
            local_path = os.path.join(local_dir, filename)
            _download(base_url, auth, remote_dir, filename, local_path)
            total += 1

    print(success(f"\n{total} file(s) restored from Nextcloud."))


def configure():
    print(info("Configure Nextcloud credentials (stored in system keyring)"))
    url = input("Nextcloud URL (e.g. https://cloud.example.com): ").strip()
    user = input("Username: ").strip()
    password = getpass.getpass("App password: ")
    for key, val in [("url", url), ("user", user), ("password", password)]:
        keyring.set_password(SERVICE_NAME, key, val)
    print(success("Credentials saved."))


def run(claude=False, journal=False, cv=False, skills=False):
    creds = _get_credentials()
    base_url = _webdav_base(creds["url"], creds["user"])
    auth = (creds["user"], creds["password"])

    all_sources = not (claude or journal or cv or skills)
    sync_claude = claude or all_sources
    sync_journal = journal or all_sources
    sync_cv = cv or all_sources
    sync_skills = skills or all_sources

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

    if sync_cv:
        print(info("CV:"))
        files = _cv_files()
        agent_files = _cv_agent_files()
        if not (files or agent_files):
            print(error("  No CV files found."))
        else:
            if files:
                _ensure_remote_dir(base_url, auth, REMOTE_CV)
                for path in files:
                    _upload(base_url, auth, path, REMOTE_CV)
                    total += 1
            if agent_files:
                _ensure_remote_dir(base_url, auth, REMOTE_CV_AGENTS)
                for path in agent_files:
                    _upload(base_url, auth, path, REMOTE_CV_AGENTS)
                    total += 1

    if sync_skills:
        print(info("Skills:"))
        files = _skills_files()
        if not files:
            print(error("  No skills found."))
        else:
            seen_dirs = set()
            for path, remote_dir in files:
                if remote_dir not in seen_dirs:
                    _ensure_remote_dir(base_url, auth, remote_dir)
                    seen_dirs.add(remote_dir)
                _upload(base_url, auth, path, remote_dir)
                total += 1

    print(success(f"\n{total} file(s) synced to Nextcloud."))
