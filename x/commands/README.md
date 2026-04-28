# Commands

Each command has its own file and a minimal manual test procedure.

---

## sync

**What it does:** Uploads Claude memory files and journal Markdown notes to Nextcloud via WebDAV. Credentials are stored in the system keyring (never in plaintext).

**Sources synced:**
- `~/.claude/CLAUDE.md`
- `~/.claude/projects/-home-eswine/memory/*.md`
- `~/documents/journal/YYYY-MM-DD.md`

**Destinations on Nextcloud:**
- `backups/claude-memory/`
- `backups/journal/`

**First-time setup:**
```bash
x sync --configure
# prompts for: Nextcloud URL, username, app password
# app password: Nextcloud → Settings → Security → App passwords
```

**Usage:**
```bash
x sync              # sync everything
x sync --claude     # Claude memory files only
x sync --journal    # journal notes only
```

**Dependencies:**
- `requests` — WebDAV HTTP calls
- `keyring` + `keyrings.alt` — secure credential storage (WSL fallback via `keyrings.alt`)

**Manual test:**
```bash
x sync --configure   # enter real or dummy creds
x sync --journal     # upload journal notes, verify in Nextcloud web UI
```

---

## wtf

**What it does:** Captures the last failed command and its error message, then sends it to the AI for analysis.

**Dependencies:**
- `/tmp/last_command.txt` — written by `log_output` in `.bashrc`
- `/tmp/last_error.txt` — written by `log_output` in `.bashrc`
- `OPENROUTER_API_KEY` env variable

**Manual test:**
```bash
ls ~/non-existent-folder
x wtf
```

**Expected output:**
```
Command: ls ~/non-existent-folder
Error: ls: cannot access '...': No such file or directory

Analyzing...
<AI explanation>
```

---
