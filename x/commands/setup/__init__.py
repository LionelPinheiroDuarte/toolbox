import os
import subprocess

from x.utils.colors import error, info, success

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
        result = subprocess.run(["git", "-C", DOTFILES_DIR, "pull"])
        if result.returncode != 0:
            print(error("Pull failed."))
            raise SystemExit(1)

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
