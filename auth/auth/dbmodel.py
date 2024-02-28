from sqlmodel import SQLModel, Field, Column, TEXT
from pydantic import EmailStr
from datetime import datetime
import uuid


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    id: int = Field(default=None, primary_key=True)
    public_id: str = Field(unique=True, default_factory=uuid.uuid4)
    fullname: str
    email: EmailStr = Field(sa_column=Column(TEXT))  # used as login for simplicity
    role: str
    password_hash: str
    created_at: datetime
    updated_at: datetime