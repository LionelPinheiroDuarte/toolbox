# wtf

**What it does:** Captures the last failed command and its error message, then sends it to the AI for analysis.

**Dependencies:**
- `/tmp/last_command.txt` — written by `log_output` in `.bashrc`
- `/tmp/last_error.txt` — written by `log_output` in `.bashrc`
- `OPENROUTER_API_KEY` env variable

**Shell setup:**

Add to `~/.bashrc` to enable error capture:

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

Then reload: `source ~/.bashrc`

**API key:**

`x wtf` sends errors to [OpenRouter](https://openrouter.ai/) for AI analysis:

```bash
export OPENROUTER_API_KEY=your_key_here
```

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
