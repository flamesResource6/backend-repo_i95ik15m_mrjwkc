import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import User, ContentItem, Task, Checkin, Squad, Post, Program, Enrollment, Feedback

app = FastAPI(title="Life Moves API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility
class IdResponse(BaseModel):
    id: str


def collection(name: str):
    return db[name]


@app.get("/")
def read_root():
    return {"name": "Life Moves API", "status": "ok"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# Auth (MVP: email + simple session token stored in user document)
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/signup", response_model=IdResponse)
def signup(payload: SignupRequest):
    if not db:
        raise HTTPException(status_code=500, detail="Database unavailable")
    existing = collection("user").find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    # Simple hash substitute for MVP (NOT for production)
    password_hash = f"sha1::{abs(hash(payload.password))}"
    user = User(name=payload.name, email=payload.email, password_hash=password_hash)
    new_id = create_document("user", user)
    return {"id": new_id}


@app.post("/auth/login")
def login(payload: LoginRequest):
    u = collection("user").find_one({"email": payload.email})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    expected = u.get("password_hash")
    if expected != f"sha1::{abs(hash(payload.password))}":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # naive session token
    token = f"tok_{abs(hash(payload.email + payload.password))}"
    collection("user").update_one({"_id": u["_id"]}, {"$set": {"session_token": token}})
    return {"token": token, "user": {"id": str(u["_id"]), "name": u.get("name"), "email": u.get("email"), "plan": u.get("plan", "free")}}


# Library endpoints
@app.get("/library", response_model=List[ContentItem])
def list_content(category: Optional[str] = None, q: Optional[str] = None, tier: Optional[str] = None):
    filt = {}
    if category:
        filt["category"] = category
    if tier:
        filt["tier"] = tier
    items = get_documents("contentitem", filt)  # ContentItem -> collection "contentitem"
    # simple search filter
    if q:
        ql = q.lower()
        items = [i for i in items if ql in i.get("title", "").lower() or ql in (i.get("description", "").lower())]
    # remove _id for clean response
    for i in items:
        i.pop("_id", None)
    return items


@app.post("/library", response_model=IdResponse)
def add_content(item: ContentItem):
    new_id = create_document("contentitem", item)
    return {"id": new_id}


# Progress: weekly tasks
@app.post("/tasks", response_model=IdResponse)
def submit_task(task: Task):
    new_id = create_document("task", task)
    return {"id": new_id}


@app.get("/tasks")
def list_tasks(user_id: str, week: Optional[str] = None):
    filt = {"user_id": user_id}
    if week:
        filt["week"] = week
    tasks = get_documents("task", filt)
    for t in tasks:
        t["id"] = str(t.pop("_id")) if t.get("_id") else None
    return tasks


# Daily check-ins
@app.post("/checkins", response_model=IdResponse)
def create_checkin(checkin: Checkin):
    new_id = create_document("checkin", checkin)
    return {"id": new_id}


@app.get("/checkins")
def list_checkins(user_id: str, limit: int = 30):
    docs = get_documents("checkin", {"user_id": user_id}, limit=limit)
    for d in docs:
        d["id"] = str(d.pop("_id")) if d.get("_id") else None
    return docs


# Squads & posts (community basics)
@app.post("/squads", response_model=IdResponse)
def create_squad(squad: Squad):
    if squad.owner_id not in squad.members:
        squad.members.append(squad.owner_id)
    new_id = create_document("squad", squad)
    return {"id": new_id}


@app.get("/squads")
def list_squads(member_id: Optional[str] = None):
    filt = {"members": {"$in": [member_id]}} if member_id else {}
    docs = get_documents("squad", filt)
    for d in docs:
        d["id"] = str(d.pop("_id")) if d.get("_id") else None
    return docs


@app.post("/posts", response_model=IdResponse)
def create_post(post: Post):
    new_id = create_document("post", post)
    return {"id": new_id}


@app.get("/posts")
def list_posts(squad_id: Optional[str] = None, user_id: Optional[str] = None, limit: int = 50):
    filt = {}
    if squad_id:
        filt["squad_id"] = squad_id
    if user_id:
        filt["user_id"] = user_id
    docs = get_documents("post", filt, limit=limit)
    for d in docs:
        d["id"] = str(d.pop("_id")) if d.get("_id") else None
    return docs


# Programs & enrollments
@app.post("/programs", response_model=IdResponse)
def create_program(program: Program):
    new_id = create_document("program", program)
    return {"id": new_id}


@app.get("/programs", response_model=List[Program])
def list_programs(tier: Optional[str] = None):
    filt = {"tier": tier} if tier else {}
    docs = get_documents("program", filt)
    for d in docs:
        d.pop("_id", None)
    return docs


@app.post("/enroll", response_model=IdResponse)
def enroll_user(enrollment: Enrollment):
    new_id = create_document("enrollment", enrollment)
    return {"id": new_id}


@app.get("/enrollments")
def list_enrollments(user_id: str):
    docs = get_documents("enrollment", {"user_id": user_id})
    for d in docs:
        d["id"] = str(d.pop("_id")) if d.get("_id") else None
    return docs


# Feedback
@app.post("/feedback", response_model=IdResponse)
def submit_feedback(feedback: Feedback):
    new_id = create_document("feedback", feedback)
    return {"id": new_id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
