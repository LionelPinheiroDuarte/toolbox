# repos

**What it does:** Clones, pulls and pushes my GitHub repositories — one by name, or all of them at once.

**Usage:**
```bash
x repos clone toolbox                  # clone one of my repos (owner added for you)
x repos clone someone/repo             # clone anyone's repo
x repos clone --language python        # clone all my Python repos
x repos clone --all                    # clone everything

x repos pull                           # fast-forward every repo
x repos pull vocab                     # fast-forward one repo

x repos push                           # preview unpushed commits, confirm, push
x repos push vocab                     # push one repo, no prompt
x repos push -y                        # push all without confirmation
```

**Options:**
- `NAME` — repo directory name (`owner/name` also accepted by `clone`)
- `--language` / `-l` — `clone` only: all repos matching a language
- `--all` — `clone` only: all your repos (`pull`/`push` act on all repos when `NAME` is omitted)
- `--yes` / `-y` — `push` only: skip the confirmation
- `--dir` / `-d` — repos directory (default: `$GITHUB`, else `~/repos/github`)

**Rules for `pull` and `push`:**
- Only repos whose `origin` is one of my GitHub repos (https or ssh) — others are skipped
- Current branch only; a branch without an upstream on `origin` is skipped, with the command to fix it
- `pull` is always `--ff-only`: a diverged branch is reported, never merged or rebased
- Uncommitted changes are allowed — git refuses if they would be overwritten — and shown as `(dirty)`
- `push` never forces; a rejected push is reported
- One line per repo, then `ok · failed · skipped`; exit code 1 if any repo failed (skipped is not a failure)

**Example output:**
```
✓ brain     (main)  up to date (dirty)
✗ agents    (main)  diverged: resolve manually
- infra-lab (docs)  skipped: no upstream (git push -u origin docs)
- matomo            skipped: no GitHub origin

1 ok · 1 failed · 2 skipped
```

**Dependencies:**
- `git`
- `gh` CLI — `clone` only, must be authenticated (`gh auth login`)

**Manual test:**
```bash
x repos pull                 # safe: fast-forward only
echo n | x repos push        # shows the preview, pushes nothing
```
