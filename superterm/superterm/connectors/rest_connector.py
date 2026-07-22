from __future__ import annotations

import pandas as pd
import requests

from .base import Connector


class RestConnector(Connector):
    """config: {url, method: "GET", headers: {...}, params: {...}, json_path: "data.items",
    table: "<name>"}. `json_path` is a dotted path to the list of records in the response body
    (omit if the response body is itself a list)."""

    def extract(self) -> dict[str, pd.DataFrame]:
        method = self.config.get("method", "GET")
        resp = requests.request(
            method,
            self.config["url"],
            headers=self.config.get("headers"),
            params=self.config.get("params"),
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()

        json_path = self.config.get("json_path")
        if json_path:
            for key in json_path.split("."):
                body = body[key]

        table = self.config.get("table", self.name)
        return {table: pd.DataFrame(body)}
