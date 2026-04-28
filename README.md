# toolbox

A personal CLI toolkit built in Python. All commands live under a single entry point `x`, designed to be extended with new subcommands over time.

---

## Commands

| Command | Description |
|---------|-------------|
| [`x wtf`](x/commands/wtf/README.md) | Analyze the last failed shell command via AI |
| [`x notes`](x/commands/notes/README.md) | Browse journal notes with syntax highlighting |
| [`x repos`](x/commands/repos/README.md) | Clone GitHub repos with optional filters |
| [`x sync`](x/commands/sync/README.md) | Sync Claude memory and journal notes to Nextcloud |

---

## Requirements

- Python 3.8+
- pip
- `batcat` (for `x notes`)
- `gh` CLI (for `x repos`)
- `OPENROUTER_API_KEY` env variable (for `x wtf`)
- Nextcloud account + app password (for `x sync`)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/LionelPinheiroDuarte/toolbox.git
cd toolbox
```

### 2. Install the package

```bash
pip install -e . --break-system-packages
```

### 3. Per-command setup

Some commands require additional setup — see each command's README linked above.

---

## Project structure

```
toolbox/
├── x/
│   ├── __init__.py
│   ├── main.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── notes/
│   │   │   ├── __init__.py
│   │   │   └── README.md
│   │   ├── repos/
│   │   │   ├── __init__.py
│   │   │   └── README.md
│   │   ├── sync/
│   │   │   ├── __init__.py
│   │   │   └── README.md
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
├── pyproject.toml
└── README.md
```

---

## Roadmap

- [x] `x wtf` — capture and explain last failed command via AI (OpenRouter)
- [x] `x notes` — browse journal notes with syntax highlighting
- [x] `x repos` — clone GitHub repos with optional filters
- [x] `x sync` — sync Claude memory and journal notes to Nextcloud
- [x] Gruvbox Dark color formatting
- [ ] `x history` — browse past errors
- [ ] `install.sh` — one-line installation script

---

## License

MIT
