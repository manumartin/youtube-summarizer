from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoMetadata:
    """Metadata for a YouTube video."""

    title: str
    channel: str
    channel_id: str
    upload_date: str
    duration: Optional[int] = None
    description: Optional[str] = None
    view_count: Optional[int] = None
