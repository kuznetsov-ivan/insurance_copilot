from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class DemoDataService:
    def __init__(self) -> None:
        self._data_dir = Path(__file__).resolve().parent.parent / "data"

    @lru_cache(maxsize=1)
    def customers(self) -> list[dict[str, Any]]:
        return self._load("customers.json")

    @lru_cache(maxsize=1)
    def policies(self) -> list[dict[str, Any]]:
        return self._load("policies.json")

    @lru_cache(maxsize=1)
    def providers(self) -> list[dict[str, Any]]:
        return self._load("providers.json")

    @lru_cache(maxsize=1)
    def scenarios(self) -> list[dict[str, Any]]:
        return self._load("scenarios.json")

    def _load(self, filename: str) -> list[dict[str, Any]]:
        with (self._data_dir / filename).open("r", encoding="utf-8") as handle:
            return json.load(handle)
