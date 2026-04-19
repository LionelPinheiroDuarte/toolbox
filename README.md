# toolbox

A personal CLI toolkit built in Python. All commands live under a single entry point `x`, designed to be extended with new subcommands over time.

---

## Commands

- `x wtf` — captures the last failed shell command and explains it via AI
- `x notes` — opens today's journal note (or the last one) using `bat`

---

## Requirements

- Python 3.8+
- pip
- `batcat` (for `x notes`)
- `OPENROUTER_API_KEY` environment variable (for `x wtf`)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/eswine/toolbox.git
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
x --help              # show all available commands
x wtf                 # analyze the last failed command
x notes               # open today's journal note
x notes --last        # open the most recent note
x notes --tasks       # open the task file
```

### x notes

![x notes demo](assets/notes.gif)

### x wtf

```bash
$ ls ~/non-existent-folder
ls: cannot access '/home/user/non-existent-folder': No such file or directory

$ x wtf
Command: ls ~/non-existent-folder
Error: ls: cannot access '/home/user/non-existent-folder': No such file or directory
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
│   │   ├── hello.py
│   │   ├── notes.py
│   │   └── wtf.py
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
- [x] Gruvbox Dark color formatting
- [ ] `x history` — browse past errors
- [ ] `install.sh` — one-line installation script

---

## License

MIT
