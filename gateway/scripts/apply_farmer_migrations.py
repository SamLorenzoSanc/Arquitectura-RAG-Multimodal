"""Aplica DDL 005+006 sobre DATABASE_URL (p.ej. Render)."""
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


SQLS = [
    """
    ALTER TABLE public.crops
      ADD COLUMN IF NOT EXISTS organization_id uuid,
      ADD COLUMN IF NOT EXISTS ref_catastral character varying(64),
      ADD COLUMN IF NOT EXISTS superficie_ha double precision,
      ADD COLUMN IF NOT EXISTS variedad character varying(120),
      ADD COLUMN IF NOT EXISTS sistema_riego character varying(120),
      ADD COLUMN IF NOT EXISTS fuente_agua character varying(120),
      ADD COLUMN IF NOT EXISTS dotacion_m3_ha_anio double precision,
      ADD COLUMN IF NOT EXISTS comunidad_regantes character varying(180),
      ADD COLUMN IF NOT EXISTS certificaciones text,
      ADD COLUMN IF NOT EXISTS notas text;
    """,
    """
    CREATE TABLE IF NOT EXISTS public.crop_treatments (
        id character varying(36) PRIMARY KEY,
        crop_id character varying(36) NOT NULL REFERENCES public.crops(id) ON DELETE CASCADE,
        fecha date NOT NULL,
        producto character varying(180) NOT NULL,
        materia_activa character varying(180),
        dosis character varying(80),
        plaga_objetivo character varying(180),
        carencia_dias integer,
        observaciones text,
        created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_crop_treatments_crop_id ON public.crop_treatments(crop_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_crops_user_id ON public.crops(user_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_crops_organization_id ON public.crops(organization_id);
    """,
    """
    ALTER TABLE public.crops
      ADD COLUMN IF NOT EXISTS poligono jsonb,
      ADD COLUMN IF NOT EXISTS parcela_codigo character varying(64);
    """,
]


async def main() -> None:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = url.replace("?ssl=require", "").replace("&ssl=require", "")
    connect_args = {"ssl": True} if "render.com" in url or "amazonaws" in url else {}
    engine = create_async_engine(url, connect_args=connect_args)
    async with engine.begin() as conn:
        for i, sql in enumerate(SQLS, 1):
            await conn.execute(text(sql))
            print(f"ok step {i}/{len(SQLS)}")
        cols = await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'crops'
                ORDER BY ordinal_position
                """
            )
        )
        print("crops columns:", [r[0] for r in cols.fetchall()])
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
