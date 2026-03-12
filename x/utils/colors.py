# Gruvbox Dark palette
RED = "\033[38;2;251;73;52m"        # bright red — erreurs
ORANGE = "\033[38;2;254;128;25m"    # bright orange — commandes
YELLOW = "\033[38;2;250;189;47m"    # bright yellow — warnings
GREEN = "\033[38;2;184;187;38m"     # bright green — succès
BLUE = "\033[38;2;131;165;152m"     # bright blue — info
PURPLE = "\033[38;2;211;134;155m"   # bright purple — accents
BOLD = "\033[1m"
RESET = "\033[0m"

def error(text):
    return f"{RED}{text}{RESET}"

def command(text):
    return f"{ORANGE}{text}{RESET}"

def success(text):
    return f"{GREEN}{text}{RESET}"

def info(text):
    return f"{BLUE}{text}{RESET}"
