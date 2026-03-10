import sys
from commands import hello
from commands import wtf

def main():
    if len(sys.argv) < 2:
     print("Use: python3 x.py commands")
     return

    commands = sys.argv[1]

    if commands == "hello":
        hello.run()
    elif commands == "wtf":
        wtf.run()
    else:
        print(f"Unknow command: {command}")

main()
