# toolbox

A personal CLI toolkit built in Python. All commands live under a single entry point `x`, designed to be extended with new subcommands over time.

---

## Commands

| Command | Description |
|---------|-------------|
| `x wtf` | Analyze the last failed shell command via AI |
| `x notes` | Browse journal notes with syntax highlighting |
| `x repos` | Clone GitHub repos with optional filters |
| `x sync` | Sync Claude memory and journal notes to Nextcloud |

Full documentation for each command: [`x/commands/`](x/commands/README.md)

---

## Requirements

- Python 3.8+
- pip
- `batcat` (for `x notes`)
- `gh` CLI (for `x repos`)
- `OPENROUTER_API_KEY` environment variable (for `x wtf`)
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

### 3. Configure your shell

Add the following to your `~/.bashrc` to enable error capture for `x wtf`:

```bash
log_output() {
    local exit_code=$?
    local last_cmd=$(history 1 | awk '{$1=""; print $0}' | xargs)
    if [ $exit_code -ne 0 ]; then
        echo "$last_cmd" > /tmp/last_command.txt
        case "$last_cmd" in
            python3*|python*|x\ *|x) ;;
            *) eval "$last_cmd" 2>/tmp/last_error.txt 1>/dev/null ;;
        esac
    fi
}

PROMPT_COMMAND='log_output'
```

Then reload your shell:

```bash
source ~/.bashrc
```

### 4. Set your API key

`x wtf` sends errors to [OpenRouter](https://openrouter.ai/) for AI analysis:

```bash
export OPENROUTER_API_KEY=your_key_here
```

---

## Usage

```bash
x --help                                        # show all available commands
x wtf                                           # analyze the last failed command
x notes                                         # open today's journal note
x notes --last                                  # open the most recent note
x notes --tasks                                 # open the task file
x repos --single LionelPinheiroDuarte/toolbox   # clone a single repo
x repos --language python                       # clone all Python repos
x sync                                          # sync Claude memory + journal to Nextcloud
x sync --configure                              # set up Nextcloud credentials
```

### x notes

![x notes demo](assets/notes.gif)

---

## Project structure

```
toolbox/
├── x/
│   ├── __init__.py
│   ├── main.py
│   ├── commands/
│   │   ├── README.md       ← commands index
│   │   ├── __init__.py
│   │   ├── notes.py
│   │   ├── notes.md
│   │   ├── repos.py
│   │   ├── repos.md
│   │   ├── sync.py
│   │   ├── sync.md
│   │   ├── wtf.py
│   │   └── wtf.md
│   └── utils/
│       ├── __init__.py
│       ├── ai.py
│       └── colors.py
├── assets/
│   └── notes.gif
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
