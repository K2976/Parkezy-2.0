from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import NotFound, ValidationFailed
from app.db.models import PlatformSetting
from app.domain.rules import PlatformRules
from app.infra.cache import Cache

CACHE_NS = "platform_settings"


class SettingsService:
    def __init__(self, session: AsyncSession, cache: Cache, clock: Clock, cache_ttl_seconds: int) -> None:
        self._session = session
        self._cache = cache
        self._clock = clock
        self._ttl = cache_ttl_seconds

    async def _load_raw(self) -> dict[str, Any]:
        rows = (await self._session.execute(select(PlatformSetting))).scalars().all()
        return {row.key: row.value for row in rows}

    async def rules(self) -> PlatformRules:
        raw = await self._cache.get_or_set(CACHE_NS, "all", self._ttl, self._load_raw)
        return PlatformRules.model_validate(raw)

    async def list_all(self) -> list[PlatformSetting]:
        return list((await self._session.execute(select(PlatformSetting).order_by(PlatformSetting.key))).scalars())

    async def update(self, changes: dict[str, Any]) -> PlatformRules:
        rows = {
            row.key: row
            for row in (
                await self._session.execute(
                    select(PlatformSetting).where(PlatformSetting.key.in_(changes)).with_for_update()
                )
            ).scalars()
        }
        unknown = set(changes) - set(rows)
        if unknown:
            raise NotFound("Unknown setting", details={"keys": sorted(unknown)})
        merged = await self._load_raw() | changes
        try:
            validated = PlatformRules.model_validate(merged)
        except ValidationError as e:
            raise ValidationFailed("Invalid setting value", details=e.errors(include_url=False)) from e
        now = self._clock.now()
        for key, value in changes.items():
            rows[key].value = value
            rows[key].updated_at = now
        await self._session.commit()
        await self._cache.bump(CACHE_NS)
        return validated
