from dataclasses import dataclass


@dataclass
class TimestampedSegment:
    """A text segment with its timestamp."""

    start_time: str  # Format: "00:01:23"
    end_time: str  # Format: "00:01:26"
    text: str
    start_seconds: int  # For creating YouTube links
