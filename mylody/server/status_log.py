"""Small in-memory status feed for the web UI."""

from datetime import datetime


MAX_STATUS_EVENTS = 80


def add_status(app, message: str) -> None:
    """Append a timestamped status message to app.state.status_events."""
    events = getattr(app.state, "status_events", None)
    if events is None:
        events = []
        app.state.status_events = events

    timestamp = datetime.now().strftime("%H:%M:%S")
    events.append({"time": timestamp, "message": message})
    del events[:-MAX_STATUS_EVENTS]
