"""Database mappings kept in the infrastructure layer."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (
        CheckConstraint("check_interval_seconds > 0", name="ck_sites_positive_interval"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    check_interval_seconds: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    check_results: Mapped[list["CheckResult"]] = relationship(
        back_populates="site", cascade="all, delete-orphan", passive_deletes=True
    )


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (
        CheckConstraint("response_ms >= 0", name="ck_check_results_nonnegative_response"),
        CheckConstraint("status_code BETWEEN 100 AND 599", name="ck_check_results_http_status"),
        Index("ix_check_results_site_id_checked_at", "site_id", "checked_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_up: Mapped[bool] = mapped_column(Boolean)
    status_code: Mapped[int | None] = mapped_column(Integer)
    response_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)

    site: Mapped[Site] = relationship(back_populates="check_results")
