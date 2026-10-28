import copy
import json
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, unquote

# A session snapshot is a plain JSON-able dict. Keys are camelCase so snapshots
# are interchangeable with the TypeScript tutti-api's `Session.toJSON()`.
SessionSnapshot = dict[str, Any]


@dataclass
class AppConfig:
    """App identity headers. Defaults mirror a captured tutti Android client."""

    version: str = "Tutti/11.0.0(40011774)/Android/36"  # X-App-Version
    source: str = "Android 11.0.0 (40011774)"  # X-Tutti-Source
    client_id: str = "android/11.0.0+env-live.git-a9330101d"  # X-Tutti-Client-Identifier
    app_id: str = ""  # X-App-Id
    # The WAF checks this; generic HTTP-library user agents are blocked.
    user_agent: str = "ch.tutti/android (Google Pixel 7a, OS 16)"


@dataclass
class AuthState:
    """Authenticated-account state. ``None`` on the session means anonymous."""

    token: str
    refresh_token: str | None = None
    expires_at: int | None = None
    account_id: str | None = None


_APP_KEYS = {
    "version": "version",
    "source": "source",
    "client_id": "clientId",
    "app_id": "appId",
    "user_agent": "userAgent",
}
_AUTH_KEYS = {
    "token": "token",
    "refresh_token": "refreshToken",
    "expires_at": "expiresAt",
    "account_id": "accountId",
}


@dataclass
class Session:
    """Per-account state and the single source of request headers. One Session =
    one account; construct several for several accounts."""

    tutti_hash: str = field(default_factory=lambda: str(uuid.uuid4()))  # per-install device id
    app: AppConfig = field(default_factory=AppConfig)
    language: str = "de"
    auth: AuthState | None = None

    def build_headers(self) -> dict[str, str]:
        """Headers for every request. Called per request so auth changes apply at once."""
        headers = {
            "X-Tutti-Hash": self.tutti_hash,
            "X-Tutti-Source": self.app.source,
            "X-Tutti-Client-Identifier": self.app.client_id,
            "X-App-Version": self.app.version,
            "X-App-Id": self.app.app_id,
            "User-Agent": self.app.user_agent,
            "Accept-Language": self.language,
        }
        # tutti authenticates with the session token in X-Tutti-Auth (NOT a Bearer
        # header — that is only used once, to mint this token via authenticateJWT).
        if self.auth and self.auth.token:
            headers["X-Tutti-Auth"] = self.auth.token
        return headers

    def set_auth(self, auth: AuthState) -> None:
        self.auth = auth

    def clear_auth(self) -> None:
        self.auth = None

    @property
    def is_authenticated(self) -> bool:
        return bool(self.auth and self.auth.token)

    def to_dict(self) -> SessionSnapshot:
        """Persist a (possibly logged-in) account; restore with ``Session.from_dict``."""
        snap: SessionSnapshot = {
            "tuttiHash": self.tutti_hash,
            "app": {wire: getattr(self.app, attr) for attr, wire in _APP_KEYS.items()},
            "language": self.language,
        }
        if self.auth:
            snap["auth"] = {
                wire: getattr(self.auth, attr)
                for attr, wire in _AUTH_KEYS.items()
                if getattr(self.auth, attr) is not None
            }
        return snap

    @classmethod
    def from_dict(cls, snap: SessionSnapshot) -> "Session":
        app = snap.get("app") or {}
        auth = snap.get("auth")
        return cls(
            tutti_hash=snap["tuttiHash"],
            app=replace(
                AppConfig(), **{attr: app[wire] for attr, wire in _APP_KEYS.items() if wire in app}
            ),
            language=snap.get("language", "de"),
            auth=AuthState(
                **{attr: auth[wire] for attr, wire in _AUTH_KEYS.items() if wire in auth}
            )
            if auth
            else None,
        )


class SessionStore(Protocol):
    """Persists session snapshots under a string key. Implementations are
    interchangeable (in-memory, file, Redis, …)."""

    def save(self, key: str, snapshot: SessionSnapshot) -> None: ...
    def load(self, key: str) -> SessionSnapshot | None: ...
    def delete(self, key: str) -> None: ...
    def keys(self) -> list[str]: ...


class InMemorySessionStore:
    """Volatile, process-local store. Good for tests and short-lived processes."""

    def __init__(self) -> None:
        self._map: dict[str, SessionSnapshot] = {}

    def save(self, key: str, snapshot: SessionSnapshot) -> None:
        self._map[key] = copy.deepcopy(snapshot)

    def load(self, key: str) -> SessionSnapshot | None:
        s = self._map.get(key)
        return copy.deepcopy(s) if s is not None else None

    def delete(self, key: str) -> None:
        self._map.pop(key, None)

    def keys(self) -> list[str]:
        return list(self._map)


class FileSessionStore:
    """Persists each session as a JSON file in a directory (one file per key)."""

    def __init__(self, directory: str | Path) -> None:
        self.dir = Path(directory)

    def save(self, key: str, snapshot: SessionSnapshot) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self._file(key).write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    def load(self, key: str) -> SessionSnapshot | None:
        try:
            return json.loads(self._file(key).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def delete(self, key: str) -> None:
        self._file(key).unlink(missing_ok=True)

    def keys(self) -> list[str]:
        if not self.dir.is_dir():
            return []
        return [unquote(p.name[:-5]) for p in self.dir.iterdir() if p.name.endswith(".json")]

    def _file(self, key: str) -> Path:
        # Same escaping as JS encodeURIComponent, so files match the TS store.
        return self.dir / (quote(key, safe="!~*'()") + ".json")
