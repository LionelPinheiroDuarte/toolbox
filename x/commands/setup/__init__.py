import os
import subprocess

from x.commands.repos import pull_repo, FAILED, SKIPPED
from x.utils.colors import error, info, success, warning

DOTFILES_REPO = "https://github.com/LionelPinheiroDuarte/dotfiles.git"
DOTFILES_DIR = os.path.expanduser("~/repos/github/dotfiles")


def run(short=False):
    if not os.path.isdir(DOTFILES_DIR):
        print(info("Cloning dotfiles..."))
        result = subprocess.run(["git", "clone", DOTFILES_REPO, DOTFILES_DIR])
        if result.returncode != 0:
            print(error("Clone failed."))
            raise SystemExit(1)
    else:
        print(info("Updating dotfiles..."))
        status, _, message = pull_repo(DOTFILES_DIR)
        if status == FAILED:
            print(error(f"Pull failed: {message}"))
            raise SystemExit(1)
        print(warning(message) if status == SKIPPED else success(message))

    cmd = ["ansible-playbook", "ansible/playbook.yml", "-i", "ansible/inventory.ini"]
    if short:
        cmd += ["--tags", "dotfiles,toolbox"]
    else:
        cmd += ["-K"]

    print(info("Running Ansible playbook..."))
    result = subprocess.run(cmd, cwd=DOTFILES_DIR)
    if result.returncode != 0:
        print(error("Ansible playbook failed."))
        raise SystemExit(result.returncode)

    print(success("Done."))
