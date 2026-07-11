import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Optional


DEFAULT_CACHE_DIR = Path.home() / ".cache" / "jos-daily-brief"


@dataclass
class CachedValue:
    payload: Dict
    stale: bool = False


def _read(path: Path, source: str, now: datetime) -> Optional[tuple]:
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        if envelope.get("version") != 1 or envelope.get("source") != source:
            return None
        fetched_at = datetime.fromisoformat(envelope["fetched_at"])
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        return envelope["payload"], now - fetched_at.astimezone(timezone.utc)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write(path: Path, source: str, payload: Dict, now: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "version": 1,
        "source": source,
        "fetched_at": now.astimezone(timezone.utc).isoformat(),
        "payload": payload,
    }
    handle, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as temporary:
            json.dump(envelope, temporary, ensure_ascii=False)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def load_with_cache(
    source: str,
    loader: Callable[[], Dict],
    fresh_for: timedelta,
    stale_for: timedelta,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    now: Optional[datetime] = None,
) -> CachedValue:
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    path = cache_dir / f"{source}.json"
    cached = _read(path, source, current_time)
    if cached and cached[1] <= fresh_for:
        return CachedValue(cached[0])

    try:
        payload = loader()
        _write(path, source, payload, current_time)
        return CachedValue(payload)
    except Exception:
        if cached and cached[1] <= stale_for:
            return CachedValue(cached[0], stale=True)
        raise
