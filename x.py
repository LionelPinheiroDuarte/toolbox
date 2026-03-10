import sys
from commands import hello

def main():
    if len(sys.argv) < 2:
     print("Use: python3 x.py commands")
     return

    commands = sys.argv[1]

    if commands == "hello":
        hello.run()
    else:
        print(f"Unknow command: {command}")

main()
