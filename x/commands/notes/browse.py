"""`x notes --browse`: the journal in an fzf popup, built like the
claude-projects popup (agents repo) so they look and behave alike.

fzf drives the interface and calls `x notes` back for every action:

    --list-entries          the list (also on every reload)
    --open-path <path>      enter: edit the note, then back to the list
    --window-path <path>    ctrl-o: edit it in a new tmux window, popup closes
    --new-note <query>      ctrl-n: today's note, or notes/<slug>.md
    --trash-path <path>     ctrl-x: to the trash, then reload

The preview is plain batcat, run by fzf itself: no Python start-up on each
move. The list is one line per note under a header line per group:

    <header>\t<row>\t<path>\t<kind>

Header lines have an empty path, which is how the cursor skips them.
"""
import os
import shlex
import shutil
import subprocess
import sys
import time

from x.commands.notes import store

# palette of the agents repo's popups (tools/lib/popup.sh), kept in sync by hand
DIM = "\033[38;2;139;147;163m"
BLU = "\033[38;2;130;170;255m"
YLW = "\033[38;2;229;192;123m"
BOLD = "\033[1m"
OFF = "\033[0m"
KEY = "\033[48;2;90;98;115m\033[38;2;214;217;223m"
ACCENT = "#82aaff"

GROUPS = [("tasks", "TÂCHES"), ("dated", "JOURNAL"), ("topic", "NOTES")]
DAYS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
FZF_MIN = (0, 66)  # --footer (0.63), --gutter (0.66), as the agents popups


def ago(epoch, now=None):
    """"< 1 min", "4 min", "2 h", "hier", "3 j", "2 sem", "1 mois", "3 ans"."""
    age = (now or time.time()) - epoch
    if age < 60:
        return "< 1 min"
    if age < 3600:
        return f"{int(age // 60)} min"
    if age < 86400:
        return f"{int(age // 3600)} h"
    if age < 2 * 86400:
        return "hier"
    if age < 14 * 86400:
        return f"{int(age // 86400)} j"
    if age < 60 * 86400:
        return f"{int(age // 604800)} sem"
    if age < 365 * 86400:
        return f"{int(age // 2592000)} mois"
    if age < 730 * 86400:
        return "1 an"
    return f"{int(age // 31536000)} ans"


def _cut(text, width):
    if width <= 0:
        return ""
    return text if len(text) <= width else text[:max(width - 1, 0)] + "…"


def _list_width():
    """Columns a row may use: half the popup (the preview takes the other
    half), less the pointer and gutter. In a reload, stdout is a pipe: the
    width is fzf's $FZF_COLUMNS (0 before fzf has drawn, hence no reload at
    start); otherwise the terminal's, asked on stdout."""
    # $FZF_COLUMNS is inside the border: 4 columns less than the terminal
    cols = int(os.environ.get("FZF_COLUMNS") or 0) or shutil.get_terminal_size().columns - 4
    return max(cols // 2 - 3, 30)


def row(note, width, now=None):
    """One list row, coloured, at most <width> columns (age included)."""
    # a dated note is as old as its day (its mtime moves on every sync restore)
    when = time.mktime(note.day.timetuple()) if note.day else note.mtime
    age = f"{ago(when, now):>7}" if when else ""
    avail = width - len(age) - 2
    if note.kind == "tasks":
        state = "" if note.mtime else "à créer"
        text = f"{BOLD}{note.title}{OFF}"
        pad = avail - len(note.title) - len(state)
        return f"{text}{' ' * max(pad, 1)}{DIM}{state}{OFF}  {DIM}{age}{OFF}"
    if note.kind == "dated":
        lead = f"{note.day.isoformat()} {DAYS[note.day.weekday()]}  "
        title = _cut(note.title, avail - len(lead))
        pad = avail - len(lead) - len(title)
        return (f"{YLW}{note.day.isoformat()}{OFF} {DIM}{DAYS[note.day.weekday()]}{OFF}  "
                f"{title}{' ' * max(pad, 0)}  {DIM}{age}{OFF}")
    meta = " · ".join(x for x in (note.project, note.tags) if x)
    # the title comes first: project and tags get at most 40% of the row
    meta = _cut(meta, min(len(meta), avail * 2 // 5))
    if len(meta) < 8:  # a stub of a word says nothing: the title takes it all
        meta = ""
    title = _cut(note.title, avail - len(meta) - 2 if meta else avail)
    pad = avail - len(title) - len(meta)
    return f"{title}{' ' * max(pad, 1)}{DIM}{meta}{OFF}  {DIM}{age}{OFF}"


def entries(root=None, width=None, now=None):
    """The fzf input: every group's header (always, so the header count the
    info line subtracts stays 3), then its notes."""
    width = width or _list_width()
    notes = store.list_notes(root)
    lines = []
    for kind, label in GROUPS:
        lines.append(f"{DIM}{label}{OFF}\t\t\t")
        for note in notes:
            if note.kind == kind:
                # the row is cut to fit: the whole title, project and tags go
                # after it, past the right edge (see --ellipsis), for the search
                full = " ".join(x for x in (note.title, note.project, note.tags) if x)
                lines.append(f"\t{row(note, width, now)}{' ' * 200}{full}"
                             f"\t{note.path}\t{note.kind}")
    return lines


def _editor_argv(path):
    # $VISUAL then $EDITOR, as git does; the value may carry arguments
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    return [*shlex.split(editor), path]


def open_path(path):
    if not path:
        return
    if os.path.realpath(path) == os.path.realpath(store.tasks_path()):
        store.ensure_tasks()
    subprocess.run(_editor_argv(path))


def open_window(path):
    """ctrl-o: the note in a new tmux window named note:<name>; outside tmux,
    just the editor here."""
    if not path:
        return
    if os.path.realpath(path) == os.path.realpath(store.tasks_path()):
        store.ensure_tasks()
    if not os.environ.get("TMUX"):
        subprocess.run(_editor_argv(path))
        return
    name = os.path.splitext(os.path.basename(path))[0]
    subprocess.run(["tmux", "new-window", "-n", f"note:{name}",
                    "-c", os.path.dirname(path), *_editor_argv(path)])


def new_note(query):
    subprocess.run(_editor_argv(store.new_note(query)))


def trash_path(path, self_cmd):
    """Prints the fzf actions to run next (ctrl-x is a transform): reload and
    say what happened, or just say why nothing was done."""
    if not path:
        return
    name = os.path.relpath(path, store.JOURNAL_DIR)
    try:
        store.trash(path)
    except store.TrashRefused as e:
        print(f"bell+change-header:⚠ {e}")
        return
    except subprocess.CalledProcessError as e:
        # "gio: file:///…/note.md: Operation not supported": keep the reason
        lines = (e.stderr or "").strip().splitlines()
        reason = lines[-1].split(": ")[-1] if lines else "gio trash a échoué"
        print(f"bell+change-header:⚠ {name} n'a pas été supprimée : {reason}")
        return
    print(f"reload({self_cmd} --list-entries)+change-header:"
          f"✓ {name} est dans la corbeille (~/.local/share/Trash/files)")


NEW_PROMPT = "nouvelle note ❯ "
NEW_GHOST = "nom du fichier · esc pour annuler"
SEARCH_MODE = "change-prompt(❯ )+enable-search+clear-query+change-ghost(chercher une note)"


def _enter(self_cmd, reload):
    """The shell behind enter, which prints the fzf actions to run: in the
    name field, create the note named by the query (read from $FZF_QUERY
    by the editor's shell, so a ")" in the name can't break the action) and
    go back to searching; in the list, edit the note under the cursor."""
    create = f"execute({self_cmd} --new-note \\\"\\$FZF_QUERY\\\")+{SEARCH_MODE}+{reload}"
    edit = f"execute({self_cmd} --open-path {{3}})+change-header()+{reload}"
    return (f"if [ \"$FZF_PROMPT\" = '{NEW_PROMPT}' ]; then echo \"{create}\"; "
            f"elif [ -n {{3}} ]; then echo \"{edit}\"; fi")


def _fzf_version():
    try:
        out = subprocess.run(["fzf", "--version"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return None
    try:
        return tuple(int(x) for x in out.split()[0].split(".")[:2])
    except (IndexError, ValueError):
        return None


def self_command():
    """How fzf calls this command back: the same x, by absolute path."""
    return f"{shlex.quote(os.path.abspath(sys.argv[0]))} notes"


def browse():
    version = _fzf_version()
    if not version or version < FZF_MIN:
        found = ".".join(map(str, version)) if version else "aucun"
        print(f"x notes --browse a besoin de fzf >= 0.66 (installé : {found}).")
        print("Lance le playbook dotfiles : ansible-playbook -i inventory.ini playbook.yml --tags fzf -K")
        if os.environ.get("TMUX"):
            input()  # keep the popup open long enough to read it
        sys.exit(1)

    self_cmd = self_command()
    reload = f"reload({self_cmd} --list-entries)"
    headers = len(GROUPS)
    footer = (f"{KEY} ⏎ {OFF} ouvrir   {KEY} ^O {OFF} fenêtre tmux   {KEY} ^N {OFF} nouvelle   "
              f"{KEY} ^X {OFF} corbeille   {KEY} ^/ {OFF} aperçu\n"
              f"{DIM}^N : nom du fichier, créé dans notes/ · vide : note du jour{OFF}")
    preview = ("[ -s {3} ] && batcat --color=always --style=plain --language=md "
               "--terminal-width=$FZF_PREVIEW_COLUMNS {3} "
               f"|| printf '{DIM}%s{OFF}\\n' \"$(basename {{3}}) est vide — ⏎ pour l'écrire\"")
    info = (f'm=$FZF_MATCH_COUNT; [ -z "$FZF_QUERY" ] && m=$((m - {headers})); '
            f'echo "$m/$((FZF_TOTAL_COUNT - {headers}))"')

    cmd = [
        "fzf", "--ansi", "--layout=reverse", "--delimiter", "\t",
        "--with-nth", "1,2", "--nth", "2", "--tabstop", "1",
        # keep the cursor on the same note across reloads (its path)
        "--id-nth", "3", "--track",
        "--border=rounded", "--border-label", " ◆ notes ", "--border-label-pos=3",
        "--input-border=line", "--footer-border=line",
        "--prompt", "❯ ", "--ghost", "chercher une note", "--info=inline-right",
        "--no-separator", "--pointer", "▌", "--gutter", " ", "--highlight-line",
        "--no-scrollbar",
        # rows carry their full text past the edge, for the search: cut it
        # without a marker, and never scroll sideways to show a match there
        "--ellipsis", "", "--no-hscroll",
        "--color", f"bg+:#2c313c,fg+:#d6d9df,pointer:{ACCENT},hl:{ACCENT},hl+:{ACCENT}",
        "--color", f"border:#5a6273,label:{ACCENT}:bold,prompt:{ACCENT},info:#d6d9df,"
                   "ghost:#5a6273,header:#d6d9df",
        "--color", "input-border:#5a6273,footer-border:#5a6273,preview-border:#5a6273",
        "--footer", footer, "--info-command", info,
        "--preview-window", "right,50%,border-left", "--preview", preview,
        # the cursor never rests on a header line (empty {3})
        "--bind", "change:first+change-header()",
        "--bind", "result:transform([ -n {3} ] || echo down)",
        "--bind", "down:down+transform([ -n {3} ] || echo down)",
        "--bind", "up:up+transform([ -n {3} ] || { [ $FZF_POS -le 1 ] && echo down || echo up; })",
        # ctrl-n turns the input into a field for the new note's name (the
        # prompt says which mode is on): enter creates, esc goes back
        "--bind", f"ctrl-n:change-prompt({NEW_PROMPT})+disable-search+clear-query"
                  f"+change-ghost({NEW_GHOST})+change-header()",
        # (transform: to the end of the string, as their scripts hold ")")
        "--bind", f"enter:transform:{_enter(self_cmd, reload)}",
        "--bind", f"esc:transform:[ \"$FZF_PROMPT\" = '{NEW_PROMPT}' ] "
                  f"&& echo '{SEARCH_MODE}' || echo abort",
        "--bind", f"ctrl-o:become({self_cmd} --window-path {{3}})",
        "--bind", f"ctrl-x:transform({self_cmd} --trash-path {{3}})",
        "--bind", "ctrl-/:toggle-preview",
    ]
    # sized here, while stdout is still the terminal
    fzf = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
    fzf.communicate("\n".join(entries()) + "\n")
