import sys
import click

from x.commands import hello as hello_cmd
from x.commands import wtf as wtf_cmd
from x.commands import notes as notes_cmd

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

def main():
    cli()
