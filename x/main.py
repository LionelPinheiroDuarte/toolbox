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
@click.option("--last", is_flag=True, help="Show the last created note instead of today's.")
def notes(last):
    """Show today's journal note, or the last created one with --last."""
    notes_cmd.run(last=last)

def main():
    cli()
