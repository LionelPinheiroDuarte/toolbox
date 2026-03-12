# Commands

Each command has its own file and a minimal manual test procedure.

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
