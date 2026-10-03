from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageCounter(Base):
    """How many requests one key made in one fixed window of one limit (services/limits.py).

    Holds no content: the key is a candidate id, the SHA-256 of a network address, or "all". No
    foreign key on purpose: deleting a candidate must not reset what their account already used.
    Rows are deleted once their window has ended.
    """

    __tablename__ = "usage_counters"
    __table_args__ = (CheckConstraint("count >= 1", name="count_positive"),)

    scope: Mapped[str] = mapped_column(String(40), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
