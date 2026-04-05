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
            "headerServersSetting": "[]",
            "hideFullAmong": "false",
            "sCategories": "{}",
            "competitionsLeague": "high",
            "gMapFilerv": "[]",
            "gCategoryFiler": "[]",
            "glocationFilerNewv": "[]",
            "gSortFiler": "online",
            "gPrimeFiler": "both",
            "gSortShopFiler2": "down",
            "gCompetitionsDataStats": "month",
            "gCompetitionsDataId": "12",
            "gCompetitionsDataClass": "low",
            "gCompetitionsDataHalfmonth": "0",
            "gProfileSkinchangerFilterQ": "%E2%98%85%20Karambit",
            "gProfileSkinchangerFilterCollection": "1",
            "hideFullServers": "true",
            "gSkipPremiumModal": "0",
            "gServersPrimeMode": "all",
            "gHideFilledServers": "1",
            "changer_update": "1773293722",
            "categories": "{}",
        }
        return cookies

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://cybershoke.net",
            "Sec-GPC": "1",
            "Connection": "keep-alive",
            "Referer": "https://cybershoke.net/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
        return headers

    def get_server_data(self) -> Servers:
        try:
            response = self.web_client.get(
                url="https://api.cybershoke.net/api/v2/main/data",
                cookies=self._get_cookies(),
                headers=self._get_headers(),
            )
        except Exception:
            raise ValueError("Did not receive a response!")
        return Servers(**response.json())
