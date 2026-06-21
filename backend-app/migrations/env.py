from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app import config as app_config
from app import models  # noqa: F401  -- import so every table registers on the metadata

alembic_config = context.config

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = SQLModel.metadata


def _resolve_url() -> str:
    # Resolve at run time, not import time: a caller (test/runtime) may have set
    # POLINGO_DATABASE_URL or sqlalchemy.url on the cfg after env.py was imported.
    return alembic_config.get_main_option("sqlalchemy.url") or app_config.database_url()


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = dict(alembic_config.get_section(alembic_config.config_ini_section, {}))
    section["sqlalchemy.url"] = _resolve_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
