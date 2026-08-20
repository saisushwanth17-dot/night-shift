"""Unit tests for demo_repo data pipeline."""

import pytest
from data_pipeline import calculate_batch_summary, process_user_event


def test_process_standard_event():
    event = {
        "id": "evt_101",
        "type": "click",
        "metadata": {"session_id": "sess_abc123"},
    }
    result = process_user_event(event)
    assert result["event_id"] == "evt_101"
    assert result["session_id"] == "sess_abc123"
    assert result["is_valid"] is True


def test_process_event_with_missing_or_null_metadata():
    """Edge case: event payload with null metadata or missing session_id."""
    event = {
        "id": "evt_102",
        "type": "heartbeat",
        "metadata": None,
    }
    result = process_user_event(event)
    assert result["event_id"] == "evt_102"
    assert result["session_id"] is None
    assert result["is_valid"] is True


def test_calculate_batch_summary():
    events = [
        {"id": "evt_1", "metadata": {"session_id": "s1"}},
        {"id": "evt_2", "metadata": {"session_id": "s2"}},
    ]
    summary = calculate_batch_summary(events)
    assert summary["total_processed"] == 2
    assert summary["valid_count"] == 2
