"""In-memory admin login attempt limiter (C1, FR-A1).

Policy: per (store_id, username), 5 consecutive failures -> 10 minute lock.
Successful login resets the counter and lock. In-process only (single-process
assumption); counters reset on restart.
"""
import threading
import time

from app.common import config

_lock = threading.Lock()
_state: dict[tuple[int, str], dict] = {}


def _key(store_id: int, username: str) -> tuple[int, str]:
    return (int(store_id), str(username))


def is_locked(store_id: int, username: str) -> bool:
    with _lock:
        entry = _state.get(_key(store_id, username))
        if not entry:
            return False
        return bool(entry["locked_until"]) and entry["locked_until"] > time.time()


def register_failure(store_id: int, username: str) -> None:
    with _lock:
        key = _key(store_id, username)
        entry = _state.setdefault(key, {"fail": 0, "locked_until": 0.0})
        # Reset a stale (expired) lock before counting.
        if entry["locked_until"] and entry["locked_until"] <= time.time():
            entry["fail"] = 0
            entry["locked_until"] = 0.0
        entry["fail"] += 1
        if entry["fail"] >= config.LOGIN_MAX_FAILS:
            entry["locked_until"] = time.time() + config.LOGIN_LOCK_SECONDS


def reset(store_id: int, username: str) -> None:
    with _lock:
        _state.pop(_key(store_id, username), None)


def reset_all() -> None:
    with _lock:
        _state.clear()
