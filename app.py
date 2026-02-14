from __future__ import annotations

import random
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

MAX_MESSAGES = 120
ACTIVE_WINDOW_SECONDS = 150


@dataclass
class Message:
    name: str
    text: str
    timestamp: float


messages: Deque[Message] = deque(maxlen=MAX_MESSAGES)
last_seen: dict[str, float] = defaultdict(float)


def active_users() -> list[str]:
    now = time.time()
    users = [name for name, seen in last_seen.items() if now - seen <= ACTIVE_WINDOW_SECONDS]
    users.sort(key=str.lower)
    return users


def ensure_captcha() -> None:
    if "captcha_question" in session:
        return
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    session["captcha_answer"] = str(a + b)
    session["captcha_question"] = f"{a} + {b}"


@app.get("/")
def index():
    if not session.get("verified"):
        ensure_captcha()
        return redirect(url_for("verify"))

    username = session.get("username")
    if not username:
        return redirect(url_for("join"))

    last_seen[username] = time.time()

    everyone = active_users()
    random.shuffle(everyone)
    split = len(everyone) // 2
    left_users = everyone[:split]
    right_users = everyone[split:]

    return render_template(
        "chat.html",
        username=username,
        messages=list(messages),
        left_users=left_users,
        right_users=right_users,
    )


@app.route("/verify", methods=["GET", "POST"])
def verify():
    ensure_captcha()
    error = None

    if request.method == "POST":
        answer = (request.form.get("answer") or "").strip()
        if answer == session.get("captcha_answer"):
            session["verified"] = True
            session.pop("captcha_answer", None)
            session.pop("captcha_question", None)
            return redirect(url_for("join"))
        error = "Verification failed. Try again."
        session.pop("captcha_question", None)
        ensure_captcha()

    return render_template("verify.html", error=error, question=session["captcha_question"])


@app.route("/join", methods=["GET", "POST"])
def join():
    if not session.get("verified"):
        return redirect(url_for("verify"))

    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username:
            error = "Pick any name so your friends can recognize you."
        else:
            session["username"] = username[:24]
            session["password"] = password
            last_seen[session["username"]] = time.time()
            return redirect(url_for("index"))

    return render_template("join.html", error=error)


@app.post("/send")
def send_message():
    if not session.get("verified") or not session.get("username"):
        return redirect(url_for("join"))

    text = (request.form.get("message") or "").strip()
    if text:
        username = session["username"]
        last_seen[username] = time.time()
        messages.append(Message(name=username, text=text[:300], timestamp=time.time()))

    return redirect(url_for("index"))


@app.post("/logout")
def logout():
    username = session.get("username")
    if username:
        last_seen.pop(username, None)

    session.clear()
    return redirect(url_for("verify"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
