# toolbox

A personal CLI toolkit built in Python. All commands live under a single entry point `x`, designed to be extended with new subcommands over time.

---

## Commands

| Command | Description |
|---------|-------------|
| [`x wtf`](x/commands/wtf/README.md) | Analyze the last failed shell command via AI |
| [`x notes`](x/commands/notes/README.md) | Show, edit or browse (fzf) journal notes and the task file |
| [`x repos`](x/commands/repos/README.md) | Clone, pull or push my GitHub repos — one or all |
| [`x keys`](x/commands/keys/README.md) | List my tmux shortcuts, read from the `bind -N` notes in `~/.tmux.conf` |
| [`x sync`](x/commands/sync/README.md) | Sync Claude memory, skills, journal notes and CV project to Nextcloud |
| `x setup` | Clone dotfiles and run the full Ansible playbook (`--short` for user-level only) |

---

## Requirements

- Python 3.8+
- pip
- `batcat` (for `x notes`), `fzf` >= 0.66 and `gio` (for `x notes --browse`)
- `gh` CLI (for `x repos clone`)
- `tmux` >= 3.1 (for `x keys`)
- `OPENROUTER_API_KEY` env variable (for `x wtf`)
- Nextcloud account + app password (for `x sync`)
- `ansible-core` + `git` (for `x setup`)

---

## Installation

```bash
curl -sSL https://raw.githubusercontent.com/LionelPinheiroDuarte/toolbox/main/install.sh | bash
```

The script checks for Python 3.8+, installs pipx if needed, and prints a setup summary with required env variables.

### Per-command setup

Some commands require additional setup — see each command's README linked above.

### Development install

```bash
git clone https://github.com/LionelPinheiroDuarte/toolbox.git
cd toolbox
pip install -e . --break-system-packages
```

---

## Project structure

```
toolbox/
├── x/
│   ├── __init__.py
│   ├── main.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── keys/
│   │   │   ├── __init__.py
│   │   │   └── README.md
│   │   ├── notes/
│   │   │   ├── __init__.py
│   │   │   ├── browse.py      # --browse: the fzf popup
│   │   │   ├── store.py       # the journal on disk
│   │   │   └── README.md
│   │   ├── repos/
│   │   │   ├── __init__.py
│   │   │   └── README.md
│   │   ├── sync/
│   │   │   ├── __init__.py
│   │   │   └── README.md
│   │   ├── setup/
│   │   │   └── __init__.py
│   │   └── wtf/
│   │       ├── __init__.py
│   │       └── README.md
│   └── utils/
│       ├── __init__.py
│       ├── ai.py
│       └── colors.py
├── assets/
│   ├── notes.gif
│   └── sync.gif
├── tests/                     # pytest
├── pyproject.toml
└── README.md
```

---

## Roadmap

- [x] `x wtf` — capture and explain last failed command via AI (OpenRouter)
- [x] `x notes` — browse journal notes with syntax highlighting
- [x] `x notes --browse` — fzf popup to open, create and trash notes
- [x] `x keys` — tmux shortcuts, from the config's own notes
- [x] `x repos` — clone, pull and push GitHub repos
- [x] `x sync` — sync Claude memory, skills, journal notes and CV project to Nextcloud
- [x] `x setup` — provision a new machine from dotfiles + Ansible
- [x] Gruvbox Dark color formatting
- [ ] `x history` — browse past errors
- [x] `install.sh` — one-line installation script

---

## License

MIT
