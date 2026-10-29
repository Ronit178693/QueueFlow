# SQLAlchemy is an open-source Python library that serves as a comprehensive SQL toolkit and Object-Relational Mapper (ORM). It acts as a bridge between Python code and relational databases, allowing developers to interact with systems like PostgreSQL, MySQL, and SQLite using Pythonic expressions instead of writing raw SQL

from datetime import datetime
from typing import Any

# These are SQL column types and a helper
# tell the database what kind of column to create.
from sqlalchemy import DateTime, Integer, String, func
# A Postgres-specific column type for storing JSON data 
from sqlalchemy.dialects.postgresql import JSONB
# An optional Object-Relational Mapper built on top of the Core. It maps database tables directly to Python classes, allowing you to manage data entirely as Python objects.
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="queued",
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Determines when another worker may reclaim the job
    lease_expires_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
    )
    
    # Identifies the current claim, preventing an old worker from updating the job after losing ownership
    lease_token: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
