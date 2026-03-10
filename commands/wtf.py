def run():
    try:
        with open("/tmp/last_command.txt", "r") as f:
            last_command = f.read().strip()
        print(f"Last failed command: {last_command}")
    except FileNotFoundError:
        print("No failed command found yet.")
