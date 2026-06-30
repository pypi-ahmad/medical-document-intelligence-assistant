"""Memory persistence and retention controls."""

from __future__ import annotations

import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.medical_db_models import MemoryEntry, User


class MemoryService:
    async def add_memory(
        self,
        db: AsyncSession,
        *,
        user: User,
        memory_type: str,
        memory_key: str,
        memory_value: dict,
        ttl_days: int | None,
    ) -> MemoryEntry:
        expires_at = None
        if ttl_days is None:
            ttl_days = settings.memory_retention_days
        if ttl_days > 0:
            expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=ttl_days)

        entry = MemoryEntry(
            user_id=user.id,
            memory_type=memory_type,
            memory_key=memory_key,
            memory_value=memory_value,
            expires_at=expires_at,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def list_memory(self, db: AsyncSession, *, user: User) -> list[MemoryEntry]:
        now = datetime.datetime.now(datetime.UTC)
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.user_id == user.id)
            .where((MemoryEntry.expires_at.is_(None)) | (MemoryEntry.expires_at > now))
            .order_by(MemoryEntry.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def clear_memory(self, db: AsyncSession, *, user: User, memory_type: str | None = None) -> int:
        stmt = delete(MemoryEntry).where(MemoryEntry.user_id == user.id)
        if memory_type:
            stmt = stmt.where(MemoryEntry.memory_type == memory_type)
        result = await db.execute(stmt)
        return int(result.rowcount or 0)

    async def purge_expired(self, db: AsyncSession) -> int:
        now = datetime.datetime.now(datetime.UTC)
        result = await db.execute(delete(MemoryEntry).where(MemoryEntry.expires_at <= now))
        return int(result.rowcount or 0)
