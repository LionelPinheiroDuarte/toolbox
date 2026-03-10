# x — your personal CLI

A unified, extensible command-line tool built in Python. `x` groups all your personal CLI commands under a single entry point — starting with `wtf`, which automatically captures and explains the last failed terminal command.

---

## Requirements

- Python 3.8+
- pip

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-user/x.git
cd x
```

### 2. Install the package

```bash
pip install -e . --break-system-packages
```

### 3. Configure your shell

Add the following to your `~/.bashrc`:

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

---

## Usage

```bash
x --help       # show all available commands
x wtf          # analyze the last failed command
```

### Example

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
x/
├── x/
│   ├── __init__.py
│   ├── main.py
│   └── commands/
│       ├── __init__.py
│       ├── hello.py
│       └── wtf.py
│   └── utils/
│       ├── __init__.py
│       └── colors.py
├── pyproject.toml
└── README.md
```

---

## Roadmap

- [x] `x wtf` — capture and display last failed command
- [x] Gruvbox Dark color formatting
- [ ] AI-powered error analysis via Claude API
- [ ] `x history` — browse past errors
- [ ] `install.sh` — one-line installation script

---

## License

MIT
