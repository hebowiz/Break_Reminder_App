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
    comment: str,
    symptoms: list[str],
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
        "comment": str(comment or ""),
        "symptoms": normalize_symptoms(symptoms),
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


def load_condition_logs(path: Path | None = None) -> list[ConditionLogRecord]:
    """Load condition log JSONL records sorted by timestamp descending."""
    log_path = path or DEFAULT_CONDITION_LOG_PATH
    if not log_path.exists():
        return []

    records: list[ConditionLogRecord] = []
    try:
        with log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                if isinstance(raw, dict):
                    records.append(raw)
    except Exception:
        traceback.print_exc()
        return []

    return sorted(
        records,
        key=lambda record: str(record.get("timestamp", "")),
        reverse=True,
    )


def get_record_symptoms(record: ConditionLogRecord) -> list[str]:
    """Return normalized symptoms, including legacy other_symptom values."""
    symptoms = record.get("symptoms")
    symptom_values = symptoms if isinstance(symptoms, list) else []
    return normalize_symptoms(
        [*symptom_values, *split_symptom_text(record.get("other_symptom"))]
    )


def normalize_symptoms(symptoms: list[object]) -> list[str]:
    """Normalize symptom values while preserving order and removing duplicates."""
    normalized: list[str] = []
    seen: set[str] = set()
    for symptom in symptoms:
        for item in split_symptom_text(symptom):
            if item == "その他" or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
    return normalized


def split_symptom_text(value: object) -> list[str]:
    """Split free-text symptoms by half-width or Japanese commas."""
    if value is None:
        return []
    return [
        item.strip()
        for chunk in str(value).split(",")
        for item in chunk.split("、")
        if item.strip()
    ]


def _clamp_score(value: int) -> int:
    """Clamp a score to the 0..100 range."""
    return max(0, min(100, int(value)))
