# wtf

**What it does:** Captures the last failed command and its error message, then sends it to the AI for analysis.

**Dependencies:**
- `/tmp/last_command.txt` — written by `log_output` in `.bashrc`
- `/tmp/last_error.txt` — written by the `wtf` shell function
- `OPENROUTER_API_KEY` env variable

**Shell setup:**

Add to `~/.bashrc`. `log_output` only records the last failed command; it
never re-runs anything from the prompt. `wtf` re-runs it on demand, in a
subshell, captures its stderr, then calls `x wtf`.

```bash
log_output() {
	local exit_code=$? num cmd
	read -r num cmd < <(history 1)
	# Skip the first prompt and prompts with no new history entry.
	if [[ -z ${__log_last_num+set} || $num == "$__log_last_num" ]]; then
		__log_last_num=$num
		return
	fi
	__log_last_num=$num
	((exit_code)) && printf '%s\n' "$cmd" >/tmp/last_command.txt
}

wtf() {
	local cmd
	cmd=$(</tmp/last_command.txt) || return
	printf 're-running: %s\n' "$cmd" >&2
	(eval "$cmd") 2>/tmp/last_error.txt >/dev/null
	x wtf
}

PROMPT_COMMAND='log_output'
```

Then reload: `source ~/.bashrc`

> Do not re-run the command from `PROMPT_COMMAND` itself: a new shell can
> start with a non-zero `$?` and its history loaded from file, so the last
> command of a previous session would run in the foreground at every new
> terminal, and Ctrl+C would loop it.

**API key:**

`x wtf` sends errors to [OpenRouter](https://openrouter.ai/) for AI analysis:

```bash
export OPENROUTER_API_KEY=your_key_here
```

**Manual test:**
```bash
ls ~/non-existent-folder
wtf
```

**Expected output:**
```
Command: ls ~/non-existent-folder
Error: ls: cannot access '...': No such file or directory

Analyzing...
<AI explanation>
```
