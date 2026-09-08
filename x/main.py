import sys
import click

from x.commands import hello as hello_cmd
from x.commands import wtf as wtf_cmd
from x.commands import notes as notes_cmd
from x.commands import repos as repos_cmd
from x.commands import sync as sync_cmd
from x.commands import setup as setup_cmd
from x.commands import dotfiles as dotfiles_cmd

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

@cli.command()
@click.option("--single", "-s", default=None, help="Clone a single repo by name.")
@click.option("--language", "-l", default=None, help="Clone all repos matching a language.")
@click.option("--all", "all_repos", is_flag=True, help="Clone all repos.")
@click.option("--dest", "-d", default=repos_cmd.DEFAULT_DEST, show_default=True, help="Destination directory.")
def repos(single, language, all_repos, dest):
    """Clone GitHub repos with optional filters."""
    if not any([single, language, all_repos]):
        import click as _click
        raise _click.UsageError("Specify --single, --language, or --all.")
    repos_cmd.run(single=single, language=language, all_repos=all_repos, dest=dest)

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


@cli.group()
def dotfiles():
    """Manage dotfiles repository."""
    pass


@dotfiles.command()
def pull():
    """Pull latest changes from the dotfiles repo."""
    dotfiles_cmd.pull()


def main():
    cli()
