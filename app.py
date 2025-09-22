from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os, time

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATA_DIR = "data"
CHATROOM_DIR = "chatrooms"
PFP_DIR = "pfp"

ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.txt")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHATROOM_DIR, exist_ok=True)
os.makedirs(PFP_DIR, exist_ok=True)

# --- Helpers ---
def load_accounts():
    accounts = {}
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r") as f:
            for line in f:
                if ":" in line:
                    user, pwd = line.strip().split(":", 1)
                    accounts[user] = pwd
    return accounts

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w") as f:
        for user, pwd in accounts.items():
            f.write(f"{user}:{pwd}\n")

def chatroom_path(roomname):
    return os.path.join(CHATROOM_DIR, f"{roomname}.txt")

def allowed_path(roomname):
    return os.path.join(CHATROOM_DIR, f"{roomname}_allowed.txt")

def load_allowed(roomname):
    path = allowed_path(roomname)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def save_allowed(roomname, allowed):
    with open(allowed_path(roomname), "w") as f:
        for user in allowed:
            f.write(user + "\n")

# --- Routes ---

@app.route("/")
def home():
    return render_template("home.html", logged_in="username" in session)

@app.route("/account/signinup", methods=["GET", "POST"])
def signinup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        accounts = load_accounts()
        if username in accounts:
            if accounts[username] == password:
                session["username"] = username
                return redirect(url_for("account"))
            else:
                return "Incorrect password"
        else:
            accounts[username] = password
            save_accounts(accounts)
            session["username"] = username
            return redirect(url_for("account"))
    return render_template("signinup.html")

@app.route("/account/")
def account():
    if "username" not in session:
        return redirect(url_for("signinup"))
    return render_template("account.html", username=session["username"])

@app.route("/account/delete")
def delete_account():
    if "username" not in session:
        return redirect(url_for("signinup"))
    accounts = load_accounts()
    user = session["username"]
    if user in accounts:
        del accounts[user]
        save_accounts(accounts)
    pfp_path = os.path.join(PFP_DIR, f"{user}.jpg")
    if os.path.exists(pfp_path):
        os.remove(pfp_path)
    session.clear()
    return redirect(url_for("home"))

@app.route("/account/upload", methods=["POST"])
def upload_pfp():
    if "username" not in session:
        return redirect(url_for("signinup"))
    file = request.files["pfp"]
    if file and file.filename.lower().endswith(".jpg"):
        file.save(os.path.join(PFP_DIR, f"{session['username']}.jpg"))
    return redirect(url_for("account"))

@app.route("/pfp/<filename>")
def serve_pfp(filename):
    return send_from_directory(PFP_DIR, filename)

# --- Public Chatroom ---
@app.route("/public/", methods=["GET", "POST"])
def public_chat():
    return chatroom("public")

# --- General Chatroom Function ---
@app.route("/room/<roomname>/", methods=["GET", "POST"])
def chatroom(roomname):
    if "username" not in session:
        return redirect(url_for("signinup"))

    allowed = load_allowed(roomname)
    if allowed and session["username"] not in allowed:
        return "You are not allowed in this chatroom."

    if request.method == "POST":
        msg = request.form.get("message")
        if msg.strip():
            with open(chatroom_path(roomname), "a") as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp}|{session['username']}|{msg}\n")

    messages = []
    if os.path.exists(chatroom_path(roomname)):
        with open(chatroom_path(roomname), "r") as f:
            for line in f:
                timestamp, user, text = line.strip().split("|", 2)
                messages.append((timestamp, user, text))
    return render_template("chat.html", messages=messages, username=session["username"], roomname=roomname)

# --- Create New Chatroom ---
@app.route("/create/", methods=["GET", "POST"])
def create_chatroom():
    if "username" not in session:
        return redirect(url_for("signinup"))

    if request.method == "POST":
        roomname = request.form.get("roomname").strip()
        allowed_users = request.form.get("allowed").split(",")
        allowed_users = [u.strip() for u in allowed_users if u.strip()]
        if roomname:
            # initialize empty chat log
            open(chatroom_path(roomname), "a").close()
            save_allowed(roomname, allowed_users)
            return redirect(url_for("chatroom", roomname=roomname))

    return render_template("create.html")
