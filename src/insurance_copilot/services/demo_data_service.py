from __future__ import annotations

from typing import Any

from insurance_copilot.services.database_service import DatabaseService


class DemoDataService:
    def __init__(self, database: DatabaseService | None = None) -> None:
        self._database = database or DatabaseService()

    def customers(self) -> list[dict[str, Any]]:
        return self._database.customers()

    def policies(self) -> list[dict[str, Any]]:
        return self._database.policies()

    def providers(self) -> list[dict[str, Any]]:
        return self._database.providers()

    def scenarios(self) -> list[dict[str, Any]]:
        return self._database.scenarios()
