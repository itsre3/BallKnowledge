from functools import wraps
from flask import request
from flask_socketio import emit


def in_room(handler):
    @wraps(handler)
    def wrapped(self, data, *args, **kwargs):
        if not isinstance(data, dict):
            emit("error", {"message": "Invalid request"}, to=request.sid)
            return

        code = data.get("code")
        if not isinstance(code, str) or not code.strip():
            emit("error", {"message": "Invalid room code"}, to=request.sid)
            return

        code = code.strip().upper()
        room = self.active_rooms.get(code)
        if room is None:
            emit("error", {"message": "Room does not exist"}, to=request.sid)
            return

        if not any(
            player is not None and player.sid == request.sid
            for player in (room.player1, room.player2)
        ):
            emit("error", {"message": "You are not in this room"}, to=request.sid)
            return

        return handler(self, {**data, "code": code}, *args, **kwargs)

    return wrapped