import typing as t
import uuid

from sqlalchemy import Column, DateTime, func
# from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import as_declarative, declared_attr
from sqlalchemy.dialects.postgresql import UUID

class_registry: t.Dict = {}


@as_declarative(class_registry=class_registry)
class Base:
    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        unique=True,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), default=None, nullable=True)

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    def __repr__(self) -> str:
        """
        Generic repr showing class name and all non-relationship column values.
        Skips lazy-loaded relationships to avoid triggering accidental DB calls.
        """
        cols = {
            c.key: getattr(self, c.key)
            for c in self.__table__.columns
        }
        col_str = ", ".join(f"{k}={v!r}" for k, v in cols.items())
        return f"<{self.__class__.__name__}({col_str})>"

    def __str__(self) -> str:
        """
        Human-readable string — class name, id, and created_at only.
        Safe to use in logs without exposing all fields.
        """
        return (
            f"{self.__class__.__name__}("
            f"id={self.id}, "
            f"created_at={self.created_at})"
        )

    def to_dict(self) -> dict:
        """
        Serialise all column values to a plain dict.
        Useful for logging, debugging endpoints, and test assertions.
        Does not include relationships.
        """
        return {
            c.key: getattr(self, c.key)
            for c in self.__table__.columns
        }
