from x.utils.colors import error, command, success, info
from x.utils.ai import ask

def run():
    try:
        with open("/tmp/last_command.txt", "r") as f:
            last_command = f.read().strip()
        with open("/tmp/last_error.txt", "r") as f:
            last_error = f.read().strip()
        print(command(f"Command: {last_command}"))
        print(error(f"Error: {last_error}"))
        print(info(f"\nAnalyzing..."))

        prompt = f"Command: {last_command}\nError: {last_error}"
        analysis = ask(prompt)
        
        print(f"\n{analysis}")
        
    except FileNotFoundError:
        print(info("No failed command found yet."))
