from __future__ import annotations

import shutil
import sqlite3
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


TABLES_TO_COPY = [
    "accounts_user",
    "catalog_category",
    "catalog_service",
    "crm_contact",
    "crm_deal",
    "crm_dealhistory",
    "kp_eventtype",
    "kp_kptemplate",
    "kp_proposal",
    "kp_proposalitem",
]


class Command(BaseCommand):
    help = "Import legacy SQLite data from a db.sqlite3 file or a .tar.gz backup into the current SQLite database."

    def add_arguments(self, parser):
        parser.add_argument("backup_path", help="Path to db.sqlite3 or levelup_backup_*.tar.gz")
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Clear current app data in the target database before import.",
        )
        parser.add_argument(
            "--no-target-backup",
            action="store_true",
            help="Skip creating a timestamped backup copy of the target database.",
        )

    def handle(self, *args, **options):
        db_settings = settings.DATABASES["default"]
        if db_settings["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("This command supports only SQLite targets.")

        target_path = Path(str(db_settings["NAME"])).resolve()
        if not target_path.exists():
            raise CommandError(f"Target database does not exist yet: {target_path}. Run migrate first.")

        backup_path = Path(options["backup_path"]).resolve()
        if not backup_path.exists():
            raise CommandError(f"Backup file not found: {backup_path}")

        connection.close()

        if not options["no_target_backup"] and target_path.stat().st_size > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_copy = target_path.with_name(f"{target_path.stem}.before_import_{timestamp}.sqlite3")
            shutil.copy2(target_path, backup_copy)
            self.stdout.write(self.style.WARNING(f"Created local backup: {backup_copy}"))

        legacy_db_path, cleanup_path = self._resolve_legacy_db(backup_path)
        try:
            self._import_legacy_db(
                legacy_db_path=legacy_db_path,
                target_path=target_path,
                truncate=options["truncate"],
            )
        finally:
            if cleanup_path is not None:
                try:
                    cleanup_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _resolve_legacy_db(self, backup_path: Path) -> tuple[Path, Path | None]:
        if backup_path.suffix == ".sqlite3":
            return backup_path, None

        if backup_path.name.endswith(".tar.gz") or backup_path.suffix == ".tgz":
            with tarfile.open(backup_path, "r:gz") as archive:
                members = [member for member in archive.getmembers() if member.name.endswith("db.sqlite3")]
                if not members:
                    raise CommandError("Archive does not contain db.sqlite3")

                member = members[0]
                extracted_file = archive.extractfile(member)
                if extracted_file is None:
                    raise CommandError("Could not extract db.sqlite3 from archive")

                with tempfile.NamedTemporaryFile(
                    prefix="levelup_legacy_",
                    suffix=".sqlite3",
                    delete=False,
                ) as temp_file:
                    temp_file.write(extracted_file.read())
                    temp_path = Path(temp_file.name)

                return temp_path, temp_path

        raise CommandError("Unsupported backup format. Use db.sqlite3 or .tar.gz")

    def _import_legacy_db(self, *, legacy_db_path: Path, target_path: Path, truncate: bool) -> None:
        with sqlite3.connect(legacy_db_path) as source_conn, sqlite3.connect(target_path) as target_conn:
            source_conn.row_factory = sqlite3.Row
            target_conn.row_factory = sqlite3.Row

            self._validate_tables(source_conn, target_conn)
            self._prepare_target(target_conn, truncate=truncate)
            target_conn.commit()

            copied_summary: list[tuple[str, int, list[str]]] = []
            target_conn.execute("PRAGMA foreign_keys = OFF")

            try:
                for table_name in TABLES_TO_COPY:
                    copied_rows, copied_columns = self._copy_table(source_conn, target_conn, table_name)
                    self._reset_sequence(target_conn, table_name)
                    copied_summary.append((table_name, copied_rows, copied_columns))
            except Exception:
                target_conn.rollback()
                raise
            else:
                target_conn.commit()
            finally:
                target_conn.execute("PRAGMA foreign_keys = ON")

        for table_name, copied_rows, copied_columns in copied_summary:
            self.stdout.write(
                f"{table_name}: copied {copied_rows} rows using columns: {', '.join(copied_columns)}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Legacy import completed. Portfolio tables were left untouched because they do not exist in the old backup."
            )
        )

    def _validate_tables(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection) -> None:
        source_tables = self._table_names(source_conn)
        target_tables = self._table_names(target_conn)

        missing_in_source = [table for table in TABLES_TO_COPY if table not in source_tables]
        if missing_in_source:
            raise CommandError(
                f"Legacy database is missing required tables: {', '.join(missing_in_source)}"
            )

        missing_in_target = [table for table in TABLES_TO_COPY if table not in target_tables]
        if missing_in_target:
            raise CommandError(
                f"Target database is missing required tables: {', '.join(missing_in_target)}"
            )

    def _prepare_target(self, target_conn: sqlite3.Connection, *, truncate: bool) -> None:
        populated = [
            table_name
            for table_name in TABLES_TO_COPY
            if target_conn.execute(f"SELECT EXISTS(SELECT 1 FROM {table_name} LIMIT 1)").fetchone()[0]
        ]

        if populated and not truncate:
            raise CommandError(
                "Target database already contains imported app data. Re-run with --truncate to replace it. "
                f"Non-empty tables: {', '.join(populated)}"
            )

        if not populated:
            return

        for table_name in reversed(TABLES_TO_COPY):
            target_conn.execute(f"DELETE FROM {table_name}")
        target_conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ({})".format(
                ",".join("?" for _ in TABLES_TO_COPY)
            ),
            TABLES_TO_COPY,
        )

    def _copy_table(
        self,
        source_conn: sqlite3.Connection,
        target_conn: sqlite3.Connection,
        table_name: str,
    ) -> tuple[int, list[str]]:
        source_columns = self._table_columns(source_conn, table_name)
        source_column_set = set(source_columns)
        target_columns_info = self._table_columns_info(target_conn, table_name)

        insert_columns: list[str] = []
        source_select_columns: list[str] = []
        fallback_values: dict[str, object] = {}

        for column_info in target_columns_info:
            column_name = column_info["name"]
            if column_name in source_column_set:
                insert_columns.append(column_name)
                source_select_columns.append(column_name)
                continue

            if column_info["notnull"]:
                insert_columns.append(column_name)
                fallback_values[column_name] = self._fallback_value(column_info, table_name)

        if not insert_columns:
            raise CommandError(f"No compatible columns found for table {table_name}")

        columns_sql = ", ".join(insert_columns)
        select_sql = ", ".join(source_select_columns)
        placeholders_sql = ", ".join("?" for _ in insert_columns)

        rows = source_conn.execute(f"SELECT {select_sql} FROM {table_name} ORDER BY id").fetchall()
        if rows:
            target_conn.executemany(
                f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders_sql})",
                [
                    tuple(
                        row[column] if column in row.keys() else fallback_values[column]
                        for column in insert_columns
                    )
                    for row in rows
                ],
            )

        return len(rows), insert_columns

    def _reset_sequence(self, target_conn: sqlite3.Connection, table_name: str) -> None:
        max_row = target_conn.execute(f"SELECT MAX(id) FROM {table_name}").fetchone()
        max_id = int(max_row[0] or 0)
        target_conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))
        if max_id:
            target_conn.execute(
                "INSERT INTO sqlite_sequence(name, seq) VALUES(?, ?)",
                (table_name, max_id),
            )

    def _table_names(self, conn: sqlite3.Connection) -> set[str]:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {row[0] for row in rows}

    def _table_columns(self, conn: sqlite3.Connection, table_name: str) -> list[str]:
        rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        return [row[1] for row in rows]

    def _table_columns_info(self, conn: sqlite3.Connection, table_name: str) -> list[dict[str, object]]:
        rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        return [
            {
                "name": row[1],
                "type": (row[2] or "").upper(),
                "notnull": bool(row[3]),
                "default": row[4],
            }
            for row in rows
        ]

    def _fallback_value(self, column_info: dict[str, object], table_name: str) -> object:
        default = column_info["default"]
        if default not in (None, "NULL"):
            return self._normalize_default(default)

        column_type = str(column_info["type"])
        if "CHAR" in column_type or "TEXT" in column_type:
            return ""
        if any(token in column_type for token in ("INT", "DECIMAL", "NUMERIC", "REAL", "BOOL")):
            return 0

        raise CommandError(
            f"Cannot infer fallback value for {table_name}.{column_info['name']} ({column_type})"
        )

    def _normalize_default(self, value: object) -> object:
        raw = str(value).strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
            return raw[1:-1]

        lowered = raw.lower()
        if lowered in {"true", "false"}:
            return int(lowered == "true")

        try:
            return int(raw)
        except ValueError:
            pass

        try:
            return float(raw)
        except ValueError:
            return raw
