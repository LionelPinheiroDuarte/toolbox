"""x keys: my tmux shortcuts, read from tmux itself.

The source of truth is ~/.tmux.conf: a binding shows up here when it has a
note (`bind -N "..."`). Bindings sharing a note are shown on one line
(`h j k l  Select pane`), and a binding with no note stays out of the list,
which is how aliases (`\\` next to `|`) are kept quiet.

tmux's own bindings carry notes too. They are told apart by asking a
throwaway server started with no config (`-f /dev/null`) for its notes: what
the real server has beyond those is mine.
"""
import os
import shutil
import subprocess

from x.utils.colors import BOLD, ORANGE, RESET, error, info

# (table, heading): root holds the bindings that need no prefix
TABLES = (("prefix", None), ("root", "without prefix"))

CONFIG = os.path.expanduser("~/.tmux.conf")

# a separate socket, so the throwaway servers never touch the real one
_SCRATCH_SOCKET = "x-keys"


def _tmux(args, scratch_config=None):
    """Run tmux and return its output, or None if it failed.

    With scratch_config, the commands run in a throwaway server started from
    that config, which exits on its own once they are done (it has no
    session to keep it alive).
    """
    cmd = ["tmux"]
    if scratch_config is not None:
        cmd += ["-L", _SCRATCH_SOCKET, "-f", scratch_config, "start-server", ";"]
    result = subprocess.run(cmd + args, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout


def parse(output):
    """`list-keys -N` output -> [(key, note)], in tmux's order."""
    pairs = []
    for line in output.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            pairs.append((parts[0], parts[1].strip()))
    return pairs


def group(pairs):
    """Merge the keys sharing a note: [(["h", "j"], note)], first-seen order."""
    groups = {}
    for key, note in pairs:
        groups.setdefault(note, []).append(key)
    return [(keys, note) for note, keys in groups.items()]


def in_config_order(groups, config):
    """Sort the groups by where their note first appears in the config text,
    so the list reads like the file; a note not found there goes last."""
    def position(item):
        found = config.find(f'"{item[1]}"')
        return found if found >= 0 else len(config)
    return sorted(groups, key=position)


def custom(pairs, defaults):
    """The pairs that are not one of tmux's own bindings, unchanged."""
    defaults = set(defaults)
    return [pair for pair in pairs if pair not in defaults]


def render(sections, prefix):
    """[(heading, groups)] -> the text to print, keys aligned across sections."""
    sections = [(heading, groups) for heading, groups in sections if groups]
    if not sections:
        return info("No tmux binding has a note: add one with bind -N \"...\".")
    width = max(len(" ".join(keys)) for _, groups in sections for keys, _ in groups)
    lines = [f"{BOLD}tmux shortcuts{RESET}  {info(f'prefix {prefix}')}"]
    for heading, groups in sections:
        lines.append("")
        if heading:
            lines.append(info(heading))
        for keys, note in groups:
            lines.append(f"  {ORANGE}{' '.join(keys).ljust(width)}{RESET}  {note}")
    return "\n".join(lines)


def _query(scratch_config=None):
    """{table: [(key, note)]} and the prefix, from one tmux server.

    One tmux call per table: their outputs can't be told apart in a single
    call (an empty table prints nothing). A throwaway server costs ~15 ms.
    """
    prefix = _tmux(["show-options", "-gv", "prefix"], scratch_config)
    if prefix is None:
        return None, None
    tables = {}
    for table, _ in TABLES:
        output = _tmux(["list-keys", "-N", "-T", table], scratch_config)
        # a table with no binding at all is an error for tmux, not a failure
        tables[table] = parse(output or "")
    return tables, prefix.strip()


def run(show_all=False):
    if shutil.which("tmux") is None:
        print(error("tmux is not installed."))
        raise SystemExit(1)

    mine, prefix = _query()
    if mine is None:
        # no server running (outside tmux): read the config in a throwaway one
        mine, prefix = _query(CONFIG)
    defaults, _ = _query("/dev/null")
    if mine is None or defaults is None:
        print(error("Could not read the bindings from tmux."))
        raise SystemExit(1)

    try:
        with open(CONFIG) as f:
            config = f.read()
    except OSError:
        config = ""
    sections = []
    for table, heading in TABLES:
        pairs = custom(mine.get(table, []), defaults.get(table, []))
        sections.append((heading, in_config_order(group(pairs), config)))
    if show_all:
        # tmux's own, minus the ones my config replaced
        for table, heading in TABLES:
            still_bound = set(mine.get(table, []))
            kept = [p for p in defaults.get(table, []) if p in still_bound]
            title = "tmux defaults" + (f" ({heading})" if heading else "")
            sections.append((title, group(kept)))
    print(render(sections, prefix))
