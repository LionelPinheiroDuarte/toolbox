import os
import subprocess

from x.utils.colors import error, info, success

DOTFILES_DIR = os.path.expanduser("~/repos/github/dotfiles")


def pull():
    if not os.path.isdir(DOTFILES_DIR):
        print(error(f"Dotfiles repo not found at {DOTFILES_DIR} — run x setup first."))
        raise SystemExit(1)

    print(info("Pulling dotfiles..."))
    result = subprocess.run(["git", "-C", DOTFILES_DIR, "pull"])
    if result.returncode != 0:
        print(error("Pull failed."))
        raise SystemExit(1)

    print(success("Done."))
