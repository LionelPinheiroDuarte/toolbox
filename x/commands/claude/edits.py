"""`x claude edits`: fuzzy-pick a file recently written by Claude Code, see
what Claude changed in it, and open it in Vim in a new tmux window. Meant to
run inside a tmux popup (see dotfiles' .tmux.conf).

The data comes from the log-edits hook (agents/hooks/log-edits/): files are
grouped by the Claude session that last touched them, newest first, deleted
files skipped. "Before" is the file as it was before Claude's first edit in
that session; "after" is the file on disk now.

fzf keeps the popup's state in two temp files, the view (diff or file,
ctrl-f) and the scope (a repo, or empty for all, ctrl-g), and calls this
command back for the list, the preview and the keys (see cli). Its input is
one line per file under a header line per session:

    <header>\\t<row>\\t<path>\\t<epoch>\\t<session>

No dependency beyond fzf (>= 0.66) and diff; bat is used for the file view
when present.
"""
import glob
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

from x.utils.popup import (BG_BLU, BLU, BOLD, DIM, GRN, HOME, KEY, OFF, PRP, RED, STATE_DIR, YLW,
                           ago, fzf, github_dir, info_command, popup_fzf_opts, preview_columns,
                           require_fzf, run, self_command, since, terminal_columns, wait_key,
                           write_info)

LOG = os.path.join(STATE_DIR, "edits.log")
SNAPSHOTS = os.path.join(STATE_DIR, "snapshots")
VIMSCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edits.vim")
PREVIEW_PCT = 58

ADD = "\033[48;2;35;51;40m\033[38;2;140;201;143m"
DEL = "\033[48;2;58;38;41m\033[38;2;239;143;143m"


def _read(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def _write(path, text):
    with open(path, "w") as f:
        f.write(text + "\n" if text else "")


def snapshot_dir(session, path):
    """Snapshot directory of <path> in <session> (may not exist)."""
    return os.path.join(SNAPSHOTS, session or "unknown", hashlib.sha1(path.encode()).hexdigest())


def _origs(d):
    return sorted(glob.glob(os.path.join(glob.escape(d), "*.orig")))


def before_at(d):
    """The "before" file kept in snapshot <d> ("/dev/null" if Claude created
    the file), or None if there is no snapshot."""
    if not os.path.isdir(d):
        return None
    if os.path.exists(os.path.join(d, "new")):
        return "/dev/null"
    origs = _origs(d)
    return origs[0] if origs else None


def short_path(f, base=None):
    """Path shown to the user: relative to <base> when given, else to
    $GITHUB or ~."""
    for root, lead in ((base, ""), (github_dir(), ""), (HOME, "~/")):
        if root and f.startswith(root + "/"):
            return lead + f[len(root) + 1:]
    return f


def render_path(p):
    """Dim directory, bold file name."""
    head, sep, name = p.rpartition("/")
    return f"{DIM}{head}{sep}{OFF}{BOLD}{name}{OFF}" if sep else f"{BOLD}{p}{OFF}"


def unified(before, after):
    """`diff -u` of <before> -> <after>, with the enclosing top-level line
    (function, class, import...) after each @@; "" when they match."""
    try:
        return subprocess.run(["diff", "-u", "-F", "^[[:alpha:]_$@]", before, after],
                              capture_output=True, text=True, errors="replace").stdout
    except OSError:
        return ""


def counts(u):
    """(added, deleted, hunks) in unified diff <u>."""
    lines = u.splitlines()[2:]
    return (sum(l.startswith("+") for l in lines), sum(l.startswith("-") for l in lines),
            sum(l.startswith("@@") for l in lines))


def logged():
    """(epoch, session, path) of every logged file, newest first; files
    grouped by the session that touched them last, groups ordered by their
    latest edit."""
    try:
        with open(LOG, errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    groups, seen = {}, set()
    for line in reversed(lines):
        parts = line.split("\t", 2)
        if len(parts) < 3 or parts[2] in seen:
            continue
        seen.add(parts[2])
        groups.setdefault(parts[1], []).append(parts)
    return [tuple(p) for g in groups.values() for p in g]


def _fit(p, width):
    """<p> in <width> columns: drop whole leading dirs, so the file name
    always stays readable."""
    if len(p) <= width:
        return p
    parts = p.split("/")
    while len(parts) > 1:
        parts = parts[1:]
        p = "…/" + "/".join(parts)
        if len(p) <= width:
            return p
    return "…" + p[-(width - 1):]


def entries(scope="", info_path=None):
    """The fzf input lines. Also writes the header count and the counter's
    prefix (scope badge, ctrl-g hint) to <info_path>, for the info line."""
    files = []
    for ts, sess, path in logged():
        if not os.path.isfile(path) or (scope and not path.startswith(scope + "/")):
            continue
        before = before_at(snapshot_dir(sess, path))
        added = deleted = None
        if before is None:
            sym = f"{DIM}?{OFF}"
        else:
            added, deleted, _ = counts(unified(before, path))
            if added + deleted == 0:
                sym = f"{DIM}↶{OFF}"
            elif before == "/dev/null":
                sym = f"{GRN}✚{OFF}"
            else:
                sym = f"{YLW}~{OFF}"
        files.append((ts, sess, path, sym, added, deleted))

    # path column: whatever the list pane leaves after the mark, stats and age
    room = max(int(os.environ.get("LIST_COLS") or 70) - 26, 20)
    shorts = [_fit(short_path(f[2], scope), room) for f in files]
    width = max([0] + [len(p) for p in shorts])

    lines, last, group = [], None, -1
    labels = ["DERNIÈRE SESSION", "SESSION PRÉCÉDENTE"]
    for (ts, sess, path, sym, added, deleted), p in zip(files, shorts):
        if sess != last:
            last, group = sess, group + 1
            label = labels[group] if group < len(labels) else "SESSION"
            lines.append(f"{DIM}{label} · {since(ts)}{OFF}\t\t\t\t")
        if added is None:
            stat = f"{DIM}{'sans diff':>11}{OFF}"
        elif added + deleted == 0:
            stat = f"{DIM}{'annulé':>11}{OFF}"
        else:
            minus = f"-{deleted}" if deleted else "·"
            stat = f"{GRN}{'+' + str(added):>5}{OFF} {RED}{minus:>5}{OFF}"
        lines.append(f"\t{sym} {render_path(p)}{' ' * (width - len(p))}  {stat}  "
                     f"{DIM}{ago(ts):>7}{OFF}\t{path}\t{ts}\t{sess}")

    if scope:
        prefix = f"{BG_BLU} {os.path.basename(scope)} {OFF}  {DIM}tous ^G{OFF}"
    else:
        prefix = f"{BLU}{BOLD}tous{OFF}  {DIM}dépôt ^G{OFF}"
    write_info(info_path, group + 1, f"{prefix}  {DIM}·{OFF}  ")
    return lines


# --- the preview -----------------------------------------------------------

def tabs(mode):
    """"diff · fichier" with the active view highlighted (ctrl-f)."""
    if mode == "file":
        return f"{DIM}diff{OFF} · {BLU}{BOLD}fichier{OFF}"
    return f"{BLU}{BOLD}diff{OFF} · {DIM}fichier{OFF}"


def show_file(path):
    bat = shutil.which("batcat") or shutil.which("bat")
    if bat:
        sys.stdout.flush()
        subprocess.run([bat, "--color=always", "--style=numbers", path])
        return []
    with open(path, errors="replace") as f:
        return [f"{DIM}{i:4d}{OFF}  {line.rstrip(chr(10))}" for i, line in enumerate(f, 1)]


def show_diff(u, width):
    """Unified diff <u> drawn for the preview: old and new line numbers,
    full-width background on added/removed lines, and the enclosing
    top-level line after each @@."""
    fill = lambda s: s + " " * max(width - len(s), 0)  # noqa: E731
    out, o, n = [], 0, 0
    for line in u.expandtabs(4).splitlines()[2:]:
        if line.startswith("@@"):
            f = line.split()
            a, b = f[1][1:].split(","), f[2][1:].split(",")
            o, n = int(a[0]), int(b[0])
            ctx = line.split("@@", 2)[2].lstrip(" ") if line.count("@@") >= 2 else ""
            out.append(f"{PRP}@@ {a[0]},{a[1] if len(a) > 1 else 1} → "
                       f"{b[0]},{b[1] if len(b) > 1 else 1} @@ {ctx}{OFF}")
        elif line.startswith("-"):
            out.append(f"{DEL}{fill(f'{o:4d}       - {line[1:]}')}{OFF}")
            o += 1
        elif line.startswith("+"):
            out.append(f"{ADD}{fill(f'     {n:4d}  + {line[1:]}')}{OFF}")
            n += 1
        elif line.startswith("\\"):
            out.append(f"{DIM}           {line[2:]}{OFF}")
        else:
            out.append(f"{DIM}{o:4d} {n:4d}    {line[1:]}{OFF}")
            o, n = o + 1, n + 1
    return out


def preview(path, ts, session, mode):
    if not path:
        return
    cols = preview_columns()
    # path on the left, tabs on the right, clear of fzf's scroll counter
    p = short_path(path)
    out = [f"{render_path(p)}{' ' * max(cols - len(p) - 24, 1)}{tabs(mode)}"]

    # one diff for the header's counts, the reverted check and the view
    d = snapshot_dir(session, path)
    before = before_at(d)
    u = unified(before, path) if before else ""
    added, deleted, hunks = counts(u)
    n = len(_origs(d))
    edits = f"{n} édition{'s' if n > 1 else ''}"

    edited = f"édité par Claude {since(ts)}"
    if not before:
        out.append(f"{DIM}{edited} · sans snapshot : édité avant l'enregistrement des diffs{OFF}")
    elif not u:
        out.append(f"{DIM}{edited} · annulé depuis : plus aucun changement · {edits}{OFF}")
    else:
        if before == "/dev/null":
            edits = "créé par Claude"
        out.append(f"{DIM}{edited} · {GRN}+{added} {RED}-{deleted}{DIM} · "
                   f"{hunks} bloc{'s' if hunks > 1 else ''} · {edits}{OFF}")
    out.append(f"{DIM}{'─' * cols}{OFF}")

    if mode == "file" or not before or before == "/dev/null":
        print("\n".join(out))
        rest = show_file(path)
    else:
        rest = show_diff(u, cols) if u else []
        rest = out + rest
    if rest:
        print("\n".join(rest))


# --- vim -------------------------------------------------------------------

def open_in_vim(path, before, *vim_args):
    """<path> in Vim in a new tmux window, with ,d ready to show Claude's
    diff. <vim_args> are passed to vim (e.g. -c ClaudeDiff to start in the
    diff)."""
    name = os.path.basename(path)
    if vim_args:
        name = f"diff:{name}"
    let = "let g:claude_before='{}'".format((before or "").replace("'", "''"))
    argv = ["vim", "-c", let, "-S", VIMSCRIPT, *vim_args, path]
    subprocess.run(["tmux", "new-window", "-c", os.path.dirname(path), "-n", name,
                    " ".join(shlex.quote(a) for a in argv)])


def vimdiff(path, session):
    before = before_at(snapshot_dir(session, path))
    if before:
        open_in_vim(path, before, "-c", "ClaudeDiff")


def toggle(mode_path):
    _write(mode_path, "diff" if _read(mode_path) == "file" else "file")


def flip_scope(scope_path, repo):
    """Between the repo and all sessions."""
    if _read(scope_path):
        _write(scope_path, "")
    elif repo:
        _write(scope_path, repo)


# --- the popup -------------------------------------------------------------

def browse(directory=None):
    require_fzf("x claude edits")
    if not os.path.isfile(LOG) or not os.path.getsize(LOG):
        print(f"Aucune édition enregistrée ({LOG}).")
        wait_key()
        return

    # the repo of <directory> (or of the current directory, for ctrl-g); the
    # list starts filtered only when <directory> is given
    repo = run("git", "-C", directory or os.getcwd(), "rev-parse", "--show-toplevel") or ""
    if not repo and directory:
        repo = os.path.realpath(directory)

    # the list pane's width, for the path column (inherited by ctrl-g's reload)
    os.environ["LIST_COLS"] = str(terminal_columns() * (100 - PREVIEW_PCT) // 100 - 4)

    me = self_command("claude", "edits")
    tmp = tempfile.mkdtemp(prefix="x-claude-edits.")
    mode, scope, info = (os.path.join(tmp, f) for f in ("mode", "scope", "info"))
    _write(mode, "diff")
    _write(scope, repo if directory else "")
    q = shlex.quote

    # footer, under the list: shortcuts, then the marks' legend (fzf draws it
    # in the list column, the preview keeps the full height)
    footer = (f"{KEY} ⏎ {OFF} vim   {KEY} ^D {OFF} vimdiff   {KEY} ^F {OFF} diff/fichier\n"
              f"{KEY} ^G {OFF} dépôt/tous   {KEY} ^Y {OFF} copier   {KEY} ^/ {OFF} aperçu\n"
              f"{GRN}✚{OFF} créé  {YLW}~{OFF} modifié  {DIM}↶{OFF} annulé  {DIM}?{OFF} sans diff")
    reload = f"reload({me} --list {q(scope)} {q(info)})"
    try:
        sel = fzf(entries(_read(scope), info), [
            *popup_fzf_opts("#82aaff", "✎ fichiers modifiés par claude", "chercher un fichier"),
            "--footer", footer, "--info-command", info_command(info),
            "--preview-window", f"right,{PREVIEW_PCT}%,border-left",
            "--preview", f"{me} --preview {{3}} {{4}} {{5}} \"$(cat {q(mode)})\"",
            "--bind", f"ctrl-f:execute-silent({me} --toggle {q(mode)})+refresh-preview",
            "--bind", f"ctrl-d:execute-silent([ -n {{3}} ] && {me} --vimdiff {{3}} {{5}})+abort",
            "--bind", f"ctrl-g:execute-silent({me} --scope {q(scope)} {q(repo)})+{reload}",
            "--bind", "ctrl-y:execute-silent([ -n {3} ] && tmux set-buffer -w -- {3} "
                      "&& tmux display-message 'chemin copié : '{3})",
        ])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    fields = sel.rstrip("\n").split("\t")
    if len(fields) < 5 or not fields[2]:
        return
    path, session = fields[2], fields[4]
    open_in_vim(path, before_at(snapshot_dir(session, path)))
