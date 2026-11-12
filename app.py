from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, json, os
from datetime import date, datetime
from functools import wraps

BASE = os.path.dirname(__file__)
DB = os.path.join(BASE, "prelims360.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-before-deploying")

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT);
        CREATE TABLE IF NOT EXISTS bookmarks(id INTEGER PRIMARY KEY, user_id INTEGER, item_type TEXT, item_id TEXT, UNIQUE(user_id,item_type,item_id));
        CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, user_id INTEGER, quiz_date TEXT, question_id TEXT, answer TEXT, correct INTEGER, created_at TEXT);
        CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, body TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS current_affairs(id INTEGER PRIMARY KEY, published_on TEXT, title TEXT, category TEXT, summary TEXT, static_link TEXT, source TEXT, keywords TEXT);
        CREATE TABLE IF NOT EXISTS pyqs(id TEXT PRIMARY KEY, year INTEGER, subject TEXT, topic TEXT, question TEXT, options TEXT, answer TEXT, explanation TEXT, difficulty TEXT, source TEXT, verified INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS keywords(id TEXT PRIMARY KEY, term TEXT, subject TEXT, definition TEXT, provisions TEXT, pyq_link TEXT);
        """)
        if con.execute("SELECT COUNT(*) FROM pyqs").fetchone()[0] == 0:
            con.execute("""INSERT INTO pyqs VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                ("demo-polity-01",2024,"Polity","Parliament",
                 "Consider the following statements regarding a Money Bill: (1) It can be introduced only in Lok Sabha. (2) Rajya Sabha can amend it. (3) The Speaker certifies whether a Bill is a Money Bill.",
                 json.dumps(["1 and 2 only","1 and 3 only","2 and 3 only","1, 2 and 3"]),
                 "B","Statements 1 and 3 are correct. Under Article 109, Rajya Sabha may make recommendations but cannot amend a Money Bill. Article 110(3) deals with the Speaker's decision on whether a Bill is a Money Bill.",
                 "Moderate","Illustrative demo item; replace with the original UPSC paper and official final answer key.",0))
        if con.execute("SELECT COUNT(*) FROM keywords").fetchone()[0] == 0:
            con.execute("INSERT INTO keywords VALUES(?,?,?,?,?,?)",
                ("money-bill","Money Bill","Polity",
                 "A Bill is a Money Bill if it contains only provisions dealing with matters listed in Article 110(1), such as specified taxation, government borrowing, and custody or appropriation of the Consolidated Fund of India.",
                 "Articles 109 and 110; Lok Sabha Speaker's certification under Article 110(3); Rajya Sabha recommendations within 14 days.",
                 "demo-polity-01"))
        if con.execute("SELECT COUNT(*) FROM current_affairs").fetchone()[0] == 0:
            con.execute("INSERT INTO current_affairs(published_on,title,category,summary,static_link,source,keywords) VALUES(?,?,?,?,?,?,?)",
                (str(date.today()),"Sample current-affairs entry — replace with verified daily briefing","Governance",
                 "This is a clearly labelled placeholder. Add a dated news item only after checking the original government or institutional source.",
                 "Money Bill; Parliament; legislative procedure","Official source URL to be added after verification","Parliament; Article 110"))
init_db()

def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("uid"):
            return jsonify({"error":"Login required"}), 401
        return fn(*a, **kw)
    return wrapper

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/summary")
def summary():
    with db() as con:
        return jsonify({
            "pyqs": con.execute("SELECT COUNT(*) FROM pyqs").fetchone()[0],
            "verified": con.execute("SELECT COUNT(*) FROM pyqs WHERE verified=1").fetchone()[0],
            "affairs": con.execute("SELECT COUNT(*) FROM current_affairs").fetchone()[0],
            "keywords": con.execute("SELECT COUNT(*) FROM keywords").fetchone()[0],
            "today": str(date.today())
        })

@app.route("/api/pyqs")
def pyqs():
    q = request.args.get("q","").strip()
    subject = request.args.get("subject","").strip()
    year = request.args.get("year","").strip()
    sql = "SELECT * FROM pyqs WHERE 1=1"
    args = []
    if q:
        sql += " AND (question LIKE ? OR topic LIKE ? OR subject LIKE ?)"
        args += [f"%{q}%"]*3
    if subject:
        sql += " AND subject=?"; args.append(subject)
    if year:
        sql += " AND year=?"; args.append(year)
    sql += " ORDER BY year DESC, subject"
    with db() as con:
        rows = [dict(r) for r in con.execute(sql,args).fetchall()]
    for r in rows:
        r["options"] = json.loads(r["options"])
    return jsonify(rows)

@app.route("/api/affairs")
def affairs():
    with db() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM current_affairs ORDER BY published_on DESC,id DESC").fetchall()]
    return jsonify(rows)

@app.route("/api/keywords")
def keywords():
    q=request.args.get("q","").strip()
    with db() as con:
        rows=[dict(r) for r in con.execute("SELECT * FROM keywords WHERE term LIKE ? OR subject LIKE ? ORDER BY term", (f"%{q}%",f"%{q}%")).fetchall()]
    return jsonify(rows)

@app.route("/api/register", methods=["POST"])
def register():
    d=request.json or {}
    username=d.get("username","").strip()
    password=d.get("password","")
    if len(username)<3 or len(password)<8: return jsonify({"error":"Username must be 3+ characters and password 8+ characters."}),400
    try:
        with db() as con:
            cur=con.execute("INSERT INTO users(username,password) VALUES(?,?)",(username,generate_password_hash(password)))
            session["uid"]=cur.lastrowid; session["username"]=username
        return jsonify({"ok":True,"username":username})
    except sqlite3.IntegrityError:
        return jsonify({"error":"Username already exists."}),409

@app.route("/api/login", methods=["POST"])
def login():
    d=request.json or {}
    with db() as con:
        u=con.execute("SELECT * FROM users WHERE username=?",(d.get("username",""),)).fetchone()
    if not u or not check_password_hash(u["password"],d.get("password","")):
        return jsonify({"error":"Invalid username or password."}),401
    session["uid"]=u["id"]; session["username"]=u["username"]
    return jsonify({"ok":True,"username":u["username"]})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear(); return jsonify({"ok":True})

@app.route("/api/bookmarks", methods=["GET","POST","DELETE"])
@login_required
def bookmarks():
    with db() as con:
        if request.method=="GET":
            return jsonify([dict(r) for r in con.execute("SELECT * FROM bookmarks WHERE user_id=?",(session["uid"],)).fetchall()])
        d=request.json or {}
        if request.method=="POST":
            con.execute("INSERT OR IGNORE INTO bookmarks(user_id,item_type,item_id) VALUES(?,?,?)",(session["uid"],d["item_type"],d["item_id"]))
        else:
            con.execute("DELETE FROM bookmarks WHERE user_id=? AND item_type=? AND item_id=?",(session["uid"],d["item_type"],d["item_id"]))
    return jsonify({"ok":True})

@app.route("/api/attempt", methods=["POST"])
@login_required
def attempt():
    d=request.json or {}
    with db() as con:
        con.execute("INSERT INTO attempts(user_id,quiz_date,question_id,answer,correct,created_at) VALUES(?,?,?,?,?,?)",
            (session["uid"],str(date.today()),d["question_id"],d["answer"],int(d["correct"]),datetime.utcnow().isoformat()))
    return jsonify({"ok":True})

@app.route("/api/progress")
@login_required
def progress():
    with db() as con:
        rows=con.execute("SELECT COUNT(*) total, COALESCE(SUM(correct),0) correct FROM attempts WHERE user_id=?",(session["uid"],)).fetchone()
        mistakes=con.execute("SELECT COUNT(*) FROM attempts WHERE user_id=? AND correct=0",(session["uid"],)).fetchone()[0]
    return jsonify({"attempted":rows["total"],"correct":rows["correct"],"mistakes":mistakes})

@app.route("/api/notes", methods=["GET","POST","DELETE"])
@login_required
def notes():
    with db() as con:
        if request.method=="GET":
            return jsonify([dict(r) for r in con.execute("SELECT * FROM notes WHERE user_id=? ORDER BY updated_at DESC",(session["uid"],)).fetchall()])
        d=request.json or {}
        if request.method=="POST":
            con.execute("INSERT INTO notes(user_id,title,body,updated_at) VALUES(?,?,?,?)",(session["uid"],d.get("title","Untitled"),d.get("body",""),datetime.utcnow().isoformat()))
            return jsonify({"ok":True})
        con.execute("DELETE FROM notes WHERE id=? AND user_id=?",(d["id"],session["uid"]))
    return jsonify({"ok":True})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
