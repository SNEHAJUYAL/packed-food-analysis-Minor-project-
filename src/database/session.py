"""Engine and session from DATABASE_URL (PostgreSQL). Secrets come only from the environment."""
from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseNotConfigured(RuntimeError):
    pass


def database_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL")
    if url and url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@lru_cache(maxsize=4)
def get_engine(url: Optional[str] = None) -> Engine:
    url = url or database_url()
    if not url:
        raise DatabaseNotConfigured("DATABASE_URL is not set. See .env.example.")
    return create_engine(url, pool_pre_ping=True, future=True)


def session_factory(engine: Optional[Engine] = None) -> sessionmaker:
    return sessionmaker(bind=engine or get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope(engine: Optional[Engine] = None) -> Iterator[Session]:
    s = session_factory(engine)()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
