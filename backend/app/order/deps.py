"""U2 consumed-contract adapter (placed under order/ to avoid a new shared dir).

Declares the U1 interfaces U2 CONSUMES (contract v0.2.0 §12) as:
  - lightweight local context/value types (attribute-compatible with U1's),
  - Ports (typing.Protocol) for Menu lookup and password hashing,
  - placeholder FastAPI dependency callables.

The Integration Lead wires the REAL U1 implementations in `main.py` via
`app.dependency_overrides` (contract §14 stub/mock rule). U2 never imports from
U1 owned paths. Unit tests inject fakes directly into service classes.

Framework-agnostic types here import no FastAPI/Pydantic so the core stays testable.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


# --- Contexts (mirror of contract §4; U1's equivalents are attribute-compatible) ---
@dataclass
class TabletContext:
    """Trusted source of store_id/table_no for customer APIs (§4)."""

    store_id: int
    table_no: int


@dataclass
class AdminContext:
    """Admin identity from JWT (§4)."""

    store_id: int
    admin_user_id: int
    username: str


@dataclass
class MenuInfo:
    """Minimal menu projection U2 needs to snapshot price/name at order time."""

    id: int
    store_id: int
    name: str
    price: int  # KRW integer


# --- Ports (consumed U1 capabilities) ---
@runtime_checkable
class MenuLookupPort(Protocol):
    """U1 Menu lookup used for order validation + price/name snapshot."""

    def get_menu(self, store_id: int, menu_id: int) -> Optional[MenuInfo]:
        ...


@runtime_checkable
class PasswordHasherPort(Protocol):
    """U1 common.hash_password (contract v0.2.0 §4). U2 does NOT implement bcrypt."""

    def hash_password(self, plaintext: str) -> str:
        ...


# --- Placeholder FastAPI dependencies (overridden by main.py at integration) ---
_UNWIRED = (
    "{name} is a U1-provided contract dependency. The Integration Lead must wire the "
    "real U1 implementation in main.py via app.dependency_overrides (contract v0.2.0 §12/§14)."
)


def verify_tablet_token() -> TabletContext:  # pragma: no cover - overridden at integration
    raise NotImplementedError(_UNWIRED.format(name="verify_tablet_token"))


def verify_admin_token() -> AdminContext:  # pragma: no cover - overridden at integration
    raise NotImplementedError(_UNWIRED.format(name="verify_admin_token"))


def get_connection() -> sqlite3.Connection:  # pragma: no cover - overridden at integration
    raise NotImplementedError(_UNWIRED.format(name="get_connection"))


def get_menu_lookup() -> MenuLookupPort:  # pragma: no cover - overridden at integration
    raise NotImplementedError(_UNWIRED.format(name="get_menu_lookup"))


def get_password_hasher() -> PasswordHasherPort:  # pragma: no cover - overridden at integration
    raise NotImplementedError(_UNWIRED.format(name="get_password_hasher"))
