from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from tenancy.adapters.outbound.postgres import PostgresTenancyRepository


@dataclass
class TenancyContainer:
    repo: PostgresTenancyRepository


def build_tenancy_container(db: AsyncSession) -> TenancyContainer:
    return TenancyContainer(repo=PostgresTenancyRepository(db))
