from x.utils.colors import error, command, success, info

def run():
    try:
        with open("/tmp/last_command.txt", "r") as f:
            last_command = f.read().strip()
        with open("/tmp/last_error.txt", "r") as f:
            last_error = f.read().strip()
        print(command(f"Command: {last_command}"))
        print(error(f"Error: {last_error}"))

    except FileNotFoundError:
        print(info("No failed command found yet."))
