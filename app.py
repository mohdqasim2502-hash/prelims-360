import os
from datetime import date, datetime
from functools import wraps

from flask import Flask, jsonify, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_, case
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is missing. Set it in the hosting environment.")

database_url = os.environ.get("DATABASE_URL", "").strip()
if not database_url:
    raise RuntimeError("DATABASE_URL is missing. Add your Neon PostgreSQL connection string in Render Environment.")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config.update(
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 280},
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type = db.Column(db.String(40), nullable=False)
    item_id = db.Column(db.String(160), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "item_type", "item_id"),)

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_date = db.Column(db.String(10), nullable=False)
    question_id = db.Column(db.String(100), nullable=False)
    answer = db.Column(db.String(20), nullable=False)
    correct = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class CurrentAffair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    published_on = db.Column(db.String(10), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="General")
    summary = db.Column(db.Text, nullable=False, default="")
    static_link = db.Column(db.Text, nullable=False, default="")
    source = db.Column(db.Text, nullable=False, default="")
    keywords = db.Column(db.Text, nullable=False, default="")

class PYQ(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    subject = db.Column(db.String(80), nullable=False, index=True)
    topic = db.Column(db.String(160), nullable=False, default="")
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)
    answer = db.Column(db.String(8), nullable=False)
    explanation = db.Column(db.Text, nullable=False, default="")
    difficulty = db.Column(db.String(30), nullable=False, default="Unclassified")
    source = db.Column(db.Text, nullable=False, default="")
    verified = db.Column(db.Boolean, nullable=False, default=False)

class Keyword(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    term = db.Column(db.String(160), nullable=False, index=True)
    subject = db.Column(db.String(80), nullable=False, index=True)
    definition = db.Column(db.Text, nullable=False)
    provisions = db.Column(db.Text, nullable=False, default="")
    pyq_link = db.Column(db.String(100), nullable=False, default="")

class PlannerTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    task_date = db.Column(db.String(10), nullable=False, index=True)
    subject = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    minutes = db.Column(db.Integer, nullable=False, default=60)
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    done = db.Column(db.Boolean, nullable=False, default=False)

class Revision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = db.Column(db.String(300), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    due_date = db.Column(db.String(10), nullable=False, index=True)
    done = db.Column(db.Boolean, nullable=False, default=False)

class Mistake(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = db.Column(db.String(80), nullable=False)
    error_type = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    correction = db.Column(db.Text, nullable=False, default="")
    reviewed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

def require_login(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("uid"):
            return jsonify(error="Please sign in to sync your study data."), 401
        return fn(*args, **kwargs)
    return wrapped

def owned(model, row_id):
    return model.query.filter_by(id=row_id, user_id=session["uid"]).first()

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/health")
def health():
    try:
        db.session.execute(db.select(1))
        return jsonify(status="ok", database="connected")
    except Exception:
        app.logger.exception("Health check database failure")
        return jsonify(status="error"), 503

@app.get("/api/summary")
def summary():
    return jsonify(
        pyqs=PYQ.query.count(),
        verified=PYQ.query.filter_by(verified=True).count(),
        affairs=CurrentAffair.query.count(),
        keywords=Keyword.query.count(),
        today=str(date.today()),
    )

@app.get("/api/pyqs")
def pyqs():
    q = request.args.get("q", "").strip()
    subject = request.args.get("subject", "").strip()
    year = request.args.get("year", "").strip()
    query = PYQ.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(PYQ.question.ilike(like), PYQ.topic.ilike(like), PYQ.subject.ilike(like)))
    if subject:
        query = query.filter_by(subject=subject)
    if year.isdigit():
        query = query.filter_by(year=int(year))
    rows = query.order_by(PYQ.year.desc(), PYQ.subject).limit(500).all()
    return jsonify([{
        "id": x.id, "year": x.year, "subject": x.subject, "topic": x.topic,
        "question": x.question, "options": x.options, "answer": x.answer,
        "explanation": x.explanation, "difficulty": x.difficulty,
        "source": x.source, "verified": x.verified
    } for x in rows])

@app.get("/api/affairs")
def affairs():
    rows = CurrentAffair.query.order_by(CurrentAffair.published_on.desc(), CurrentAffair.id.desc()).limit(300).all()
    return jsonify([{"id":x.id,"published_on":x.published_on,"title":x.title,"category":x.category,
        "summary":x.summary,"static_link":x.static_link,"source":x.source,"keywords":x.keywords} for x in rows])

@app.get("/api/keywords")
def keywords():
    q = request.args.get("q", "").strip()
    query = Keyword.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Keyword.term.ilike(like), Keyword.subject.ilike(like), Keyword.definition.ilike(like)))
    rows = query.order_by(Keyword.term).limit(500).all()
    return jsonify([{"id":x.id,"term":x.term,"subject":x.subject,"definition":x.definition,
        "provisions":x.provisions,"pyq_link":x.pyq_link} for x in rows])

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if len(username) < 3 or len(username) > 40 or len(password) < 10:
        return jsonify(error="Username must be 3–40 characters and password at least 10 characters."), 400
    if User.query.filter_by(username=username).first():
        return jsonify(error="This username already has an account. Please sign in instead."), 409
    user = User(username=username, password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    session.clear()
    session.permanent = True
    session["uid"], session["username"] = user.id, user.username
    return jsonify(ok=True, username=user.username)

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify(error="Username or password is incorrect."), 401
    session.clear()
    session.permanent = True
    session["uid"], session["username"] = user.id, user.username
    return jsonify(ok=True, username=user.username)

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@app.get("/api/me")
def me():
    return jsonify(logged_in=bool(session.get("uid")), username=session.get("username"))

@app.route("/api/bookmarks", methods=["GET", "POST", "DELETE"])
@require_login
def bookmarks():
    if request.method == "GET":
        rows = Bookmark.query.filter_by(user_id=session["uid"]).order_by(Bookmark.id.desc()).all()
        return jsonify([{"id":x.id,"item_type":x.item_type,"item_id":x.item_id} for x in rows])
    data = request.get_json(silent=True) or {}
    item_type, item_id = str(data.get("item_type","topic"))[:40], str(data.get("item_id","")).strip()[:160]
    if not item_id:
        return jsonify(error="Bookmark item is required."), 400
    row = Bookmark.query.filter_by(user_id=session["uid"], item_type=item_type, item_id=item_id).first()
    if request.method == "POST" and not row:
        db.session.add(Bookmark(user_id=session["uid"], item_type=item_type, item_id=item_id))
    elif request.method == "DELETE" and row:
        db.session.delete(row)
    db.session.commit()
    return jsonify(ok=True)

@app.route("/api/notes", methods=["GET", "POST", "DELETE"])
@require_login
def notes():
    if request.method == "GET":
        rows = Note.query.filter_by(user_id=session["uid"]).order_by(Note.updated_at.desc()).all()
        return jsonify([{"id":x.id,"title":x.title,"body":x.body,"updated_at":x.updated_at.isoformat()} for x in rows])
    data = request.get_json(silent=True) or {}
    if request.method == "POST":
        title, body = str(data.get("title","")).strip()[:200], str(data.get("body",""))
        if not title or not body.strip():
            return jsonify(error="A title and note content are required."), 400
        note = Note(user_id=session["uid"], title=title, body=body)
        db.session.add(note)
        db.session.commit()
        return jsonify(ok=True, id=note.id)
    note = owned(Note, data.get("id"))
    if note:
        db.session.delete(note)
        db.session.commit()
    return jsonify(ok=True)

@app.post("/api/attempt")
@require_login
def attempt():
    data = request.get_json(silent=True) or {}
    qid = str(data.get("question_id",""))[:100]
    answer = str(data.get("answer",""))[:20]
    if not qid or not answer:
        return jsonify(error="Question and answer are required."), 400
    db.session.add(Attempt(user_id=session["uid"], quiz_date=str(date.today()), question_id=qid,
        answer=answer, correct=bool(data.get("correct")), created_at=datetime.utcnow()))
    db.session.commit()
    return jsonify(ok=True)

@app.get("/api/progress")
@require_login
def progress():
    q = db.session.query(func.count(Attempt.id), func.coalesce(func.sum(case((Attempt.correct.is_(True), 1), else_=0)), 0)).filter_by(user_id=session["uid"]).one()
    mistakes = Attempt.query.filter_by(user_id=session["uid"], correct=False).count()
    return jsonify(attempted=q[0], correct=int(q[1]), mistakes=mistakes)

@app.route("/api/planner", methods=["GET","POST","PATCH","DELETE"])
@require_login
def planner():
    uid = session["uid"]
    if request.method == "GET":
        rows = PlannerTask.query.filter_by(user_id=uid).order_by(PlannerTask.task_date, PlannerTask.id).all()
        return jsonify([{"id":x.id,"date":x.task_date,"subject":x.subject,"title":x.title,"minutes":x.minutes,"priority":x.priority,"done":x.done} for x in rows])
    data = request.get_json(silent=True) or {}
    if request.method == "POST":
        if not str(data.get("title","")).strip(): return jsonify(error="Task title is required."), 400
        x = PlannerTask(user_id=uid, task_date=str(data.get("date",date.today()))[:10], subject=str(data.get("subject","General"))[:80],
            title=str(data["title"]).strip()[:300], minutes=max(1,min(1440,int(data.get("minutes",60)))),
            priority=str(data.get("priority","Medium"))[:20], done=False)
        db.session.add(x); db.session.commit(); return jsonify(ok=True,id=x.id)
    x = owned(PlannerTask, data.get("id"))
    if x:
        if request.method == "DELETE": db.session.delete(x)
        else: x.done = bool(data.get("done"))
        db.session.commit()
    return jsonify(ok=True)

@app.route("/api/revisions", methods=["GET","POST","PATCH","DELETE"])
@require_login
def revisions():
    uid=session["uid"]
    if request.method=="GET":
        rows=Revision.query.filter_by(user_id=uid).order_by(Revision.due_date,Revision.id).all()
        return jsonify([{"id":x.id,"topic":x.topic,"subject":x.subject,"date":x.due_date,"done":x.done} for x in rows])
    data=request.get_json(silent=True) or {}
    if request.method=="POST":
        topic=str(data.get("topic","")).strip()
        if not topic:return jsonify(error="Topic is required."),400
        x=Revision(user_id=uid,topic=topic[:300],subject=str(data.get("subject","General"))[:80],due_date=str(data.get("date",date.today()))[:10])
        db.session.add(x);db.session.commit();return jsonify(ok=True,id=x.id)
    x=owned(Revision,data.get("id"))
    if x:
        if request.method=="DELETE":db.session.delete(x)
        else:x.done=bool(data.get("done"))
        db.session.commit()
    return jsonify(ok=True)

@app.route("/api/mistakes", methods=["GET","POST","PATCH","DELETE"])
@require_login
def mistakes():
    uid=session["uid"]
    if request.method=="GET":
        rows=Mistake.query.filter_by(user_id=uid).order_by(Mistake.created_at.desc()).all()
        return jsonify([{"id":x.id,"subject":x.subject,"type":x.error_type,"title":x.title,"fix":x.correction,"done":x.reviewed,"date":x.created_at.date().isoformat()} for x in rows])
    data=request.get_json(silent=True) or {}
    if request.method=="POST":
        title=str(data.get("title","")).strip()
        if not title:return jsonify(error="Mistake title is required."),400
        x=Mistake(user_id=uid,subject=str(data.get("subject","General"))[:80],error_type=str(data.get("type","Conceptual"))[:80],title=title[:300],correction=str(data.get("fix","")))
        db.session.add(x);db.session.commit();return jsonify(ok=True,id=x.id)
    x=owned(Mistake,data.get("id"))
    if x:
        if request.method=="DELETE":db.session.delete(x)
        else:x.reviewed=bool(data.get("done"))
        db.session.commit()
    return jsonify(ok=True)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
