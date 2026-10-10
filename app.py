from flask import Flask, render_template, session, request, redirect
from flask_socketio import SocketIO
from core.helpers import guest_names, generate_hash, verify_pass
from core.event import GameNameSpace
import sqlite3

ACTIVE_ROOMS = {}
MATCHING_QUEUE = []

app = Flask(__name__)
app.config["SECRET_KEY"] = "MaxWell"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")
con = sqlite3.connect("memory/store.db")
db = con.cursor()


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/play")
def play():
    if "username" not in session:
        session["username"] = guest_names()
    return render_template("play.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirmation")
        if not email:
            return render_template("register.html", emailHelp="Add an email")
        elif not username:
            return render_template("register.html", usernameHelp="Add a username")
        elif not password:
            return render_template("register.html", passwordHelp="Password cannot be empty")
        elif not confirm:
            return render_template("register.html", confirmHelp="Field cannot be empty")
        elif password != confirm:
            return render_template("register.html", confirmHelp="Passwords do not match", passwordHelp="Passwords do not match")

        e_email = db.execute("SELECT email FROM users WHERE email = ?", (email, )).fetchone()
        e_username = db.execute("SELECT username FROM users WHERE username = ?", (username, )).fetchone()
        if e_username:
            return render_template("register.html", usernameHelp=f"{username} taken")
        elif e_email:
            return render_template("register.html", emailHelp=f"{email} already registered. Login!")

        hash = generate_hash(password)
        db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hash))
        con.commit()
        id = db.execute("SELECT id FROM users WHERE username = ?", (username, )).fetchone()
        session["user_id"] = id
        session["username"] = username
        return redirect("/play")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect("/")
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email:
            return render_template("login.html", emailHelp="Enter email")
        elif not password:
            return render_template("login.html", passwordHelp="Password cannot be empty")
        val = db.execute("SELECT id, username, password FROM users WHERE email = ?", (email, )).fetchone()
        if not val:
            return render_template("login.html", emailHelp="Email does not exist")
        if not verify_pass(password, val[2]):
            return render_template("login.html", passwordHelp="Invalid password")
        session["username"] = val[1]
        session["user_id"] = val[0]
        return redirect("/")
    return render_template("login.html")


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect("/")
    return render_template("profile.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

socketio.on_namespace(GameNameSpace(
    "/play",
    MATCHING_QUEUE,
    ACTIVE_ROOMS,
    socketio
))

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)
