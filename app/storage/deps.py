"""Shared ClaimsRepository factory — single source of truth for all API modules."""
import os

from app.storage.repository import ClaimsRepository


def get_repo() -> ClaimsRepository:
    db_path = os.environ.get("CLAIMS_DB_PATH", ".data/claims.db")
    return ClaimsRepository(db_path=db_path)
