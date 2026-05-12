import re

from curl_cffi.requests import Session

from .models import Servers

_PAGE_URL = "https://cybershoke.net/de/cs2/servers/dm"
_API_URL = "https://cybershoke.net/api/api/v2/main/data"
_DOMAIN = "cybershoke.net"


class Client:
    def __init__(self) -> None:
        self.web_client = Session(impersonate="firefox133")
        self._bootstrapped = False

    def _bootstrap(self) -> None:
        r = self.web_client.get(url=_PAGE_URL, timeout=10)
        r.raise_for_status()

        m = re.search(r'app-build-id[=:]["\s]*(\d+)', r.text)
        build_id = m.group(1) if m else "1778604034"

        for name, value in {
            "app-build-id": build_id,
            "last_page": "/de/cs2/servers/dm",
            "cookie_read": "1",
            "lang_g": "de",
            "gSortFiler": "online",
            "gPrimeFiler": "both",
            "gServersPrimeMode": "all",
            "gHideFilledServers": "1",
            "hideFullServers": "true",
        }.items():
            self.web_client.cookies.set(name, value, domain=_DOMAIN)

        self._bootstrapped = True

    def get_server_data(self) -> Servers:
        try:
            if not self._bootstrapped:
                self._bootstrap()

            response = self.web_client.get(url=_API_URL, timeout=10)
            response.raise_for_status()
            return Servers(**response.json())
        except Exception as e:
            raise ValueError(f"Failed to fetch server data: {e}") from e
