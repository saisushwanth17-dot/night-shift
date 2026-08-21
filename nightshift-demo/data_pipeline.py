"""Sample data transformation pipeline for demo_repo."""

from typing import Any


def process_user_event(event: dict[str, Any]) -> dict[str, Any]:
    """Process incoming user event records into normalized metrics.
    
    Bug intentionally present: attempts direct subscript on event['metadata'] 
    without checking if metadata is None or missing.
    """
    event_id = event.get("id")
    event_type = event.get("type", "unknown")
    
    # Root cause bug: direct subscript on None
    meta = event["metadata"]
    session_id = meta["session_id"]
    
    return {
        "event_id": event_id,
        "type": event_type,
        "session_id": session_id,
        "is_valid": True,
    }


def calculate_batch_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate aggregate summary from a batch of processed events."""
    processed = [process_user_event(e) for e in events]
    return {
        "total_processed": len(processed),
        "valid_count": sum(1 for p in processed if p["is_valid"]),
    }
