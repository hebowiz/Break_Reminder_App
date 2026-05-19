"""JSONL logger for condition self-check inputs."""

from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


CONDITION_LOG_VERSION = 1
DEFAULT_CONDITION_LOG_PATH = Path("data") / "condition_log.jsonl"
SOURCE = "break_reminder"
ConditionLogRecord = dict[str, Any]


def build_condition_log_record(
    condition: int,
    mood: int,
    energy: int,
    symptoms: list[str],
    other_symptom: str,
    timestamp: datetime | None = None,
) -> ConditionLogRecord:
    """Build one JSON-serializable condition log record."""
    logged_at = timestamp or datetime.now()
    return {
        "log_version": CONDITION_LOG_VERSION,
        "timestamp": logged_at.isoformat(timespec="seconds"),
        "condition": _clamp_score(condition),
        "mood": _clamp_score(mood),
        "energy": _clamp_score(energy),
        "symptoms": [str(symptom) for symptom in symptoms if symptom != "その他"],
        "other_symptom": str(other_symptom or ""),
        "source": SOURCE,
        "notion_synced": False,
    }


def append_condition_log(
    record: ConditionLogRecord,
    path: Path | None = None,
) -> bool:
    """Append one condition record as a UTF-8 JSON Lines entry."""
    log_path = path or DEFAULT_CONDITION_LOG_PATH
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", newline="\n") as fh:
            json.dump(record, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write("\n")
        return True
    except Exception:
        traceback.print_exc()
        return False


def _clamp_score(value: int) -> int:
    """Clamp a score to the 0..100 range."""
    return max(0, min(100, int(value)))
