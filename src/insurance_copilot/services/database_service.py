from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class DatabaseService:
    def __init__(self) -> None:
        self._data_dir = Path(__file__).resolve().parent.parent / "data"
        self._db_path = self._data_dir / "demo.sqlite3"
        self._initialize()

    def scenarios(self) -> list[dict[str, Any]]:
        return self._fetch_all("SELECT name, transcript FROM scenarios ORDER BY id")

    def customers(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT customer_id, name, phone, policy_reference
            FROM customers
            ORDER BY customer_id
            """
        )

    def policies(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                policy_reference,
                customer_name,
                customer_id,
                phone,
                status,
                roadside_assistance,
                tow_covered,
                repair_van_covered,
                rental_or_taxi_covered,
                covered_regions,
                exclusions
            FROM policy_directory
            ORDER BY policy_reference
            """
        )

    def providers(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT provider_name, garage_name, lat, lon, capabilities
            FROM providers
            ORDER BY provider_name
            """
        )

    def find_policy(self, policy_reference: str | None, customer_name: str | None) -> dict[str, Any] | None:
        if policy_reference:
            record = self._fetch_one(
                """
                SELECT *
                FROM policy_directory
                WHERE policy_reference = ?
                """,
                (policy_reference,),
            )
            if record:
                return record

        if customer_name:
            return self._fetch_one(
                """
                SELECT *
                FROM policy_directory
                WHERE lower(customer_name) = lower(?)
                """,
                (customer_name,),
            )
        return None

    def providers_for_action(self, action_type: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT provider_name, garage_name, lat, lon, capabilities
            FROM providers
            WHERE instr(capabilities, ?) > 0
            ORDER BY provider_name
            """,
            (action_type,),
        )

    def add_notification(
        self,
        *,
        session_id: str,
        customer_name: str | None,
        phone: str | None,
        coverage_status: str,
        message: str,
        timestamp: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO notifications (
                    session_id,
                    customer_name,
                    phone,
                    coverage_status,
                    message,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, customer_name, phone, coverage_status, message, timestamp),
            )

    def notifications(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT id, session_id, customer_name, phone, coverage_status, message, timestamp
            FROM notifications
            ORDER BY id DESC
            """
        )

    def execute_readonly(self, query: str) -> list[dict[str, Any]]:
        normalized = " ".join(query.strip().split())
        lowered = normalized.lower()
        if not lowered.startswith("select "):
            raise ValueError("Only SELECT queries are allowed.")
        if ";" in normalized.rstrip(";"):
            raise ValueError("Multiple statements are not allowed.")
        forbidden = ("insert ", "update ", "delete ", "drop ", "pragma ", "alter ", "attach ")
        if any(token in lowered for token in forbidden):
            raise ValueError("Only read-only SELECT queries are allowed.")
        return self._fetch_all(normalized)

    def reset_notifications(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM notifications")

    def _initialize(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    policy_reference TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS policies (
                    policy_reference TEXT PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    roadside_assistance INTEGER NOT NULL,
                    tow_covered INTEGER NOT NULL,
                    repair_van_covered INTEGER NOT NULL,
                    rental_or_taxi_covered INTEGER NOT NULL,
                    covered_regions TEXT NOT NULL,
                    exclusions TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS providers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_name TEXT NOT NULL,
                    garage_name TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    capabilities TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scenarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    transcript TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    customer_name TEXT,
                    phone TEXT,
                    coverage_status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE VIEW IF NOT EXISTS policy_directory AS
                SELECT
                    p.policy_reference,
                    p.customer_name,
                    c.customer_id,
                    c.phone,
                    p.status,
                    p.roadside_assistance,
                    p.tow_covered,
                    p.repair_van_covered,
                    p.rental_or_taxi_covered,
                    p.covered_regions,
                    p.exclusions
                FROM policies p
                LEFT JOIN customers c
                    ON c.policy_reference = p.policy_reference;
                """
            )
            self._seed_table(connection, "customers", self._load_json("customers.json"))
            self._seed_table(connection, "policies", self._load_json("policies.json"))
            self._seed_table(connection, "providers", self._load_json("providers.json"))
            self._seed_table(connection, "scenarios", self._load_json("scenarios.json"))

    def _seed_table(self, connection: sqlite3.Connection, table_name: str, rows: list[dict[str, Any]]) -> None:
        count = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if count:
            return

        if table_name == "customers":
            connection.executemany(
                """
                INSERT INTO customers (customer_id, name, phone, policy_reference)
                VALUES (:customer_id, :name, :phone, :policy_reference)
                """,
                rows,
            )
            return

        if table_name == "policies":
            normalized = []
            for row in rows:
                normalized.append(
                    {
                        **row,
                        "roadside_assistance": int(bool(row["roadside_assistance"])),
                        "tow_covered": int(bool(row["tow_covered"])),
                        "repair_van_covered": int(bool(row["repair_van_covered"])),
                        "rental_or_taxi_covered": int(bool(row["rental_or_taxi_covered"])),
                        "covered_regions": json.dumps(row["covered_regions"]),
                        "exclusions": json.dumps(row["exclusions"]),
                    }
                )
            connection.executemany(
                """
                INSERT INTO policies (
                    policy_reference,
                    customer_name,
                    status,
                    roadside_assistance,
                    tow_covered,
                    repair_van_covered,
                    rental_or_taxi_covered,
                    covered_regions,
                    exclusions
                )
                VALUES (
                    :policy_reference,
                    :customer_name,
                    :status,
                    :roadside_assistance,
                    :tow_covered,
                    :repair_van_covered,
                    :rental_or_taxi_covered,
                    :covered_regions,
                    :exclusions
                )
                """,
                normalized,
            )
            return

        if table_name == "providers":
            normalized = [{**row, "capabilities": json.dumps(row["capabilities"])} for row in rows]
            connection.executemany(
                """
                INSERT INTO providers (provider_name, garage_name, lat, lon, capabilities)
                VALUES (:provider_name, :garage_name, :lat, :lon, :capabilities)
                """,
                normalized,
            )
            return

        if table_name == "scenarios":
            connection.executemany(
                """
                INSERT INTO scenarios (name, transcript)
                VALUES (:name, :transcript)
                """,
                rows,
            )

    def _load_json(self, filename: str) -> list[dict[str, Any]]:
        with (self._data_dir / filename).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._normalize_row(dict(row)) for row in rows]

    def _fetch_one(self, query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        if row is None:
            return None
        return self._normalize_row(dict(row))

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        for field in (
            "roadside_assistance",
            "tow_covered",
            "repair_van_covered",
            "rental_or_taxi_covered",
        ):
            if field in row and row[field] is not None:
                row[field] = bool(row[field])

        for field in ("covered_regions", "exclusions", "capabilities"):
            if field in row and isinstance(row[field], str):
                row[field] = json.loads(row[field])

        return row

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection
