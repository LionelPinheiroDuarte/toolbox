# notes

**What it does:** Opens journal notes in the terminal using `batcat` with Markdown syntax highlighting. Shows today's note by default, with flags to browse other entries. With `--edit`, opens the same file in `$VISUAL` / `$EDITOR` (fallback `vi`) instead, creating it if needed. With `--browse`, lists the whole journal in fzf to open, create and trash notes — meant for a tmux popup.

**Usage:**
```bash
x notes              # open today's note (YYYY-MM-DD.md)
x notes --last       # open the most recently created note
x notes --tasks      # open the tasks file (tasks.md)
x notes -t -e        # edit the tasks file by hand (created if missing)
x notes -e           # edit today's note
x notes -l -e        # edit the last note
x notes --browse     # browse the whole journal in fzf (-b)
```

## Browsing

`x notes --browse` lists the journal in three groups — the task file, the
dated notes (newest first, titled by their summary) and the topic notes of
`notes/` (most recently changed first, with their project and tags) — with
the note rendered by batcat on the right. The search covers the full title,
project and tags, even where the row cuts them.

| Key | Action |
|-----|--------|
| `enter` | Edit the note in `$VISUAL` / `$EDITOR`, then back to the list |
| `ctrl-o` | Edit it in a new tmux window `note:<name>`, the popup closes |
| `ctrl-n` | Empty search: today's note. Otherwise `notes/<search as slug>.md`, with the journal agent's header. An existing note is opened, never overwritten |
| `ctrl-x` | Move the note to the desktop trash with `gio trash` (`~/.local/share/Trash/files/`, restorable from the file manager). `tasks.md` is never trashed |
| `ctrl-/` | Show or hide the preview |

`tasks.md` is listed before it exists and created empty the first time it is opened.

In tmux (dotfiles' `.tmux.conf`), `prefix N` opens it in a popup:

```tmux
bind N display-popup -E -w 80% -h 70% "~/.local/bin/x notes --browse"
```

fzf runs the actions by calling `x notes` back with hidden options
(`--list-entries`, `--open-path`, …): see `browse.py`. The logic they share
with the tests — listing, headers, creating, trashing — is in `store.py`.
`X_JOURNAL_DIR` points everything at another folder (tests, demos).

`tasks.md` is backed up with the dated notes by `x sync --journal`: on a new machine,
`x sync --restore --journal` brings it back.

**Dependencies:**
- `batcat` — syntax-highlighted file viewer
- `fzf` >= 0.66 — for `--browse`
- `gio` (GLib) — the trash, for `--browse`
- `~/documents/journal/` — directory containing dated `.md` notes

**Manual test:**
```bash
x notes              # should show today's note or "No note for today"
x notes --last       # should show the last dated note
x notes --tasks      # should show ~/documents/journal/tasks.md
VISUAL="echo EDIT" x notes -t -e   # should print EDIT …/tasks.md

# browser, on a copy of the journal
cp -r ~/documents/journal /tmp/journal-copy
X_JOURNAL_DIR=/tmp/journal-copy x notes --browse
#   type a word, ctrl-n          → vi on notes/<word>.md, then the note in NOTES
#   enter on a note, :q          → back on the same note
#   ctrl-x on tasks.md           → "tasks.md ne part jamais à la corbeille"
#   ctrl-o (inside tmux)         → a new window note:<name>, popup closed
```

**Tests:**
```bash
pipx inject toolbox pytest
~/.local/share/pipx/venvs/toolbox/bin/python -m pytest
```
