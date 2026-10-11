from flask import request, session, redirect
from flask_socketio import Namespace, emit, leave_room, join_room
from .helpers import select_draft, generate_code, players, hints, is_correct_guess
from .game import Player, Room
from .decorators import in_room
import random, sqlite3

class GameNameSpace(Namespace):
    def __init__(self, namespace, matching_queue, active_rooms, socket):
        super().__init__(namespace)
        self.matching_queue = matching_queue
        self.active_rooms = active_rooms
        self.active_players = set()
        self.socket = socket

    def on_disconnect(self):
        for room in list(self.matching_queue):
            if room.player1 and room.player1.sid == request.sid:
                self.matching_queue.remove(room)
                self.active_players.discard(request.sid)
                return
        room_code = None
        for room in self.active_rooms:
            if self.active_rooms[room].player1 and self.active_rooms[room].player1.sid == request.sid:
                room_code = room
                remaining_player = self.active_rooms[room].player2
                leave_room(room_code, sid=remaining_player.sid)
                break
            elif self.active_rooms[room].player2 and self.active_rooms[room].player2.sid == request.sid:
                room_code = room
                remaining_player = self.active_rooms[room].player1
                leave_room(room_code, sid=remaining_player.sid)
                break
        if room_code:
            if remaining_player:
                emit("disconnect", {"player": session.get("username", "Opponent")}, to=remaining_player.sid)
                self.active_players.discard(remaining_player.sid)
            del self.active_rooms[room_code]
        self.active_players.discard(request.sid)



    def on_matchmaking(self):
        player = Player(sid = request.sid, username = session.get("username", " random"))
        if request.sid in self.active_players:
            return
        self.active_players.add(request.sid)
        for room in self.matching_queue:
            if not room.player2 and not room.is_full() and player.sid != room.player1.sid:
                self.matching_queue.remove(room)
                room.player2 = player
                self.active_rooms[room.code] = room
                room.phase = "in_session"
                join_room(room.code)
                emit("match_found", {"code": room.code, "players": {"player1": room.player1.username, "player2": room.player2.username}}, to=room.code)
                self.socket.sleep(4)
                room.player1.choices = select_draft()
                room.player2.choices = select_draft()
                emit("lock_choice",{"choice": room.player1.choices}, to=room.player1.sid)
                emit("lock_choice", {"choice": room.player2.choices}, to=room.player2.sid)
                return

        code = generate_code()
        room = Room(code=code, type="ranked")
        room.player1 = player
        room.phase = "waiting"
        self.matching_queue.append(room)
        join_room(room.code)
        emit("waiting", {"message": "Matchmaking ranked", "code": room.code}, to=player.sid)
        return

    def on_createroom(self):
        sid = request.sid
        if sid in self.active_players:
            return
        player = Player(sid=sid, username=session.get("username", ""))
        code = generate_code()
        room = Room(code=code, type="custom")
        room.player1 = player
        room.phase = "waiting"
        self.active_rooms[code] = room
        join_room(code)
        emit("waiting", {"message": "Room created", "code": code})

    def on_joinroom(self, data):
        if request.sid in self.active_players:
            return
        code = data["code"].upper().strip()
        room = self.active_rooms.get(code)
        if not room:
            emit("error", {"message": "Room doesnt exist"}, to=request.sid)
            return
        player = Player(sid=request.sid, username=session.get("username", ""))
        if room and room.player1 and not room.is_full():
            room.player2 = player
            room.phase = "in_session"
            join_room(code)
            emit("match_found", {"code": room.code, "players": {"player1": room.player1.username, "player2": player.username}}, to=code)
            self.socket.sleep(4)
            room.player1.choices = select_draft()
            room.player2.choices = select_draft()
            emit("lock_choice",{"choice": room.player1.choices}, to=room.player1.sid)
            emit("lock_choice",{"choice": room.player2.choices}, to=room.player2.sid)
        else:
            emit("error", {"message": "Room Full!"}, to=request.sid)

    @in_room
    def on_saveword(self, data):
        room = self.active_rooms.get(data["code"])
        if not room:
            emit("error", {"message": "Error, Invalid room code"}, to=request.sid)
            return

        if room.player1 and room.player1.sid == request.sid:
            for i in room.player1.choices:
                if data["word"] in i:
                    room.player1.word = i
                    room.player2.hints = hints(i)
                    if room.player2.word:
                        emit("startmatch", {"code": data["code"]}, to=data["code"])
                    return
            emit("wrongchoice", to=request.sid)
        elif room.player2 and room.player2.sid == request.sid:
            for i in room.player2.choices:
                if data["word"] in i:
                    room.player1.hints = hints(i)
                    room.player2.word = i
                    if room.player1.word:
                        emit("startmatch", {"code": data["code"]}, to=data["code"])
                    return
            emit("wrongchoice", to=request.sid)
        else:
            emit("error", {"message": "Player not authorised"}, to=request.sid)

    @in_room
    def on_takeguess(self, data):
        room = self.active_rooms.get(data["code"])
        if not room:
            emit("error", {"message": "Error, Invalid room code"}, to=request.sid)
            return
        if request.sid == room.player1.sid:
            player = room.player1
            player_2 = room.player2
        elif request.sid == room.player2.sid:
            player = room.player2
            player_2 = room.player1
        else:
            emit("error", {"message": "Player not authorised"}, to=request.sid)
            return

        if player.finished:
            emit("disableBox", {"message": "You have already finished guessing."}, to=request.sid)
            return
        
        if is_correct_guess(data["word"], player_2.word):
            if not player.finished:
                player.finished = True
                self.correct_guess({"player": player.sid, "code": room.code})
                return
        else:
            if player.trials < 7:
                player.trials += 1
                random.shuffle(player.hints)
                emit("wrongguess", {"hint": player.hints[0]}, to=request.sid)
                player.hints.pop(0)
            else:
                player.finished = True
                emit("disableBox", {"message": f"Out of Tries. Player is {player_2.word}"})
                self.correct_guess({"player": player.sid, "code": room.code})

    
                    
    def correct_guess(self, data):
        room = self.active_rooms.get(data["code"])
        if not room:
            emit("error", {"message": "Error, Invalid room code"}, to=request.sid)
            return
        if request.sid == data["player"] and data["player"] == room.player1.sid:
            player = room.player1
            s_player = room.player2
        elif request.sid == data["player"] and data["player"] == room.player2.sid:
            player = room.player2
            s_player = room.player1
        else:
            emit("error", {"message": "Error, Invalid player"}, to=request.sid)
            return
        if player.finished and s_player.finished:
            self.check_match_winner(room)
        else:
            if player.trials == 7:
                return
            emit("disableBox", {"message": f"Correct! Waiting for {s_player.username} guess"})
            player.finished = True

    def check_match_winner(self, room):
        p1 = room.player1
        p2 = room.player2
        if p1.trials < p2.trials:
            winner = p1.username
            result_text = f"{p1.username} wins with fewer guesses ({p1.trials} vs {p2.trials})!"
        elif p2.trials < p1.trials:
            winner = p2.username
            result_text = f"{p2.username} wins with fewer guesses ({p2.trials} vs {p1.trials})!"
        else:
            winner = "Draw"
            result_text = f"It's a tie! Both guessed in {p1.trials} tries."

        room.winner = winner
        emit("game_over", {
            "winner": winner,
            "p1_trials": p1.trials,
            "p2_trials": p2.trials,
            "message": result_text
        }, to=room.code)

        self.active_players.discard(p1.sid)
        self.active_players.discard(p2.sid)
        self.active_rooms.pop(room.code, None)

