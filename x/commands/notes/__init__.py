import os
import subprocess
from datetime import date
from x.utils.colors import info, error

JOURNAL_DIR = os.path.expanduser("~/documents/journal")
TASKS_FILE = os.path.join(os.path.expanduser("~/documents/journal"), "tasks.md")

def _bat(path, title):
    subprocess.run(["batcat", "--language=md", f"--file-name={title}", path])

def _files():
    import re
    return sorted([
        f for f in os.listdir(JOURNAL_DIR)
        if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", f)
    ])

def run(last=False, tasks=False):
    files = _files()

    if tasks:
        if os.path.exists(TASKS_FILE):
            _bat(TASKS_FILE, "tasks.md")
        else:
            print(error(f"Task file not found: {TASKS_FILE}"))
        return

    if not files:
        print(error("No notes found."))
        return

    if last:
        note = files[-1]
        print(info(f"Last created — {note}"))
        _bat(os.path.join(JOURNAL_DIR, note), note)
    else:
        today = f"{date.today()}.md"
        today_path = os.path.join(JOURNAL_DIR, today)
        if os.path.exists(today_path):
            print(info(f"Today — {today}"))
            _bat(today_path, today)
        else:
            print(info(f"No note for today ({today})."))
