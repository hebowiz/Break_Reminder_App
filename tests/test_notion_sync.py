"""Tests for condition-log synchronization without contacting Notion."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from app.infra.condition_logger import append_condition_log, load_condition_logs_in_file_order
from app.infra.notion_sync import NotionConditionSync, normalize_notion_id


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        self.text = ""
        self.reason = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, on_create=None) -> None:  # noqa: ANN001
        self.created_pages: list[dict[str, Any]] = []
        self.on_create = on_create

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        if method == "GET" and "/databases/" in url:
            return FakeResponse({"data_sources": [{"id": "source-id"}]})
        if method == "GET" and "/data_sources/" in url:
            return FakeResponse(
                {
                    "properties": {
                        "名前": {"type": "title"},
                        "日時": {"type": "date"},
                        "体調": {"type": "number"},
                        "気分": {"type": "number"},
                        "余力": {"type": "number"},
                        "不調項目": {"type": "multi_select"},
                        "コメント": {"type": "rich_text"},
                        "source": {"type": "rich_text"},
                    }
                }
            )
        if method == "POST" and url.endswith("/query"):
            return FakeResponse({"results": []})
        if method == "POST" and url.endswith("/pages"):
            self.created_pages.append(kwargs["json"])
            if self.on_create is not None:
                self.on_create()
            return FakeResponse({"id": "created-page-id"})
        raise AssertionError(f"Unexpected request: {method} {url}")


class NotionConditionSyncTests(unittest.TestCase):
    DATABASE_ID = "0123456789abcdef0123456789abcdef"

    def test_normalizes_database_url(self) -> None:
        url = f"https://www.notion.so/{self.DATABASE_ID}?v=view"
        self.assertEqual(
            normalize_notion_id(url),
            self.DATABASE_ID,
        )

    def test_uploads_pending_record_and_marks_jsonl(self) -> None:
        record = {
            "log_version": 1,
            "timestamp": "2026-09-03T12:30:00",
            "condition": 60,
            "mood": 70,
            "energy": 40,
            "comment": "少し疲れ",
            "symptoms": ["眠気"],
            "source": "break_reminder",
            "notion_synced": False,
        }
        with tempfile.TemporaryDirectory() as temporary_dir:
            log_path = Path(temporary_dir) / "condition_log.jsonl"
            log_path.write_text(
                json.dumps(record, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            session = FakeSession()
            synchronizer = NotionConditionSync(
                token="secret_test",
                database_id=self.DATABASE_ID,
                session=session,  # type: ignore[arg-type]
            )

            result = synchronizer.sync_pending_records(log_path)

            self.assertEqual(result.uploaded, 1)
            self.assertEqual(len(session.created_pages), 1)
            properties = session.created_pages[0]["properties"]
            self.assertEqual(properties["体調"], {"number": 60})
            self.assertEqual(
                properties["不調項目"],
                {"multi_select": [{"name": "眠気"}]},
            )
            saved = load_condition_logs_in_file_order(log_path)
            self.assertTrue(saved[0]["notion_synced"])
            self.assertEqual(saved[0]["notion_page_id"], "created-page-id")

    def test_preserves_record_appended_during_network_request(self) -> None:
        first = {
            "timestamp": "2026-09-03T12:30:00",
            "condition": 60,
            "mood": 70,
            "energy": 40,
            "symptoms": [],
            "notion_synced": False,
        }
        second = {
            "timestamp": "2026-09-03T12:31:00",
            "condition": 80,
            "mood": 80,
            "energy": 80,
            "symptoms": [],
            "notion_synced": False,
        }
        with tempfile.TemporaryDirectory() as temporary_dir:
            log_path = Path(temporary_dir) / "condition_log.jsonl"
            log_path.write_text(json.dumps(first) + "\n", encoding="utf-8")
            session = FakeSession(on_create=lambda: append_condition_log(second, log_path))
            synchronizer = NotionConditionSync(
                token="secret_test",
                database_id=self.DATABASE_ID,
                session=session,  # type: ignore[arg-type]
            )

            synchronizer.sync_pending_records(log_path)

            saved = load_condition_logs_in_file_order(log_path)
            self.assertEqual(len(saved), 2)
            self.assertTrue(saved[0]["notion_synced"])
            self.assertFalse(saved[1]["notion_synced"])


if __name__ == "__main__":
    unittest.main()
