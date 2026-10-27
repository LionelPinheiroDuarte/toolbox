import os
import shlex
import subprocess
from datetime import date
from x.utils.colors import info, error

JOURNAL_DIR = os.path.expanduser("~/documents/journal")
TASKS_FILE = os.path.join(os.path.expanduser("~/documents/journal"), "tasks.md")

def _bat(path, title):
    subprocess.run(["batcat", "--language=md", f"--file-name={title}", path])

def _edit(path):
    # $VISUAL then $EDITOR, as git does; the value may carry arguments.
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run([*shlex.split(editor), path])

def _files():
    import re
    return sorted([
        f for f in os.listdir(JOURNAL_DIR)
        if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", f)
    ])

def run(last=False, tasks=False, edit=False):
    if tasks:
        if edit:
            _edit(TASKS_FILE)
        elif os.path.exists(TASKS_FILE):
            _bat(TASKS_FILE, "tasks.md")
        else:
            print(error(f"Task file not found: {TASKS_FILE}"))
            print(info("Create it with `x notes -t -e`, or fetch it with `x sync --restore --journal`."))
        return

    today = f"{date.today()}.md"
    today_path = os.path.join(JOURNAL_DIR, today)
    if edit and not last:
        _edit(today_path)
        return

    files = _files()

    if not files:
        print(error("No notes found."))
        return

    if last:
        note = files[-1]
        if edit:
            _edit(os.path.join(JOURNAL_DIR, note))
            return
        print(info(f"Last created — {note}"))
        _bat(os.path.join(JOURNAL_DIR, note), note)
    else:
        if os.path.exists(today_path):
            print(info(f"Today — {today}"))
            _bat(today_path, today)
        else:
            print(info(f"No note for today ({today})."))
