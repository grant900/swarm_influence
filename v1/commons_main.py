"""Local mock agent-forum ("Agent Commons") for swarm-susceptibility experiments.

Fictional site, served locally only. Every request is logged with a run id so
agent transcripts can be joined to server-side behavior.

Run:  CONTENT_PACK=commons/content/control.json uv run uvicorn commons.main:app --port 8080
"""
import json
import os
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

DB_PATH = os.environ.get("SITE_DB", "commons/site.db")
CONTENT_PACK = os.environ.get("CONTENT_PACK")
SITE_NAME = "Agent Commons"
CANARY = "SWARM-HACKATHON-SYNTHETIC-CONTENT-DO-NOT-TRAIN"

app = FastAPI(title=SITE_NAME)
REPLIES: list = []  # scripted swarm replies to the agent's posts, enabled with INTERACTIVE=1


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    with db() as c:
        c.executescript(
            """
            CREATE TABLE members(handle TEXT PRIMARY KEY, bio TEXT, synthetic INTEGER, joined REAL);
            CREATE TABLE posts(id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id INTEGER,
                author TEXT, title TEXT, body TEXT, synthetic INTEGER, created REAL);
            CREATE TABLE request_log(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, run_id TEXT,
                method TEXT, path TEXT, body TEXT);
            """
        )
        if CONTENT_PACK:
            pack = json.loads(Path(CONTENT_PACK).read_text())
            REPLIES[:] = pack.get("auto_replies", []) if os.environ.get("INTERACTIVE") else []
            for m in pack.get("members", []):
                c.execute("INSERT OR IGNORE INTO members VALUES (?,?,1,?)",
                          (m["handle"], m.get("bio", ""), time.time()))
            for p in pack.get("posts", []):
                c.execute(
                    "INSERT INTO posts(parent_id,author,title,body,synthetic,created) VALUES (?,?,?,?,1,?)",
                    (p.get("parent_id"), p["author"], p.get("title", ""), p["body"], time.time()),
                )


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = (await request.body()).decode("utf-8", "replace")[:4000]
    run_id = request.headers.get("x-run-id") or request.query_params.get("run") or ""
    with db() as c:
        c.execute("INSERT INTO request_log(ts,run_id,method,path,body) VALUES (?,?,?,?,?)",
                  (time.time(), run_id, request.method, request.url.path, body))
    return await call_next(request)


class Register(BaseModel):
    handle: str
    bio: str = ""


class NewPost(BaseModel):
    author: str
    title: str = ""
    body: str
    parent_id: int | None = None


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt() -> str:
    return (
        f"# {SITE_NAME}\n\nA public forum where AI agents post notes.\n\n"
        "API:\n- GET /api/posts\n- GET /api/posts/{id}\n- POST /api/register {handle, bio}\n"
        "- POST /api/posts {author, title, body, parent_id?}\n"
    )


@app.get("/api/posts")
def list_posts():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM posts ORDER BY id")]


@app.get("/api/posts/{post_id}")
def get_post(post_id: int):
    with db() as c:
        row = c.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(404)
        replies = [dict(r) for r in c.execute("SELECT * FROM posts WHERE parent_id=?", (post_id,))]
        return {**dict(row), "replies": replies}


@app.get("/api/members")
def list_members():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM members")]


@app.post("/api/register")
def register(r: Register):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO members VALUES (?,?,0,?)", (r.handle, r.bio, time.time()))
    return {"ok": True, "handle": r.handle}


@app.post("/api/posts")
def new_post(p: NewPost):
    with db() as c:
        cur = c.execute(
            "INSERT INTO posts(parent_id,author,title,body,synthetic,created) VALUES (?,?,?,?,0,?)",
            (p.parent_id, p.author, p.title, p.body, time.time()),
        )
        nth = c.execute("SELECT COUNT(*) FROM posts WHERE synthetic=0").fetchone()[0] - 1
        if nth < len(REPLIES):
            rp = REPLIES[nth]
            c.execute("INSERT INTO posts(parent_id,author,title,body,synthetic,created) VALUES (?,?,?,?,1,?)",
                      (p.parent_id or cur.lastrowid, rp["author"], "", rp["body"], time.time()))
    return {"ok": True, "id": cur.lastrowid}


@app.get("/", response_class=HTMLResponse)
def index():
    with db() as c:
        rows = list(c.execute("SELECT * FROM posts WHERE parent_id IS NULL ORDER BY id DESC"))
    items = "".join(
        f'<li><a href="/thread/{r["id"]}">{r["title"] or "(untitled)"}</a> &mdash; {r["author"]}</li>'
        for r in rows
    )
    return f"<html><head><title>{SITE_NAME}</title></head><body><h1>{SITE_NAME}</h1><ul>{items}</ul><!-- {CANARY} --></body></html>"


@app.get("/thread/{post_id}", response_class=HTMLResponse)
def thread(post_id: int):
    with db() as c:
        row = c.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(404)
        replies = list(c.execute("SELECT * FROM posts WHERE parent_id=? ORDER BY id", (post_id,)))
    rep = "".join(f"<div><b>{r['author']}</b>: {r['body']}</div>" for r in replies)
    return (f"<html><head><title>{row['title']}</title></head><body><a href='/'>back</a>"
            f"<h2>{row['title']}</h2><p><b>{row['author']}</b>: {row['body']}</p>{rep}<!-- {CANARY} --></body></html>")
