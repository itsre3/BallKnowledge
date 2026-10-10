import random, string, json, unicodedata
import bcrypt


def generate_code():
    # Source - https://stackoverflow.com/a/2257449
    return "".join(random.choices(string.ascii_uppercase, k=4))

def guest_names():
    digits = "".join(random.choices("123456789", k=5))
    return f"Guest{digits}"

def players():
    with open("memory/players.json", "r") as file:
        players = json.load(file)
    return players

def select_draft():
    # Source: https://www.geeksforgeeks.org/python/python-random-sample-function/
    select = random.sample(players(), k=3)
    choices = []
    for p in select:
        choices.append(p["name"])
    print(choices)
    return choices

def hints(name):
    for player in players():
        if player["name"] == name:
            hints = player["hints"]
    # https://www.geeksforgeeks.org/python/convert-dictionary-to-string-list-in-python/
    res = [f"{key}: {val}" for key, val in hints.items()]
    return res

def player_data(name):
    for player in players():
        if player["name"] == name:
            return player

# https://www.geeksforgeeks.org/python/how-to-hash-passwords-in-python/
def generate_hash(password):
    s = bcrypt.gensalt()
    hash = bcrypt.hashpw(bytes(password, "utf-8"), s)
    return hash

def verify_pass(password, hash):
    return bcrypt.checkpw(bytes(password, "utf-8"), hash)

# was very confused how to do this, used ChatGpt
def normalize_name(name: str) -> str:
    if not name:
        return ""
    # Decompose Unicode characters into base letter + accent mark (e.g., é -> e + ´)
    nfkd = unicodedata.normalize("NFKD", name)
    # Filter out accent marks (Mn = Mark, nonspacing)
    ascii_clean = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return ascii_clean.lower().strip()

def is_correct_guess(guess: str, player_name: str) -> bool:
    clean_guess = normalize_name(guess)
    if not clean_guess:
        return False
    data = player_data(player_name)
    if clean_guess == normalize_name(data.get("name", "")):
        return True
    for alias in data.get("aliases", []):
        if clean_guess == normalize_name(alias):
            return True
    return False
