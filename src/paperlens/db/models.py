from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from paperlens.db.database import Base


# Database step: the users table (the password is stored only as an argon2 hash)
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


# Database step: the documents table (one row for every PDF a user uploaded)
class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("user_id", "file_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64))
    num_chunks: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
