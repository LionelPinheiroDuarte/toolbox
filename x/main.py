import sys
import click

from x.commands import hello as hello_cmd
from x.commands import wtf as wtf_cmd
from x.commands import notes as notes_cmd
from x.commands import repos as repos_cmd
from x.commands import sync as sync_cmd
from x.commands import setup as setup_cmd

@click.group()
def cli():
    pass

@cli.command()
def hello():
    """Say hello."""
    hello_cmd.run()

@cli.command()
def wtf():
    """Analyze the last failed command."""
    wtf_cmd.run()

@cli.command()
@click.option("--last", "-l", is_flag=True, help="Show the last created note.")
@click.option("--tasks", "-t", is_flag=True, help="Show the task file.")
def notes(last, tasks):
    """Show today's journal note, last entry, or task file."""
    notes_cmd.run(last=last, tasks=tasks)

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
    if do_configure:
        sync_cmd.configure()
        return
    if do_restore:
        sync_cmd.restore(claude=claude, journal=journal, cv=cv, skills=skills)
        return
    sync_cmd.run(claude=claude, journal=journal, cv=cv, skills=skills)


@cli.command()
@click.option("--short", is_flag=True, help="User-level only (dotfiles + toolbox, no sudo).")
def setup(short):
    """Clone or update dotfiles and run the Ansible playbook."""
    setup_cmd.run(short=short)


def main():
    cli()
