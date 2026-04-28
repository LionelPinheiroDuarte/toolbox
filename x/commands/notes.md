# notes

**What it does:** Opens journal notes in the terminal using `batcat` with Markdown syntax highlighting. Shows today's note by default, with flags to browse other entries.

**Usage:**
```bash
x notes              # open today's note (YYYY-MM-DD.md)
x notes --last       # open the most recently created note
x notes --tasks      # open the tasks file (tasks.md)
```

**Dependencies:**
- `batcat` — syntax-highlighted file viewer
- `~/documents/journal/` — directory containing dated `.md` notes

**Manual test:**
```bash
x notes              # should show today's note or "No note for today"
x notes --last       # should show the last dated note
x notes --tasks      # should show ~/documents/journal/tasks.md
```
