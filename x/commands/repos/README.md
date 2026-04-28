# repos

**What it does:** Clones GitHub repositories using the `gh` CLI, with filters to target a single repo, all repos matching a language, or everything.

**Usage:**
```bash
x repos --single LionelPinheiroDuarte/toolbox          # clone one repo
x repos --language python                              # clone all Python repos
x repos --all                                          # clone everything
x repos --all --dest ~/projects                        # custom destination
```

**Options:**
- `--single` / `-s` — clone a specific repo by `owner/name`
- `--language` / `-l` — clone all repos matching a language
- `--all` — clone all your repos
- `--dest` / `-d` — destination directory (default: `~/repos/github`)

**Dependencies:**
- `gh` CLI — GitHub CLI, must be authenticated (`gh auth login`)

**Manual test:**
```bash
x repos --single LionelPinheiroDuarte/toolbox
# should clone into ~/repos/github/toolbox
```
