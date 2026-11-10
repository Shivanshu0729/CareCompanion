from __future__ import annotations

from pathlib import Path

from config.settings import PROJECT_ROOT, get_settings


SCHEMA_PATH = PROJECT_ROOT / "migrations" / "001_schema.sql"


def load_schema_sql() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8")


def apply_schema() -> None:
    settings = get_settings()
    if not settings.database_url.strip():
        raise RuntimeError(
            "DATABASE_URL is not configured. Apply migrations/001_schema.sql in the Supabase SQL editor instead."
        )
    import psycopg

    sql = load_schema_sql()
    with psycopg.connect(settings.database_url) as connection:
        connection.execute(sql)
        connection.commit()


if __name__ == "__main__":
    apply_schema()
    print(f"Applied schema from {SCHEMA_PATH}")
