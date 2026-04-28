# sync

**What it does:** Uploads Claude memory files and journal Markdown notes to Nextcloud via WebDAV. Credentials are stored in the system keyring (never in plaintext).

![x sync demo](../../assets/sync.gif)

**Sources synced:**
- `~/.claude/CLAUDE.md`
- `~/.claude/projects/<user>/memory/*.md`
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
