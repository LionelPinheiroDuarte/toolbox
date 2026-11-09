# claude

**What it does:** Two tmux popups around Claude Code. `x claude projects` keeps one tmux session per project with Claude running in it, and shows where Claude is working or has answered. `x claude edits` lists the files Claude recently wrote, shows its diff and opens them in Vim. Bound to `prefix+g` and `prefix+e` / `prefix+E` in my [dotfiles](https://github.com/LionelPinheiroDuarte/dotfiles).

Both were Bash scripts in my [agents](https://github.com/LionelPinheiroDuarte/agents) repo (`tools/claude-projects`, `tools/claude-edits`). They now live here, where they share the toolbox's Python and its tests.

## x claude projects

Work with Claude Code on several projects at once: one tmux session per repo, each with a `claude` window and a `shell` window. The popup lists the projects; pick one to jump to its session, created on the fly. Open projects are remembered, and after a reboot `x claude projects restore` reopens them with `claude --continue`, so each one resumes its last conversation.

```
x claude projects                     pick a project (fzf)
x claude projects open [dir] [shell]  open (or jump to) the project in dir, e.g. one outside $GITHUB
x claude projects new <name>          create $GITHUB/<name> (git init) and open it
x claude projects save                remember the open project sessions
x claude projects restore             reopen every saved project
x claude projects kill <name>         close a project session
x claude projects state <state>       running|done|none, called by Claude Code hooks
```

In the popup:

| Key | Action |
|-----|--------|
| type | Fuzzy-filter the list |
| `enter` | Jump to the project, creating its session if needed |
| `ctrl+s` | Same, landing on its `shell` window |
| `ctrl+x` | Close the session |
| `ctrl+n` | Create `$GITHUB/<query>` (`git init`) and open it |
| `ctrl+r` | Restore every saved project |
| `ctrl+/` | Hide or show the preview |

The list has up to five groups (*sessions ouvertes*, *autres sessions tmux*, *à restaurer*, *sans projet*, *dépôts*) and one row per project: mark, name, branch, changes and age.

| Mark | Meaning | Age |
|------|---------|-----|
| `⟳` | Claude is working | since the prompt was sent |
| `✓` | Claude has answered | since the answer |
| `●` | Open | since the session's last activity |
| `↺` | Saved, reopened with `claude --continue` | since the last commit |
| `◇` | No project: Claude in `~`, while it is not open | — |
| `○` | Another tmux session, not opened from here (`enter` just goes there, `ctrl+x` closes it) | since its last activity |
| none | Another repo of `$GITHUB` | since the last commit |

Changes are `±N` modified files and `↑N` commits not pushed, for open and saved projects only: `git status` on every repo at each opening would slow the popup down.

The preview is a card: Claude's state and for how long, the path, branch, ahead/behind, clean tree or not, the tmux windows; the **last exchange** with Claude (last prompt, start of the answer), read from the newest transcript in `~/.claude/projects/`; and the last five commits. The transcript format is internal to Claude Code, so that section is just left out when it cannot be read.

**Claude's state.** Claude Code hooks (dotfiles' `.claude/settings.json`) call `x claude projects state` from the pane Claude runs in, which sets `@claude_state` on its tmux session, and `@claude_state_at` when the state changes:

| Hook | State | Mark |
|------|-------|------|
| `UserPromptSubmit` | `running` | `⟳` |
| `Stop` | `done` | `✓` |
| `SessionEnd` | `none` | — |

`✓` is not set when you are already looking at the answer (session attached, Claude's window in front), and a tmux `client-session-changed` hook clears it once you switch to the session. `Stop` does not fire when Claude is interrupted with `Esc`, so `⟳` stays until the next prompt.

**Saved list.** `~/.local/state/claude/projects.tsv`, one `name<TAB>dir` line per project, rewritten when a project is opened or killed from here and by `save`. Not on tmux's `session-closed` hook: when the server dies every session closes, and the hook would empty the list right before `restore` needs it.

## x claude edits

```
x claude edits          all sessions
x claude edits <dir>    only the files of the repo holding <dir> (e.g. the pane's)
```

Its data comes from the [`log-edits`](https://github.com/LionelPinheiroDuarte/agents/tree/main/hooks/log-edits) hook: every file Claude writes is logged, and its content before Claude's first edit of the session is kept as a snapshot. Files are grouped by the session that last touched them, newest first; deleted files are skipped.

| Key | Action |
|-----|--------|
| `enter` | Open the file in Vim, in a new tmux window |
| `ctrl+d` | Open it straight in Claude's diff |
| `ctrl+f` | Preview: diff or whole file |
| `ctrl+g` | This repo or all files |
| `ctrl+y` | Copy the path (tmux buffer and clipboard) |
| `ctrl+/` | Hide or show the preview |

Marks: `✚` created by Claude, `~` modified, `↶` reverted since (no change left), `?` no snapshot (edited before the hook recorded diffs).

In Vim, [`edits.vim`](edits.vim) adds `,d` (a `git diff`-style view of Claude's changes, unsaved edits included) and `,D` (side-by-side vimdiff with the "before" file, to take a hunk back with `do`).

## How it works

- fzf drives each popup and calls `x claude …` back for the list, the preview and the keys (hidden subcommands and options, see `x/main.py`). The popup's state (diff or file view, repo or all) lives in temp files that fzf passes back.
- The counter next to the prompt ("2 ouverts · 14/14") is computed by a few lines of shell from a file written with the list, not by Python: it runs on every key.
- Commands import their module when they run, so `x` starts in ~140 ms: `state` runs on every Claude prompt and `preview` on every move in the list.
- The palette, ages, fzf version check and shared fzf options are in [`x/utils/popup.py`](../../utils/popup.py).

## Setup

`fzf` 0.66 or later (`--footer`, `--gutter`): the dotfiles playbook installs the official binary (`--tags fzf`); the popup says so and exits on an older one. `batcat` is used for the file view when present. No `jq` needed anymore.
