import sys
import click

from x.commands import notes as notes_cmd
from x.commands import repos as repos_cmd

# Commands import their module when they run: keyring and requests (sync)
# would double the start-up of every x call, and some run on every fzf key
# or Claude prompt (x claude projects preview / state).

@click.group()
def cli():
    pass

@cli.command()
def wtf():
    """Analyze the last failed command."""
    # imported here: openai alone takes most of x's start-up time, and the
    # other commands (some called by fzf on every key) don't need it
    from x.commands import wtf as wtf_cmd
    wtf_cmd.run()

@cli.command()
@click.option("--last", "-l", is_flag=True, help="Show the last created note.")
@click.option("--tasks", "-t", is_flag=True, help="Show the task file.")
@click.option("--edit", "-e", is_flag=True, help="Open the file in $EDITOR instead of showing it.")
@click.option("--browse", "-b", is_flag=True, help="Browse, open, create and trash notes in fzf.")
# called back by fzf from --browse (see x/commands/notes/browse.py)
@click.option("--list-entries", is_flag=True, hidden=True)
@click.option("--open-path", hidden=True)
@click.option("--window-path", hidden=True)
@click.option("--new-note", hidden=True)
@click.option("--trash-path", hidden=True)
def notes(last, tasks, edit, browse, list_entries, open_path, window_path, new_note, trash_path):
    """Show today's journal note, last entry, or task file; or browse them all."""
    if any(x is not None for x in (open_path, window_path, new_note, trash_path)) \
            or browse or list_entries:
        from x.commands.notes import browse as browse_cmd
        if list_entries:
            print("\n".join(browse_cmd.entries()))
        elif open_path is not None:
            browse_cmd.open_path(open_path)
        elif window_path is not None:
            browse_cmd.open_window(window_path)
        elif new_note is not None:
            browse_cmd.new_note(new_note)
        elif trash_path is not None:
            browse_cmd.trash_path(trash_path, browse_cmd.self_command())
        else:
            browse_cmd.browse()
        return
    notes_cmd.run(last=last, tasks=tasks, edit=edit)

@cli.group()
def repos():
    """Clone, pull or push my GitHub repos."""
    pass

dir_option = click.option("--dir", "-d", "directory", default=repos_cmd.DEFAULT_DIR, show_default=True,
                          help="Directory holding the repos ($GITHUB).")

@repos.command()
@click.argument("name", required=False)
@click.option("--language", "-l", default=None, help="Clone all repos matching a language.")
@click.option("--all", "all_repos", is_flag=True, help="Clone all repos.")
@dir_option
def clone(name, language, all_repos, directory):
    """Clone a repo by NAME (or owner/name), by language, or all of them."""
    if not any([name, language, all_repos]):
        raise click.UsageError("Specify NAME, --language, or --all.")
    repos_cmd.clone(name=name, language=language, all_repos=all_repos, directory=directory)

@repos.command()
@click.argument("name", required=False)
@dir_option
def pull(name, directory):
    """Fast-forward one repo, or all of them if NAME is omitted."""
    repos_cmd.pull(name=name, directory=directory)

@repos.command()
@click.argument("name", required=False)
@click.option("--yes", "-y", is_flag=True, help="Push all without confirmation.")
@dir_option
def push(name, yes, directory):
    """Push one repo, or all of them (after confirmation) if NAME is omitted."""
    repos_cmd.push(name=name, directory=directory, yes=yes)

@cli.command()
@click.option("--claude", is_flag=True, help="Sync Claude memory files only.")
@click.option("--journal", is_flag=True, help="Sync journal notes only.")
@click.option("--cv", is_flag=True, help="Sync CV project (profile, template, PDFs, agents) only.")
@click.option("--skills", is_flag=True, help="Sync Claude skills (~/.claude/skills) only.")
@click.option("--configure", "do_configure", is_flag=True, help="Set up Nextcloud credentials.")
@click.option("--restore", "do_restore", is_flag=True, help="Restore files from Nextcloud to local machine.")
def sync(claude, journal, cv, skills, do_configure, do_restore):
    """Sync Claude memory, skills, journal notes and CV project to Nextcloud."""
    from x.commands import sync as sync_cmd
    if do_configure:
        sync_cmd.configure()
        return
    if do_restore:
        sync_cmd.restore(claude=claude, journal=journal, cv=cv, skills=skills)
        return
    sync_cmd.run(claude=claude, journal=journal, cv=cv, skills=skills)


@cli.command()
@click.option("--all", "show_all", is_flag=True, help="Also list tmux's own bindings.")
def keys(show_all):
    """Show my tmux shortcuts (the bindings with a note in ~/.tmux.conf)."""
    from x.commands import keys as keys_cmd
    keys_cmd.run(show_all=show_all)


@cli.command()
@click.option("--short", is_flag=True, help="User-level only (dotfiles + toolbox, no sudo).")
def setup(short):
    """Clone or update dotfiles and run the Ansible playbook."""
    from x.commands import setup as setup_cmd
    setup_cmd.run(short=short)


@cli.group()
def claude():
    """tmux popups around Claude Code: projects and the files it edited."""


@claude.group(invoke_without_command=True)
@click.pass_context
def projects(ctx):
    """One tmux session per project, with Claude in it (fzf picker).

    \b
    Keys in the list: enter = go (create if needed) · ctrl-x = kill the session
      ctrl-n = new project named after the query · ctrl-r = restore all saved
      ctrl-s = go, on the shell window · ctrl-/ = preview
    """
    if ctx.invoked_subcommand is None:
        from x.commands.claude import projects as projects_cmd
        projects_cmd.pick()


@projects.command("open")
@click.argument("directory", default=".")
@click.argument("window", required=False, type=click.Choice(["shell"]))
def projects_open(directory, window):
    """Open (or jump to) the project in DIRECTORY, on its shell window with "shell"."""
    from x.commands.claude import projects as projects_cmd
    projects_cmd.open_project(directory, window)


@projects.command("new")
@click.argument("name")
def projects_new(name):
    """Create $GITHUB/NAME (git init) and open it."""
    from x.commands.claude import projects as projects_cmd
    projects_cmd.new_project(name)


@projects.command("save")
def projects_save():
    """Remember the open project sessions."""
    from x.commands.claude import projects as projects_cmd
    projects_cmd.save()
    print(f"Saved {len(projects_cmd.saved_projects())} project(s) to {projects_cmd.SAVED}")


@projects.command("restore")
def projects_restore():
    """Reopen every saved project, Claude resuming its last conversation."""
    from x.commands.claude import projects as projects_cmd
    projects_cmd.restore()


@projects.command("kill")
@click.argument("name")
def projects_kill(name):
    """Close a project session."""
    from x.commands.claude import projects as projects_cmd
    projects_cmd.kill_project(name)


@projects.command("state")
@click.argument("state", type=click.Choice(["running", "done", "none"]))
def projects_state(state):
    """Claude's state on this pane's session, from Claude Code hooks."""
    from x.commands.claude import projects as projects_cmd
    projects_cmd.set_state(state)


# called back by fzf from the picker
@projects.command("entries", hidden=True)
def projects_entries():
    import os
    from x.commands.claude import projects as projects_cmd
    print("\n".join(projects_cmd.entries(os.environ.get("X_CLAUDE_PROJECTS_INFO"))))


@projects.command("preview", hidden=True)
@click.argument("directory")
@click.argument("name")
@click.argument("kind")
def projects_preview(directory, name, kind):
    from x.commands.claude import projects as projects_cmd
    projects_cmd.preview(directory, name, kind)


@claude.command()
@click.argument("directory", required=False)
# called back by fzf from the picker (see x/commands/claude/edits.py)
@click.option("--list", "list_files", nargs=2, hidden=True)
@click.option("--preview", nargs=4, hidden=True)
@click.option("--toggle", hidden=True)
@click.option("--scope", nargs=2, hidden=True)
@click.option("--vimdiff", nargs=2, hidden=True)
def edits(directory, list_files, preview, toggle, scope, vimdiff):
    """Files Claude recently wrote: its diff, then Vim (fzf picker).

    With DIRECTORY, only the files of the repo holding it.

    \b
    Keys in the list: enter = vim · ctrl-d = vimdiff before/after · ctrl-f = diff/file
                      ctrl-g = this repo/all · ctrl-y = copy the path · ctrl-/ = preview
    Keys in Vim: ,d = git-diff-like view · ,D = side-by-side vimdiff
    """
    from x.commands.claude import edits as edits_cmd
    if list_files:
        scope_path, info_path = list_files
        print("\n".join(edits_cmd.entries(edits_cmd._read(scope_path), info_path)))
    elif preview:
        edits_cmd.preview(*preview)
    elif toggle:
        edits_cmd.toggle(toggle)
    elif scope:
        edits_cmd.flip_scope(*scope)
    elif vimdiff:
        edits_cmd.vimdiff(*vimdiff)
    else:
        edits_cmd.browse(directory)


def main():
    cli()
