import threading
from datetime import datetime
from typing import Optional

from cybershoke.client import Client
from cybershoke.models import Server, Servers


class ServerService:
    GAME_ID = "2"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._client = Client()
        self._data: Optional[Servers] = None
        self._last_updated: Optional[datetime] = None

    def refresh(self) -> None:
        data = self._client.get_server_data()
        with self._lock:
            self._data = data
            self._last_updated = datetime.now()

    @property
    def last_updated(self) -> Optional[datetime]:
        with self._lock:
            return self._last_updated

    def _servers_dict(self) -> dict[str, dict[str, list[Server]]]:
        with self._lock:
            if self._data is None:
                return {}
            return self._data.data.modules.servers.data.servers.get(self.GAME_ID, {})

    def get_modes(self) -> list[str]:
        sd = self._servers_dict()
        return [mode for mode, cats in sd.items() if any(cats.values())]

    def get_categories(self, mode: str) -> list[str]:
        sd = self._servers_dict()
        cats = list(sd.get(mode, {}).keys())
        return ["ALL" if c == "" else c for c in cats]

    def get_servers(self, mode: str, category: str) -> list[Server]:
        sd = self._servers_dict()
        lookup = "" if category == "ALL" else category
        servers = sd.get(mode, {}).get(lookup, [])
        return list(servers)
