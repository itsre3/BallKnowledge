from typing import Optional

class Player:
    def __init__(self, sid, username: str = "Guest"):
        self.sid = sid
        self.username = username
        self.word = ""
        self.choices = []
        self.finished: bool = False
        self.trials = 1
        self.hints: list = []


class Room:
    def __init__(self, code: str, type: str = "ranked"):
        self.code = code
        self.type = type
        self.player1: Optional[Player] = None
        self.player2: Optional[Player] = None
        self.phase: str = "waiting"
        self.winner: Optional[Player] = None

    def is_full(self):
        return self.player1 is not None and self.player2 is not None
