"""
Core functionality for YouTube transcript summarization using yt-dlp.
"""

import re
import subprocess
import tempfile
import sys
from pathlib import Path
from typing import Optional, List

from litellm import completion

from .config import Config


class YouTubeSummarizerError(Exception):
    """Exception raised for errors in the YouTube summarizer."""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        full_message = message
        if details:
            full_message += f"\nDetails: {details}"
        super().__init__(full_message)


def get_video_id(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)",
        r"youtube\.com/watch\?.*v=([^&\n?#]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def load_urls_from_file(file_path: str) -> List[str]:
    """Load YouTube URLs from a text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            urls = [line.strip() for line in file if line.strip()]
        return urls
    except Exception as e:
        raise YouTubeSummarizerError(f"Error reading file {file_path}: {str(e)}")


def load_urls_from_stdin() -> List[str]:
    """Load YouTube URLs from stdin (for piped input)."""
    try:
        urls = []
        for line in sys.stdin:
            url = line.strip()
            if url:
                urls.append(url)
        return urls
    except Exception as e:
        raise YouTubeSummarizerError(f"Error reading URLs from stdin: {str(e)}")


def download_transcript(video_id: str) -> str:
    """Download transcript for a YouTube video using yt-dlp."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download subtitles using yt-dlp
            cmd = [
                "yt-dlp",
                # "--cookies-from-browser",
                # "chrome",  # Use cookies from Chrome browser
                "--write-auto-subs",  # Download auto-generated subtitles
                "--write-subs",  # Download manual subtitles
                "--sub-langs",
                "en",  # English subtitles
                "--sub-format",
                "vtt",  # VTT format
                "--skip-download",  # Don't download video
                "-o",
                f"{temp_dir}/%(title)s.%(ext)s",
                video_url,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)

            # Look for subtitle files (try multiple patterns) - check this first before failing
            subtitle_patterns = ["*.en.vtt", "*.en-orig.vtt", "*.en-*.vtt"]

            subtitle_files = []
            for pattern in subtitle_patterns:
                subtitle_files.extend(Path(temp_dir).glob(pattern))

            # Only fail if no subtitle files were created AND the command failed
            if result.returncode != 0 and not subtitle_files:
                details = []
                details.append(f"yt-dlp command: {' '.join(cmd)}")
                details.append(f"yt-dlp exit code: {result.returncode}")
                if result.stderr:
                    details.append(f"yt-dlp stderr: {result.stderr.strip()}")
                if result.stdout:
                    details.append(f"yt-dlp stdout: {result.stdout.strip()}")

                raise YouTubeSummarizerError(
                    f"Failed to download transcript for video {video_id}: yt-dlp command failed", "\n".join(details)
                )

            if not subtitle_files:
                # Show what files were actually created for debugging
                all_files = list(Path(temp_dir).glob("*"))
                debug_info = f"No English subtitle files found for video {video_id}"
                if all_files:
                    debug_info += f"\nFiles found in temp directory: {[f.name for f in all_files]}"
                else:
                    debug_info += "\nNo files created in temp directory"

                raise YouTubeSummarizerError(
                    f"Failed to download transcript for video {video_id}: No English subtitle files found", debug_info
                )

            # Use the first available subtitle file
            subtitle_file = subtitle_files[0]

            with open(subtitle_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse VTT content and extract clean text
            transcript_text = _parse_vtt_content(content)

            if not transcript_text:
                raise YouTubeSummarizerError(
                    f"Failed to parse transcript for video {video_id}: No text extracted from VTT content"
                )

            return transcript_text

    except subprocess.TimeoutExpired:
        raise YouTubeSummarizerError(
            f"Failed to download transcript for video {video_id}: Download timed out after 120 seconds"
        )
    except YouTubeSummarizerError:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        raise YouTubeSummarizerError(f"Failed to download transcript for video {video_id}: {str(e)}")


def _parse_vtt_content(vtt_content: str) -> str:
    """Parse VTT subtitle content and extract clean text."""
    lines = vtt_content.split("\n")
    transcript_parts = []

    for line in lines:
        line = line.strip()

        # Skip VTT headers, timestamps, and empty lines
        if (
            line
            and not line.startswith("WEBVTT")
            and not line.startswith("NOTE")
            and not line.startswith("Kind:")
            and not line.startswith("Language:")
            and "-->" not in line
            and not line.isdigit()
            and not re.match(r"^\d+$", line)
        ):
            # Clean HTML-like tags and timestamp markers
            cleaned_line = _clean_vtt_line(line)
            if cleaned_line:
                transcript_parts.append(cleaned_line)

    return " ".join(transcript_parts)


def _clean_vtt_line(line: str) -> str:
    """Clean a VTT line of timestamp markers and HTML tags."""
    # Remove timestamp markers like <00:00:01.280>
    line = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", line)

    # Remove HTML-like tags like <c>, </c>
    line = re.sub(r"<[^>]+>", "", line)

    # Remove extra whitespace
    line = " ".join(line.split())

    return line.strip()


def summarize_with_llm(transcript: str, config: Config) -> str:
    """Generate summary using configured LLM."""
    try:
        prompt = f"""Please provide a concise summary of the following YouTube video transcript in markdown format. 
Focus on the main points and key takeaways. Use proper markdown formatting including:
- Headers (##, ###) for main sections
- Bullet points (-) for lists
- **Bold text** for emphasis
- Organize the content in a clear, structured way

{transcript}"""

        # Prepare litellm parameters
        model_name = f"{config.provider.value}/{config.model}"

        # Set up litellm configuration
        kwargs = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise summaries of video transcripts in markdown format. Always use proper markdown syntax including headers, bullet points, and bold text for emphasis.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }

        # Add provider-specific parameters
        if config.effective_base_url:
            kwargs["base_url"] = config.effective_base_url

        response = completion(**kwargs)

        summary = response.choices[0].message.content
        if not summary:
            raise YouTubeSummarizerError("Failed to generate summary: LLM returned empty response")

        return summary
    except Exception as e:
        raise YouTubeSummarizerError(f"Failed to generate summary: {str(e)}")


def generate_title_from_summary(summary: str, config: Config) -> str:
    """Generate a meaningful filename from the summary using configured LLM."""
    try:
        prompt = f"""Based on this video summary, create a short, descriptive filename of 5-6 words maximum using only letters, numbers, and underscores. 
The filename should capture the main topic or key concept. Use underscores to separate words.

Summary: {summary}

Return only the filename without any explanation."""

        # Prepare litellm parameters
        model_name = f"{config.provider.value}/{config.model}"

        kwargs = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise, descriptive filenames from text summaries. Always use underscores instead of spaces and keep it to 5-6 words maximum.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": config.title_max_tokens,
            "temperature": config.title_temperature,
        }

        # Add provider-specific parameters
        if config.effective_base_url:
            kwargs["base_url"] = config.effective_base_url

        response = completion(**kwargs)

        title = response.choices[0].message.content.strip() if response.choices[0].message.content else ""

        # Clean the title to ensure it's filesystem-safe
        title = re.sub(r"[^a-zA-Z0-9_]", "_", title)
        title = re.sub(r"_+", "_", title)  # Replace multiple underscores with single
        title = title.strip("_")  # Remove leading/trailing underscores

        # Limit length and ensure it's not empty
        if not title or len(title) > 80:
            raise YouTubeSummarizerError("Failed to generate title: Generated title is empty or too long")

        return title

    except Exception as e:
        raise YouTubeSummarizerError(f"Failed to generate title: {str(e)}")


def save_summary(video_id: str, summary: str, output_dir: str, config: Config) -> str:
    """Save summary to a markdown file with a meaningful name. Returns the file path."""
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Try to generate a meaningful title
        try:
            title = generate_title_from_summary(summary, config)
            filename = f"{title}.{video_id}.md"
        except YouTubeSummarizerError:
            # Fallback to video ID if title generation fails
            filename = f"summary.{video_id}.md"

        file_path = Path(output_dir) / filename

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(summary)

        return str(file_path)
    except Exception as e:
        raise YouTubeSummarizerError(f"Failed to save summary for video {video_id}: {str(e)}")
