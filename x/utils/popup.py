"""Shared by the `x claude projects` and `x claude edits` popups, so they
look and behave alike: palette, $GITHUB, ages, the fzf version check and the
fzf options of their grouped lists.

Their fzf input lines are "<header>\\t<row>\\t<key>…": only <row> is
searched (--nth 2), so group headers drop out as soon as a query is typed,
and headers have no <key> ({3}): the cursor steps over them and enter
ignores them.
"""
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

# palette (see the design README in Documents/Design/Claude tools)
DIM = "\033[38;2;139;147;163m"
ORG = "\033[38;2;240;164;93m"
GRN = "\033[38;2;140;201;143m"
RED = "\033[38;2;239;143;143m"
BLU = "\033[38;2;130;170;255m"
PRP = "\033[38;2;195;166;255m"
YLW = "\033[38;2;229;192;123m"
BOLD = "\033[1m"
OFF = "\033[0m"
KEY = "\033[48;2;90;98;115m\033[38;2;214;217;223m"
# badges: dark bold text on an accent background
ON_DARK = "\033[38;2;27;29;35m\033[1m"
BG_ORG = "\033[48;2;240;164;93m" + ON_DARK
BG_GRN = "\033[48;2;140;201;143m" + ON_DARK
BG_BLU = "\033[48;2;130;170;255m" + ON_DARK

HOME = os.path.expanduser("~")
STATE_DIR = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local", "state"),
                         "claude")
FZF_MIN = (0, 66)  # --footer (0.63) and --gutter (0.66) are the newest options used

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def github_dir():
    """$GITHUB, with the dotfiles' fallback: ~/Repos/github, else ~/repos/github."""
    d = os.environ.get("GITHUB") or os.path.join(HOME, "Repos", "github")
    alt = os.path.join(HOME, "repos", "github")
    if not os.path.isdir(d) and os.path.isdir(alt):
        return alt
    return d


def tilde(path):
    """<path> with $HOME shown as ~."""
    if path == HOME or path.startswith(HOME + "/"):
        return "~" + path[len(HOME):]
    return path


def plain(text):
    """<text> without its colours, to measure it."""
    return _ANSI.sub("", text)


def ago(epoch, now=None):
    """"< 1 min", "4 min", "2 h", "hier", "3 j", "2 sem", "1 mois", "3 ans"
    since <epoch>; "" without one."""
    if epoch in (None, ""):
        return ""
    age = (now or time.time()) - int(epoch)
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


def since(epoch, now=None):
    """The same as a phrase: "à l'instant", "hier", "il y a 4 min"."""
    a = ago(epoch, now)
    if a == "< 1 min":
        return "à l'instant"
    if a == "hier":
        return a
    return f"il y a {a}"


def plural(n, word):
    return f"{n} {word}{'s' if n > 1 else ''}"


def run(*cmd, cwd=None):
    """stdout of <cmd>, stripped of its final newline; None when it fails or
    is missing."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    except OSError:
        return None
    return r.stdout.rstrip("\n") if r.returncode == 0 else None


def tmux(*args):
    """tmux <args>, quiet; True when it succeeded."""
    try:
        return subprocess.run(["tmux", *args], capture_output=True).returncode == 0
    except OSError:
        return False


def wait_key():
    """Keep a popup open until a key is pressed, so its message can be read."""
    try:
        import termios
        import tty
        with open("/dev/tty", "rb", buffering=0) as t:
            old = termios.tcgetattr(t)
            try:
                tty.setraw(t)
                t.read(1)
            finally:
                termios.tcsetattr(t, termios.TCSADRAIN, old)
    except (OSError, ImportError):
        pass


def fzf_version():
    out = run("fzf", "--version")
    try:
        return tuple(int(x) for x in out.split()[0].split(".")[:2])
    except (AttributeError, IndexError, ValueError):
        return None


def require_fzf(command):
    """Stop with a message when fzf is older than the popups need."""
    version = fzf_version()
    if version and version >= FZF_MIN:
        return
    found = ".".join(map(str, version)) if version else "aucun"
    print(f"{command} a besoin de fzf >= 0.66 (installé : {found}).")
    print("Lance le playbook dotfiles : ansible-playbook -i inventory.ini playbook.yml --tags fzf -K")
    wait_key()
    sys.exit(1)


def self_command(*sub):
    """How fzf calls a command back: the same x, by absolute path."""
    return " ".join([shlex.quote(os.path.abspath(sys.argv[0])), *sub])


def info_command(path):
    """The fzf --info-command of a grouped list: a prefix, then "6/14", the
    group headers counted out. <path> holds the header count on its first
    line and the prefix on the second, both written with the list: plain
    shell here, no Python start-up on every key."""
    f = shlex.quote(path)
    return (f'h=$(head -1 {f} 2>/dev/null); h=${{h:-0}}; m=$FZF_MATCH_COUNT; '
            f'[ -z "$FZF_QUERY" ] && m=$((m - h)); '
            f'printf "%s%s/%s\\n" "$(sed -n 2p {f} 2>/dev/null)" "$m" "$((FZF_TOTAL_COUNT - h))"')


def write_info(path, headers, prefix):
    if path:
        with open(path, "w") as f:
            f.write(f"{headers}\n{prefix}\n")


def preview_columns():
    return int(os.environ.get("FZF_PREVIEW_COLUMNS") or 80)


def terminal_columns(default=100):
    """Width of the terminal the popup runs in, even with stdout piped."""
    try:
        with open("/dev/tty") as t:
            return os.get_terminal_size(t.fileno()).columns
    except OSError:
        return shutil.get_terminal_size((default, 24)).columns


def popup_fzf_opts(accent, label, ghost):
    """The fzf options both popups share."""
    return [
        "--ansi", "--layout=reverse", "--delimiter", "\t", "--with-nth", "1,2", "--nth", "2",
        "--tabstop", "1",
        "--border=rounded", "--border-label", f" {label} ", "--border-label-pos=3",
        "--input-border=line", "--footer-border=line",
        "--prompt", "❯ ", "--ghost", ghost, "--info=inline-right", "--no-separator",
        "--pointer", "▌", "--gutter", " ", "--highlight-line", "--no-scrollbar",
        "--color", f"bg+:#2c313c,fg+:#d6d9df,pointer:{accent},hl:{accent},hl+:{accent}",
        "--color", f"border:#5a6273,label:{accent}:bold,prompt:{accent},info:#d6d9df,ghost:#5a6273",
        "--color", "input-border:#5a6273,footer-border:#5a6273,preview-border:#5a6273",
        "--bind", "change:first", "--bind", "result:transform([ -n {3} ] || echo down)",
        "--bind", "down:down+transform([ -n {3} ] || echo down)",
        "--bind", "up:up+transform([ -n {3} ] || { [ $FZF_POS -le 1 ] && echo down || echo up; })",
        "--bind", "enter:transform([ -n {3} ] && echo accept)",
        "--bind", "ctrl-/:toggle-preview",
    ]


def fzf(lines, opts):
    """Run fzf on <lines>; its output (what it prints on accept, and what a
    become() prints) or "" when aborted."""
    p = subprocess.run(["fzf", *opts], input="".join(l + "\n" for l in lines),
                       stdout=subprocess.PIPE, text=True)
    return p.stdout
