# backend/models.py

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID

class User(SQLModel, table=True):
    id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4
        )
    )
    email: str = Field(..., index=True, unique=True)
    hashed_password: str
    can_apply_early: bool = Field(default=False)
    name: Optional[str] = Field(default=None, nullable=True)
    surname: Optional[str] = Field(default=None, nullable=True)
    leader: bool = Field(default=False)
    group: str = Field(default=None, nullable=True)
    age: int = Field(default=None, nullable=True)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    is_verified: bool = Field(default=False)

class Trail(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    description: str
    max_applicants: int

class Applicant(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("user.id"),
            nullable=False
        )
    )
    answers: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AfternoonActivity(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    description: str
    max_participants: int
    english_language: bool = Field(default=False)
    older_participants: bool = Field(default=False)
    day: Optional[str] = Field(default=None, nullable=True)

class MorningActivity(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    description: str
    max_participants: int
    english_language: bool = Field(default=False)
    older_participants: bool = Field(default=False)
    day: Optional[str] = Field(default=None, nullable=True)
    theme: Optional[str] = Field(default=None, nullable=True)

class ApplicationsMorningActivity(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("user.id"),
            nullable=False
        )
    )
    day: str = Field(default=None, nullable=False)
    answers: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ApplicationsAfternoonActivity(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("user.id"),
            nullable=False
        )
    )
    day: str = Field(default=None, nullable=False)
    answers: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SeasideDay(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    group: str = Field(default=None, nullable=True)
    day: str = Field(default=None, nullable=True)

class ProgramAddlInfo(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(default=None, nullable=True)
    theme: str = Field(default=None, nullable=True)
    priority: int = Field(default=0, nullable=True)
    category: int = Field(default=0, nullable=True)

class MorningProgramInfoApplicants(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(default=None, nullable=True)
    equipment: str = Field(default=None, nullable=True)
    location: str = Field(default=None, nullable=True)

class AfternoonProgramInfoApplicants(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(default=None, nullable=True)
    equipment: str = Field(default=None, nullable=True)
    location: str = Field(default=None, nullable=True)
