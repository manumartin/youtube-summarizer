from typing import Optional


class YouTubeSummarizerError(Exception):
    """Exception raised for errors in the YouTube summarizer."""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        full_message = message
        if details:
            full_message += f"\nDetails: {details}"
        super().__init__(full_message)
