"""Persistent upload storage for EERR Cockpit.

Each upload is keyed by (username, year, month) and stored as a pickled
{currency: {year_str: DataFrame}} dict — the same structure returned by
mock_data.get_mock_data() and eerr_cockpit.parser.EERRParser.parse().
"""
from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

UPLOADS_ROOT = Path(__file__).parent.parent / "data" / "uploads"


# ── Internal helpers ─────────────────────────────────────────────────

def _user_dir(username: str) -> Path:
    d = UPLOADS_ROOT / username
    d.mkdir(parents=True, exist_ok=True)
    return d


def _meta_path(username: str) -> Path:
    return _user_dir(username) / "metadata.json"


def _load_meta(username: str) -> list[dict]:
    p = _meta_path(username)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def _save_meta(username: str, meta: list[dict]) -> None:
    _meta_path(username).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── Public API ───────────────────────────────────────────────────────

def upload_exists(username: str, year: int, month: int) -> bool:
    """Return True if an EERR for this user/year/month is already stored."""
    return any(
        e["year"] == year and e["month"] == month
        for e in _load_meta(username)
    )


def save_upload(username: str, year: int, month: int, data: dict) -> None:
    """Persist parsed EERR data tagged with year/month for deduplication.

    Args:
        username: Logged-in user.
        year: Reference year of the uploaded statement (e.g. 2026).
        month: Reference month (1-12).
        data: Parsed dict {currency: {year_str: DataFrame}}.
    """
    fname = f"{year}_{month:02d}.pkl"
    path = _user_dir(username) / fname
    with path.open("wb") as fh:
        pickle.dump(data, fh)

    meta = _load_meta(username)
    meta.append({
        "year": year,
        "month": month,
        "file": fname,
        "uploaded_at": datetime.now().isoformat(),
    })
    _save_meta(username, meta)


def load_upload(username: str, year: int, month: int) -> Optional[dict]:
    """Load a specific upload or None if it doesn't exist."""
    if not upload_exists(username, year, month):
        return None
    fname = f"{year}_{month:02d}.pkl"
    path = _user_dir(username) / fname
    with path.open("rb") as fh:
        return pickle.load(fh)


def list_uploads(username: str) -> list[dict]:
    """Return all upload metadata for a user, sorted by year/month."""
    return sorted(_load_meta(username), key=lambda x: (x["year"], x["month"]))


def load_latest(username: str) -> Optional[dict]:
    """Load the data from the most recently uploaded EERR (by upload date)."""
    meta = _load_meta(username)
    if not meta:
        return None
    latest = max(meta, key=lambda x: x["uploaded_at"])
    return load_upload(username, latest["year"], latest["month"])
