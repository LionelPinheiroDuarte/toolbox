"""`x claude projects`: one tmux session per project, each with Claude Code
running in it. Pick a project, jump to its session (created on the fly), and
get them all back after a reboot with Claude resuming its last conversation.
Meant to run in a tmux popup (see dotfiles' .tmux.conf), but every command
also works from a shell.

A project session has two windows: "claude" (claude in the repo) and
"shell". Sessions created here carry the @claude_project option (their
directory), which is how they are told apart from other tmux sessions.

Claude's state: hooks in dotfiles' settings.json call `state` from inside the
pane where Claude runs, which sets @claude_state on its session (and
@claude_state_at, when it changed). Running when a prompt is sent, done when
Claude has answered, cleared when Claude exits or when you switch to the
session (the tmux hook in .tmux.conf). The status bar shows the same marks
for the other sessions.

Saved list: one "name<TAB>dir" line per project. It is rewritten when a
project is opened or killed from here, and by `save`. Not on tmux's own
session-closed hook: when the server dies (logout, reboot) every session
closes, and the hook would empty the list right before it is needed.

fzf calls this command back for the list (`entries`, on ctrl-x's reload) and
the preview (`preview <dir> <name> <kind>`). Its input is one line per
project under a header line per group:

    <header>\\t<row>\\t<dir>\\t<session name>\\t<kind>
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import time

from x.utils.popup import (BG_GRN, BG_ORG, BLU, BOLD, DIM, GRN, HOME, KEY, OFF, ORG, PRP, RED,
                           STATE_DIR, YLW, ago, fzf, github_dir, info_command, plain, plural,
                           popup_fzf_opts, preview_columns, require_fzf, run, self_command,
                           tilde, tmux, write_info)

SAVED = os.path.join(STATE_DIR, "projects.tsv")
OPEN_KINDS = ("running", "done", "open")


def session_name(d):
    """tmux refuses "." and ":" in session names. ~ is the session without a
    project, "home" (the name the dotfiles' `home` script gives it)."""
    if d == HOME:
        return "home"
    return os.path.basename(d.rstrip("/")).replace(".", "_").replace(":", "_")


def _sessions(fmt, fields):
    """One list per tmux session, from <fmt>'s "|"-separated fields: read
    would collapse a run of tabs and tmux escapes control characters. The
    last field may hold a "|" (a directory)."""
    out = run("tmux", "list-sessions", "-F", fmt) or ""
    return [line.split("|", fields - 1) for line in out.splitlines() if line.count("|") >= fields - 1]


def open_projects():
    """(name, dir) of every open project session."""
    return [(s, d) for s, d in _sessions("#{session_name}|#{@claude_project}", 2) if d]


def saved_projects():
    try:
        with open(SAVED) as f:
            return [tuple(line.rstrip("\n").split("\t", 1)) for line in f if "\t" in line]
    except OSError:
        return []


def save():
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(SAVED + ".tmp", "w") as f:
        f.writelines(f"{n}\t{d}\n" for n, d in open_projects())
    os.replace(SAVED + ".tmp", SAVED)


def set_state(state):
    """Claude's state on the session of the pane it runs in. An answer you
    are already looking at (session attached, Claude's window in front) is
    not marked. Silent, and a no-op outside tmux: hooks must not print or
    fail."""
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return
    try:
        if state == "done" and run("tmux", "display-message", "-p", "-t", pane,
                                   "#{&&:#{session_attached},#{window_active}}") == "1":
            state = "none"
        if state in ("running", "done"):
            # the age shown in the popup counts from the last change of state
            if run("tmux", "show-options", "-qv", "-t", pane, "@claude_state") != state:
                tmux("set-option", "-t", pane, "@claude_state_at", str(int(time.time())))
            tmux("set-option", "-t", pane, "@claude_state", state)
        elif state == "none":
            tmux("set-option", "-t", pane, "-u", "@claude_state")
            tmux("set-option", "-t", pane, "-u", "@claude_state_at")
    except Exception:  # noqa: BLE001 - a hook never fails
        pass


def go_to(name, window=None):
    """Switch this client when inside tmux, attach otherwise. With a window
    name, land on that window."""
    target = f"={name}" + (f":{window}" if window else "")
    verb = "switch-client" if os.environ.get("TMUX") else "attach"
    subprocess.run(["tmux", verb, "-t", target])


def create(d, mode="new"):
    """The session for <d>, unless it exists. With "continue", Claude resumes
    the directory's last conversation (falls back to a new one when there is
    none). The pane drops to a shell when Claude exits, so the window stays
    open."""
    name = session_name(d)
    if tmux("has-session", "-t", f"={name}"):
        # a home session opened by the `home` script has no @claude_project: adopt it
        if d == HOME:
            tmux("set-option", "-t", name, "@claude_project", d)
        return
    cmd = "claude --continue || claude" if mode == "continue" else "claude"
    tmux("new-session", "-d", "-s", name, "-c", d, "-n", "claude", f"{cmd}; exec $SHELL")
    # set-option takes no "=" exact-match prefix; the name was just created
    tmux("set-option", "-t", name, "@claude_project", d)
    tmux("new-window", "-d", "-t", f"={name}:", "-c", d, "-n", "shell")


def open_project(path, window=None):
    d = os.path.realpath(path)
    if not os.path.isdir(d):
        sys.exit(f"Not a directory: {path}")
    mode = "continue" if any(sd == d for _, sd in saved_projects()) else "new"
    create(d, mode)
    save()
    go_to(session_name(d), window)


def new_project(name):
    """A new repo under $GITHUB, opened like any other; an existing one is
    just opened."""
    name = re.sub(r"[^A-Za-z0-9._-]", "-", name or "").strip("-")
    if not name:
        sys.exit("Usage: x claude projects new <name>")
    d = os.path.join(github_dir(), name)
    if not os.path.isdir(d):
        os.makedirs(d)
        if subprocess.run(["git", "-C", d, "init", "-q"]).returncode:
            sys.exit(1)
    open_project(d)


def restore():
    saved = saved_projects()
    if not saved:
        print(f"No saved projects ({SAVED}).")
        return
    first = None
    for name, d in saved:
        if not os.path.isdir(d):
            print(f"skip {name}: {d} is gone")
            continue
        create(d, "continue")
        first = first or session_name(d)
        print(f"restored {name}")
    if first:
        go_to(first)


def kill_project(name):
    if not name or not tmux("has-session", "-t", f"={name}"):
        return
    # don't pull the client out of tmux: leave the session first if it is ours
    if os.environ.get("TMUX") and run("tmux", "display-message", "-p", "#S") == name:
        if not tmux("switch-client", "-l"):
            tmux("switch-client", "-n")
    if tmux("kill-session", "-t", f"={name}"):
        save()


# --- git -------------------------------------------------------------------

def repo_status(d):
    """{branch, ahead, behind ("" without an upstream), dirty (files)} for
    <d>, in one git call; None outside a repo."""
    out = run("git", "-C", d, "status", "--porcelain=v2", "--branch")
    if out is None:
        return None
    st = {"branch": "", "ahead": "", "behind": "", "dirty": 0}
    for line in out.splitlines():
        if line.startswith("# branch.head "):
            st["branch"] = line.split()[2]
        elif line.startswith("# branch.ab "):
            _, _, a, b = line.split()
            st["ahead"], st["behind"] = a[1:], b[1:]
        elif line and not line.startswith("#"):
            st["dirty"] += 1
    return st


def repo_head(d):
    """(branch, epoch of the last commit) for <d>, in one git call; the
    branch falls back to symbolic-ref in a repo with no commit yet."""
    out = run("git", "-C", d, "log", "-1", "--format=%ct%x09%D") or ""
    committed, _, refs = out.partition("\t")
    m = re.match(r"HEAD -> ([^,]*)", refs)
    branch = m.group(1) if m else run("git", "-C", d, "symbolic-ref", "--short", "-q", "HEAD") or ""
    return branch, committed


# --- the list --------------------------------------------------------------

GROUPS = {"running": "SESSIONS OUVERTES", "done": "SESSIONS OUVERTES", "open": "SESSIONS OUVERTES",
          "other": "AUTRES SESSIONS TMUX", "saved": "À RESTAURER", "home": "SANS PROJET"}


def _row(kind, name, d, at=""):
    """One project. Its changes, "±3 ↑2" (modified files, commits not
    pushed), only for open and saved projects: git status on every repo
    would slow the popup."""
    branch, changes, committed = "", "", ""
    if kind in ("repo", "home"):
        branch, committed = repo_head(d)
    elif kind != "other":
        st = repo_status(d)
        if st:
            branch = st["branch"]
            parts = []
            if st["dirty"]:
                parts.append(f"±{st['dirty']}")
            if st["ahead"] not in ("", "0"):
                parts.append(f"↑{st['ahead']}")
            changes = " ".join(parts) or "·"
            if not at:
                branch, at = repo_head(d)
    return {"kind": kind, "name": name, "dir": d, "branch": branch, "changes": changes,
            "age": ago(at or committed)}


def projects():
    """Every row, in the list's order."""
    rows, seen = [], set()

    def add(*args):
        r = _row(*args)
        rows.append(r)
        # another session only borrows its directory: the project there still
        # gets its own row
        if r["kind"] != "other":
            seen.add(r["dir"])

    # open sessions, Claude working or answered first
    rank = {"running": 0, "done": 1}
    opened = [f for f in _sessions("#{@claude_state}|#{@claude_state_at}|#{session_activity}"
                                   "|#{session_name}|#{@claude_project}", 5) if f[4]]
    for st, at, act, s, d in sorted(opened, key=lambda f: rank.get(f[0], 2)):
        add(st or "open", s, d, at or act)

    # other tmux sessions (no @claude_project), most recently used first.
    # "home" is left out: the row without a project below stands for it.
    others = [f for f in _sessions("#{session_activity}|#{session_name}|#{@claude_project}"
                                   "|#{session_path}", 4) if not f[2] and f[1] != "home"]
    for act, s, _, d in sorted(others, key=lambda f: -int(f[0] or 0)):
        add("other", s, d, act)

    for s, d in saved_projects():
        if d not in seen and os.path.isdir(d):
            add("saved", s, d)

    # no project: Claude in ~ (global CLAUDE.md only), while it is neither
    # open nor saved
    if HOME not in seen:
        add("home", "home", HOME)

    gh = github_dir()
    try:
        repos = sorted(e.path for e in os.scandir(gh) if e.is_dir())
    except OSError:
        repos = []
    for d in repos:
        if d not in seen:
            add("repo", session_name(d), d)
    return rows


MARKS = {
    "running": (f"{ORG}⟳{OFF}", ORG, OFF), "done": (f"{GRN}✓{OFF}", BOLD, OFF),
    "open": (f"{BLU}●{OFF}", DIM, OFF), "saved": (f"{PRP}↺{OFF}", "", ""),
    "home": (f"{DIM}◇{OFF}", "", ""), "other": (f"{DIM}○{OFF}", DIM, OFF), "repo": (" ", "", ""),
}


def entries(info_path=None):
    """The fzf input lines. Also writes the header count and the counter's
    prefix (what is open) to <info_path>, for the info line."""
    rows = projects()
    # column widths from the data, capped so the row fits the list pane
    wn = min(max([4] + [len(r["name"]) for r in rows]), 20)
    wb = min(max([4] + [len(r["branch"]) for r in rows]), 14)
    wc = max([1] + [len(r["changes"]) for r in rows])

    lines, group, headers = [], None, 0
    counts = {"active": 0, "open": 0, "saved": 0}
    for r in rows:
        g = GROUPS.get(r["kind"], f"DÉPÔTS {tilde(github_dir())}")
        if g != group:
            group, headers = g, headers + 1
            lines.append(f"{DIM}{g}{OFF}\t\t\t\t")
        mark, before, after = MARKS[r["kind"]]
        if r["kind"] in ("running", "done"):
            counts["active"] += 1
        elif r["kind"] in ("open", "saved"):
            counts[r["kind"]] += 1
        nm = f"{before}{r['name']:<{wn}.{wn}}{after}"
        lines.append(f"\t{mark} {nm}  {DIM}{r['branch']:<{wb}.{wb}}{OFF}  "
                     f"{YLW}{r['changes']:<{wc}}{OFF}  {DIM}{r['age']:>7}{OFF}"
                     f"\t{r['dir']}\t{r['name']}\t{r['kind']}")

    # next to the prompt: only what is there, to leave room for the count
    words = [(counts["active"], "actif"), (counts["open"], "ouvert"), (counts["saved"], "sauvegardé")]
    prefix = "".join(f"{plural(n, w)} · " for n, w in words if n)
    write_info(info_path, headers, f"{DIM}{prefix}{OFF}")
    return lines


# --- the preview -----------------------------------------------------------

def _tail(path, n, block=1 << 16):
    """The last <n> lines of <path>, read from the end: transcripts grow to
    tens of MB."""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        pos, data = f.tell(), b""
        while pos > 0 and data.count(b"\n") <= n:
            step = min(block, pos)
            pos -= step
            f.seek(pos)
            data = f.read(step) + data
    return data.decode("utf-8", "replace").splitlines()[-n:]


def _text(msg):
    content = (msg.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content
                        if isinstance(c, dict) and c.get("type") == "text")
    return ""


def last_exchange(d):
    """(last prompt, start of Claude's answer to it) from the newest
    transcript of <d>, or None. That format is internal to Claude Code: if
    reading it fails, the section is just left out."""
    folder = os.path.join(HOME, ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", d))
    try:
        transcripts = [e for e in os.scandir(folder) if e.name.endswith(".jsonl")]
        newest = max(transcripts, key=lambda e: e.stat().st_mtime).path
        lines = _tail(newest, 400)
    except (OSError, ValueError):
        return None
    msgs = []
    # tool results make most of the transcript's size: keep the messages only
    for line in lines:
        if len(line) >= 20000 or not re.search(r'"type":"(user|assistant)"', line):
            continue
        try:
            msgs.append(json.loads(line))
        except ValueError:
            continue

    def is_prompt(m):
        t = _text(m)
        return m.get("type") == "user" and not m.get("isMeta") and t and not t.startswith("<")

    asked = [i for i, m in enumerate(msgs) if is_prompt(m)]
    if not asked:
        return None
    p = asked[-1]
    answers = [t for m in msgs[p + 1:] if m.get("type") == "assistant" for t in [_text(m)] if t]
    squash = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
    return squash(_text(msgs[p])), squash(answers[-1]) if answers else ""


def preview(d, name, kind):
    """A card with Claude's state, the repo's state, the last exchange with
    Claude and the last commits. <kind> comes from the row; only the live
    state of an open session is asked to tmux."""
    if not d:
        return
    cols = preview_columns()
    out = []

    windows, badge = "", ""
    if kind in OPEN_KINDS:
        info = run("tmux", "display-message", "-p", "-t", f"={name}:",
                   "#{@claude_state}|#{@claude_state_at}|#{W:#{window_name} · }") or "||"
        state, at, windows = (info.split("|", 2) + ["", ""])[:3]
        if windows.endswith(" · "):
            windows = windows[:-3]
        age = f" · {ago(at)}" if at else ""
        if state == "running":
            badge = f"{BG_ORG} ⟳ travaille{age} {OFF}"
        elif state == "done":
            badge = f"{BG_GRN} ✓ a répondu{age} {OFF}"
        else:
            badge = f"{BLU}● ouvert{OFF}"
    else:
        badge = {"saved": f"{PRP}↺ sauvegardé{OFF}", "home": f"{DIM}◇ sans projet{OFF}",
                 "other": f"{DIM}○ session tmux{OFF}"}.get(kind, "")
    pad = max(cols - len(name) - len(plain(badge)) - 1, 1)
    out.append(f"{BOLD}{name}{OFF}{' ' * pad}{badge}")
    out.append(f"{DIM}{tilde(d)}{OFF}")

    # not a project: its windows and what runs in them, nothing about git or
    # Claude (its directory is often ~, whose transcripts are not its own)
    if kind == "other":
        out += ["", f"{DIM}FENÊTRES{OFF}"]
        listing = run("tmux", "list-windows", "-t", f"={name}", "-F",
                      "#{window_index}|#{window_name}|#{pane_current_command}|#{?window_active,●,}")
        for line in (listing or "").splitlines():
            idx, wname, cmd, act = (line.split("|", 3) + [""] * 3)[:4]
            out.append(f"{YLW}{idx}{OFF} {wname}  {DIM}{cmd}{OFF} {BLU}{act}{OFF}")
        out += ["", f"{DIM}{KEY} ^X {OFF}{DIM} pour la fermer{OFF}"]
        print("\n".join(out))
        return

    st = repo_status(d)
    if st:
        line = f"{DIM}⎇ {st['branch']}{OFF}"
        if st["ahead"]:
            line += f"  {GRN}↑{st['ahead']}{OFF} {RED}↓{st['behind']}{OFF}"
        if st["dirty"]:
            line += f"  {YLW}±{st['dirty']} modifié{'s' if st['dirty'] > 1 else ''}{OFF}"
        else:
            line += f"  {DIM}arbre propre{OFF}"
        if windows:
            line += f"  {DIM}fenêtres : {OFF}{windows}"
        out.append(line)

    exchange = last_exchange(d)
    if exchange:
        prompt, answer = exchange
        out += ["", f"{DIM}DERNIER ÉCHANGE{OFF}", f"{ORG}›{OFF} {DIM}{prompt[:cols - 2]}{OFF}"]
        out += textwrap.wrap(answer, cols)[:4]

    commits = run("git", "-C", d, "log", "-5", "--format=%h%x09%ct%x09%s")
    if commits:
        out += ["", f"{DIM}DERNIERS COMMITS{OFF}"]
        for c in commits.splitlines():
            h, ts, subject = (c.split("\t", 2) + ["", ""])[:3]
            out.append(f"{YLW}{h}{OFF} {DIM}{subject[:max(cols - 20, 0)]}{OFF} {ago(ts)}")
    print("\n".join(out))


# --- the popup -------------------------------------------------------------

def pick():
    require_fzf("x claude projects")
    me = self_command("claude", "projects")
    fd, info_path = tempfile.mkstemp(prefix="x-claude-projects.")
    os.close(fd)
    os.environ["X_CLAUDE_PROJECTS_INFO"] = info_path  # for ctrl-x's reload
    footer = (f"{KEY} ⏎ {OFF} ouvrir   {KEY} ^X {OFF} fermer   {KEY} ^N {OFF} nouveau\n"
              f"{KEY} ^R {OFF} tout restaurer   {KEY} ^S {OFF} shell   {KEY} ^/ {OFF} aperçu\n"
              f"{ORG}⟳{OFF} travaille  {GRN}✓{OFF} a répondu  {BLU}●{OFF} ouvert  "
              f"{PRP}↺{OFF} sauvegardé  {DIM}○{OFF} autre session")
    try:
        # --expect: the first output line is "ctrl-s" (go to the shell
        # window) or empty (enter)
        out = fzf(entries(info_path), [
            *popup_fzf_opts("#f0a45d", "◆ projets claude", "chercher un projet"),
            "--footer", footer, "--expect", "ctrl-s",
            "--info-command", info_command(info_path),
            "--preview-window", "right,55%,border-left",
            "--preview", f"{me} preview {{3}} {{4}} {{5}}",
            "--bind", f"ctrl-x:execute-silent([ -n {{3}} ] && {me} kill {{4}})+reload({me} entries)",
            "--bind", f"ctrl-n:transform:[ -n {{q}} ] && echo \"become({me} new {{q}})\"",
            "--bind", f"ctrl-r:become({me} restore)",
        ])
    finally:
        os.unlink(info_path)
    lines = out.split("\n")
    key, row = lines[0], (lines[1] if len(lines) > 1 else "")
    fields = row.split("\t")
    if len(fields) < 5 or not fields[2]:
        return
    _, _, d, name, kind = fields[:5]
    # another session is just visited: opening its directory would make a
    # project session there
    if kind == "other":
        go_to(name)
        return
    open_project(d, "shell" if key else None)
