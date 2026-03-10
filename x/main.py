import sys
import click

from x.commands import hello as hello_cmd
from x.commands import wtf as wtf_cmd

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

def main():
    cli()
