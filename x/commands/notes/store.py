"""The journal on disk: which notes there are, what they say about
themselves, and creating or trashing one. No terminal output here, so the
browser (browse.py) and the tests share the same logic.

    ~/documents/journal/
      tasks.md            the task file
      YYYY-MM-DD.md       dated notes, written by the journal agent
      notes/<slug>.md     topic notes

X_JOURNAL_DIR overrides the location (tests, demos).
"""
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date

JOURNAL_DIR = os.path.expanduser(os.environ.get("X_JOURNAL_DIR", "~/documents/journal"))
NOTES_SUBDIR = "notes"
TASKS_NAME = "tasks.md"

DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
# **Date:** 2026-07-04 | **Project:** toolbox | **Tags:** pipx, python
META = re.compile(r"^\*\*Date:\*\*.*\|")


@dataclass
class Note:
    kind: str           # "tasks", "dated" or "topic"
    path: str
    title: str
    project: str = ""
    tags: str = ""
    day: date = None    # dated notes only
    mtime: float = 0.0  # 0 when the file does not exist yet (tasks.md)


def tasks_path(root=None):
    return os.path.join(root or JOURNAL_DIR, TASKS_NAME)


def _meta_fields(line):
    fields = {}
    for part in line.split("|"):
        m = re.match(r"\s*\*\*(\w+):\*\*\s*(.*?)\s*$", part)
        if m:
            fields[m.group(1).lower()] = m.group(2)
    return fields


def read_header(path):
    """(title, project, tags, summary) from the top of a note: the first H1,
    the **Date:** | **Project:** | **Tags:** line, and the first line of
    text that is neither a heading nor that line. Missing parts are ""."""
    title = project = tags = summary = ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for _, line in zip(range(40), f):
                line = line.strip()
                if not line:
                    continue
                if not title and line.startswith("# "):
                    title = line[2:].strip()
                elif META.match(line):
                    fields = _meta_fields(line)
                    project, tags = fields.get("project", ""), fields.get("tags", "")
                elif not line.startswith("#") and not summary:
                    summary = line
                if title and summary:
                    break
    except OSError:
        pass
    return title, project, tags, summary


def list_notes(root=None):
    """Every note: the task file first (even when it does not exist yet),
    then the dated notes newest first, then the topic notes most recently
    modified first."""
    root = root or JOURNAL_DIR
    tasks = tasks_path(root)
    notes = [Note("tasks", tasks, TASKS_NAME,
                  mtime=os.path.getmtime(tasks) if os.path.exists(tasks) else 0.0)]

    dated = []
    for name in os.listdir(root) if os.path.isdir(root) else []:
        m = DATED.match(name)
        if not m:
            continue
        path = os.path.join(root, name)
        try:
            day = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        # a daily report's H1 only repeats the date: its summary says more
        title, _, _, summary = read_header(path)
        if not title or title.startswith("Daily Report"):
            title = summary or title
        dated.append(Note("dated", path, title, day=day, mtime=os.path.getmtime(path)))
    notes += sorted(dated, key=lambda n: n.day, reverse=True)

    topic = []
    notes_dir = os.path.join(root, NOTES_SUBDIR)
    for name in os.listdir(notes_dir) if os.path.isdir(notes_dir) else []:
        if not name.endswith(".md"):
            continue
        path = os.path.join(notes_dir, name)
        title, project, tags, _ = read_header(path)
        topic.append(Note("topic", path, title or name[:-3], project, tags,
                          mtime=os.path.getmtime(path)))
    notes += sorted(topic, key=lambda n: n.mtime, reverse=True)
    return notes


def slugify(text):
    """"Docker buildx: cache!" -> "docker-buildx-cache". Accents are kept
    (é stays é): the file system is fine with them and the name stays readable."""
    slug = re.sub(r"[^\w]+", "-", text.strip().lower())
    return slug.strip("-_")


def new_note(query, root=None, today=None):
    """The path to open for ctrl-n, creating the file if needed: today's note
    for an empty query, notes/<slug>.md otherwise. An existing note is never
    overwritten, it is just returned."""
    root = root or JOURNAL_DIR
    today = today or date.today()
    query = (query or "").strip()
    if query.lower().endswith(".md"):  # a file name typed in full
        query = query[:-3].strip()
    slug = slugify(query)
    if not slug:
        path = os.path.join(root, f"{today.isoformat()}.md")
        content = ""
    else:
        path = os.path.join(root, NOTES_SUBDIR, f"{slug}.md")
        content = f"# {query}\n\n**Date:** {today.isoformat()} | **Project:** | **Tags:**\n\n"
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return path


def ensure_tasks(root=None):
    """tasks.md, created empty on first open."""
    path = tasks_path(root)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "a").close()
    return path


class TrashRefused(Exception):
    pass


def trash(path, root=None, run=subprocess.run):
    """Move a note to the desktop trash (gio trash), so a slip of ctrl-x can
    be undone. Refuses the task file and anything outside the journal."""
    root = os.path.realpath(root or JOURNAL_DIR)
    real = os.path.realpath(path)
    if os.path.commonpath([root, real]) != root or not real.endswith(".md"):
        raise TrashRefused(f"{path} n'est pas une note du journal")
    if real == os.path.realpath(tasks_path(root)):
        raise TrashRefused("tasks.md ne part jamais à la corbeille")
    if not os.path.isfile(real):
        raise TrashRefused(f"{os.path.basename(path)} n'existe pas")
    if not shutil.which("gio"):
        raise TrashRefused("gio n'est pas installé : rien n'a été supprimé")
    run(["gio", "trash", real], check=True, capture_output=True, text=True)
