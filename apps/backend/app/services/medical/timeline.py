"""Timeline query and transformation utilities."""

from __future__ import annotations

from sqlalchemy import Select, asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_db_models import TimelineEvent


class TimelineService:
    async def list_events(
        self,
        db: AsyncSession,
        *,
        document_ids: list[str],
        event_types: list[str],
        start_date,
        end_date,
    ) -> list[TimelineEvent]:
        stmt: Select[tuple[TimelineEvent]] = select(TimelineEvent)
        if document_ids:
            stmt = stmt.where(TimelineEvent.document_id.in_(document_ids))
        if event_types:
            stmt = stmt.where(TimelineEvent.event_type.in_(event_types))
        if start_date is not None:
            stmt = stmt.where(TimelineEvent.event_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(TimelineEvent.event_date <= end_date)
        stmt = stmt.order_by(asc(TimelineEvent.event_date), asc(TimelineEvent.id))
        return list((await db.execute(stmt)).scalars().all())
