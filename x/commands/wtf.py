def run():
    try:
        with open("/tmp/last_command.txt", "r") as f:
            last_command = f.read().strip()
        with open("/tmp/last_error.txt", "r") as f:
            last_error = f.read().strip()
        print(f"Command: {last_command}")
        print(f"Error: {last_error}")

    except FileNotFoundError:
        print("No failed command found yet.")
