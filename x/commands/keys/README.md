# keys

**What it does:** Lists my tmux shortcuts, so they don't have to live in the status line. Bound to `prefix+?` as a popup in my [dotfiles](https://github.com/LionelPinheiroDuarte/dotfiles).

**Usage:**
```bash
x keys          # my shortcuts
x keys --all    # plus tmux's own bindings (the ones my config didn't replace)
```

**How it knows which shortcuts are mine:**
- Nothing is hard-coded: the list comes from tmux (`list-keys -N`), so it never drifts from `~/.tmux.conf`
- A binding is listed when it has a note: `bind -N "Journal notes" N display-popup ...`. No note, not listed — that's how aliases stay quiet (`\` next to `|`)
- Keys sharing a note go on one line (`h j k l  Select the pane (vi direction)`)
- tmux's defaults have notes too; they are filtered out by comparing with a throwaway server started with no config (`tmux -L x-keys -f /dev/null`), which exits on its own
- Shortcuts are shown in the order of `~/.tmux.conf`, prefix table first, then the bindings that need no prefix (`bind -n`)
- Outside tmux (no server running), `~/.tmux.conf` is read in a throwaway server the same way

**Example output:**
```
tmux shortcuts  prefix C-a

  C-a              Last window
  |                Split side by side
  -                Split top and bottom
  C-h C-j C-k C-l  Resize the pane (vi direction)
  h j k l          Select the pane (vi direction)
  g                Claude projects: jump to one
  N                Journal notes
  ?                These shortcuts

without prefix
  C-y              Send the prefix to a nested tmux
```
