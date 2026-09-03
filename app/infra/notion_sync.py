"""Synchronize condition JSONL records to a Notion data source."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from app.infra.condition_logger import (
    DEFAULT_CONDITION_LOG_PATH,
    ConditionLogRecord,
    condition_log_transaction,
    load_condition_logs_in_file_order,
    replace_condition_logs,
)


NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2026-03-11"

FIELD_ALIASES = {
    "timestamp": ("日時", "日付", "記録日時", "timestamp", "date"),
    "condition": ("体調", "condition"),
    "mood": ("気分", "mood"),
    "energy": ("余力", "energy"),
    "symptoms": ("不調項目", "症状", "symptoms"),
    "comment": ("コメント", "メモ", "comment"),
    "source": ("記録元", "ソース", "source"),
}


class NotionSyncError(RuntimeError):
    """Raised when the Notion API cannot complete a synchronization."""


@dataclass(frozen=True)
class NotionSyncResult:
    """Summary of one synchronization attempt."""

    total: int
    already_synced: int
    uploaded: int
    linked_existing: int

    @property
    def synchronized(self) -> int:
        return self.uploaded + self.linked_existing


class NotionConditionSync:
    """Upload unsynchronized condition records and persist their remote IDs."""

    def __init__(
        self,
        token: str,
        database_id: str,
        session: requests.Session | None = None,
    ) -> None:
        self._token = token.strip()
        self._database_id = normalize_notion_id(database_id)
        if not self._token:
            raise ValueError("Notion integration token is empty")
        if len(self._database_id) != 32:
            raise ValueError("Notion database ID must contain 32 hexadecimal characters")
        self._session = session or requests.Session()

    def sync_pending_records(
        self,
        log_path: Path = DEFAULT_CONDITION_LOG_PATH,
    ) -> NotionSyncResult:
        """Synchronize all pending records, safely resuming after partial runs."""
        with condition_log_transaction():
            records = load_condition_logs_in_file_order(log_path)
            added_ids = False
            for record in records:
                if not record.get("notion_sync_id"):
                    record["notion_sync_id"] = uuid.uuid4().hex
                    added_ids = True
            if added_ids:
                replace_condition_logs(records, log_path)

        already_synced = sum(bool(record.get("notion_synced")) for record in records)
        pending = [record for record in records if not record.get("notion_synced")]
        if not pending:
            return NotionSyncResult(len(records), already_synced, 0, 0)

        data_source_id, schema = self._load_data_source()
        uploaded = 0
        linked_existing = 0

        for record in pending:
            title, properties, children = build_notion_page(record, schema)
            page_id = self._find_page_by_title(data_source_id, schema, title)
            if page_id:
                linked_existing += 1
            else:
                response = self._request(
                    "POST",
                    "/pages",
                    json_body={
                        "parent": {
                            "type": "data_source_id",
                            "data_source_id": data_source_id,
                        },
                        "properties": properties,
                        "children": children,
                    },
                )
                page_id = str(response.get("id", ""))
                if not page_id:
                    raise NotionSyncError("Notion did not return the created page ID")
                uploaded += 1

            self._mark_record_synced(
                log_path=log_path,
                sync_id=str(record["notion_sync_id"]),
                page_id=page_id,
            )

        return NotionSyncResult(
            total=len(records),
            already_synced=already_synced,
            uploaded=uploaded,
            linked_existing=linked_existing,
        )

    @staticmethod
    def _mark_record_synced(log_path: Path, sync_id: str, page_id: str) -> None:
        """Update one record without losing logs appended during network requests."""
        with condition_log_transaction():
            latest_records = load_condition_logs_in_file_order(log_path)
            for latest_record in latest_records:
                if str(latest_record.get("notion_sync_id", "")) == sync_id:
                    latest_record["notion_synced"] = True
                    latest_record["notion_page_id"] = page_id
                    replace_condition_logs(latest_records, log_path)
                    return
        raise NotionSyncError("The synchronized local condition record was not found")

    def _load_data_source(self) -> tuple[str, dict[str, Any]]:
        database = self._request("GET", f"/databases/{self._database_id}")
        data_sources = database.get("data_sources")
        if not isinstance(data_sources, list) or not data_sources:
            raise NotionSyncError("The Notion database has no accessible data source")
        data_source_id = str(data_sources[0].get("id", ""))
        if not data_source_id:
            raise NotionSyncError("The Notion database did not return a data source ID")
        data_source = self._request("GET", f"/data_sources/{data_source_id}")
        schema = data_source.get("properties")
        if not isinstance(schema, dict):
            raise NotionSyncError("The Notion data source schema is unavailable")
        return data_source_id, schema

    def _find_page_by_title(
        self,
        data_source_id: str,
        schema: dict[str, Any],
        title: str,
    ) -> str | None:
        title_name = find_title_property(schema)
        response = self._request(
            "POST",
            f"/data_sources/{data_source_id}/query",
            json_body={
                "filter": {
                    "property": title_name,
                    "title": {"equals": title},
                },
                "page_size": 1,
            },
        )
        results = response.get("results")
        if isinstance(results, list) and results:
            page_id = results[0].get("id")
            return str(page_id) if page_id else None
        return None

    def _request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }
        response: requests.Response | None = None
        for attempt in range(3):
            try:
                response = self._session.request(
                    method,
                    f"{NOTION_API_BASE}{path}",
                    headers=headers,
                    json=json_body,
                    timeout=15,
                )
            except requests.RequestException as exc:
                raise NotionSyncError(f"Notion connection failed: {exc}") from exc
            if response.status_code != 429 or attempt == 2:
                break
            retry_after = response.headers.get("Retry-After", "1")
            try:
                wait_seconds = min(10.0, max(0.0, float(retry_after)))
            except ValueError:
                wait_seconds = 1.0
            time.sleep(wait_seconds)

        if response is None:
            raise NotionSyncError("Notion did not return a response")
        if not response.ok:
            message = _notion_error_message(response)
            raise NotionSyncError(f"Notion API error ({response.status_code}): {message}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise NotionSyncError("Notion returned an invalid response") from exc
        if not isinstance(payload, dict):
            raise NotionSyncError("Notion returned an unexpected response")
        return payload


def build_notion_page(
    record: ConditionLogRecord,
    schema: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    """Convert one local record to schema-aware Notion page content."""
    title_name = find_title_property(schema)
    sync_key = condition_sync_key(record)
    timestamp = str(record.get("timestamp", ""))
    title = f"体調記録 {timestamp} [{sync_key}]"
    properties: dict[str, Any] = {
        title_name: {"title": _rich_text(title)},
    }

    for field, aliases in FIELD_ALIASES.items():
        property_name = find_property(schema, aliases, exclude={title_name})
        if property_name is None:
            continue
        notion_type = str(schema[property_name].get("type", ""))
        converted = convert_property(field, record.get(field), notion_type)
        if converted is not None:
            properties[property_name] = converted

    snapshot = json.dumps(record, ensure_ascii=False, indent=2)
    children = [
        {
            "object": "block",
            "type": "code",
            "code": {
                "language": "json",
                "rich_text": _rich_text(snapshot[:2000]),
            },
        }
    ]
    return title, properties, children


def find_title_property(schema: dict[str, Any]) -> str:
    """Return the data source's required title property name."""
    for name, definition in schema.items():
        if isinstance(definition, dict) and definition.get("type") == "title":
            return name
    raise NotionSyncError("The Notion data source has no title property")


def find_property(
    schema: dict[str, Any],
    aliases: tuple[str, ...],
    exclude: set[str],
) -> str | None:
    """Find a property using case-insensitive Japanese/English aliases."""
    normalized_aliases = {alias.casefold() for alias in aliases}
    for name in schema:
        if name not in exclude and name.strip().casefold() in normalized_aliases:
            return name
    return None


def convert_property(field: str, value: Any, notion_type: str) -> dict[str, Any] | None:
    """Convert a local field to a compatible Notion property value."""
    if field == "timestamp" and notion_type == "date":
        return {"date": {"start": str(value)}}
    if field in {"condition", "mood", "energy"} and notion_type == "number":
        return {"number": int(value)}
    if field == "symptoms" and notion_type == "multi_select":
        values = value if isinstance(value, list) else []
        return {"multi_select": [{"name": str(item)[:100]} for item in values]}

    text = ", ".join(str(item) for item in value) if isinstance(value, list) else str(value or "")
    if notion_type == "rich_text":
        return {"rich_text": _rich_text(text[:2000])}
    if notion_type == "select" and text:
        return {"select": {"name": text[:100]}}
    return None


def condition_sync_key(record: ConditionLogRecord) -> str:
    """Return a deterministic key used to avoid duplicate Notion pages."""
    sync_id = str(record.get("notion_sync_id", "")).strip()
    if sync_id:
        return sync_id
    stable_record = {
        key: value
        for key, value in record.items()
        if key not in {"notion_synced", "notion_page_id"}
    }
    encoded = json.dumps(
        stable_record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:12]


def normalize_notion_id(value: str) -> str:
    """Extract a compact database ID from an ID or a standard Notion URL."""
    text = str(value or "").strip()
    if "/" in text:
        text = text.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
        text = text.rsplit("-", 1)[-1]
    return "".join(character for character in text if character.lower() in "0123456789abcdef")


def _rich_text(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": text}}]


def _notion_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("message"):
            return str(payload["message"])[:500]
    except ValueError:
        pass
    return (response.text or response.reason or "unknown error")[:500]
