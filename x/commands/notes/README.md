# notes

**What it does:** Opens journal notes in the terminal using `batcat` with Markdown syntax highlighting. Shows today's note by default, with flags to browse other entries. With `--edit`, opens the same file in `$VISUAL` / `$EDITOR` (fallback `vi`) instead, creating it if needed.

**Usage:**
```bash
x notes              # open today's note (YYYY-MM-DD.md)
x notes --last       # open the most recently created note
x notes --tasks      # open the tasks file (tasks.md)
x notes -t -e        # edit the tasks file by hand (created if missing)
x notes -e           # edit today's note
x notes -l -e        # edit the last note
```

`tasks.md` is backed up with the dated notes by `x sync --journal`: on a new machine,
`x sync --restore --journal` brings it back.

**Dependencies:**
- `batcat` — syntax-highlighted file viewer
- `~/documents/journal/` — directory containing dated `.md` notes

**Manual test:**
```bash
x notes              # should show today's note or "No note for today"
x notes --last       # should show the last dated note
x notes --tasks      # should show ~/documents/journal/tasks.md
VISUAL="echo EDIT" x notes -t -e   # should print EDIT …/tasks.md
```
