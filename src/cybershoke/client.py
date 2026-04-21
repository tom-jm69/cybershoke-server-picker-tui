from typing import Optional

import requests

from .models import Servers


class Client:
    def __init__(
        self, web_client: Optional[requests.Session] = requests.Session()
    ) -> None:
        self.web_client = web_client

    def _get_cookies(self) -> dict[str, str]:
        cookies = {
            "app-build-id": "1776790835",
            "lang_g": "de",
            "gSortFiler": "online",
            "gPrimeFiler": "both",
            "gServersPrimeMode": "all",
            "gHideFilledServers": "1",
            "hideFullServers": "true",
        }
        return cookies

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-GPC": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Priority": "u=0, i",
            "TE": "trailers",
        }
        return headers

    def get_server_data(self) -> Servers:
        try:
            response = self.web_client.get(
                url="https://api.cybershoke.net/api/v2/main/data",
                cookies=self._get_cookies(),
                headers=self._get_headers(),
                timeout=10,
            )
            response.raise_for_status()
            return Servers(**response.json())
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to fetch server data: {e}") from e
