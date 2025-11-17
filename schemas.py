"""
Life Moves App - Database Schemas
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

class User(BaseModel):
    name: str
    email: EmailStr
    password_hash: str
    plan: Literal["free", "pro"] = "free"
    preferences: Optional[dict] = Field(default_factory=dict)
    streak: int = 0

class ContentItem(BaseModel):
    title: str
    description: Optional[str] = None
    category: Literal["art", "movement", "mindfulness"] = "mindfulness"
    tags: List[str] = Field(default_factory=list)
    tier: Literal["free", "pro"] = "free"
    duration_minutes: Optional[int] = None
    media_url: Optional[str] = None

class Task(BaseModel):
    user_id: str
    week: str
    task_type: str
    notes: Optional[str] = None
    completed: bool = True

class Checkin(BaseModel):
    user_id: str
    mood: Literal["great", "good", "ok", "low"] = "ok"
    note: Optional[str] = None
    date: datetime = Field(default_factory=datetime.utcnow)

class Squad(BaseModel):
    name: str
    description: Optional[str] = None
    owner_id: str
    members: List[str] = Field(default_factory=list)

class Post(BaseModel):
    user_id: str
    squad_id: Optional[str] = None
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Program(BaseModel):
    title: str
    description: Optional[str] = None
    weeks: int = 4
    tier: Literal["free", "pro"] = "free"

class Enrollment(BaseModel):
    user_id: str
    program_id: str
    progress_week: int = 0

class Feedback(BaseModel):
    user_id: Optional[str] = None
    message: str
    rating: Optional[int] = Field(None, ge=1, le=5)
