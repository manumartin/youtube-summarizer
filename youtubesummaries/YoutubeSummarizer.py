"""
Core functionality for YouTube transcript summarization using yt-dlp.
"""

import re
import subprocess
import tempfile
import sys
import json
from pathlib import Path
from typing import Optional, List, Tuple

from litellm import completion

from youtubesummaries.TimestampedSegment import TimestampedSegment
from youtubesummaries.VideoMetadata import VideoMetadata
from youtubesummaries.YouTubeSummarizerError import YouTubeSummarizerError

from .Config import Config


class YouTubeSummarizer:
    """YouTube video transcript summarizer using yt-dlp and LLM."""

    def __init__(self, config: Config) -> None:
        """Initialize the summarizer with configuration.

        Args:
            config: Configuration object containing LLM and other settings
        """
        self.config = config

    @staticmethod
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

    @staticmethod
    def load_urls_from_file(file_path: str) -> List[str]:
        """Load YouTube URLs from a text file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                urls = [line.strip() for line in file if line.strip()]
            return urls
        except Exception as e:
            raise YouTubeSummarizerError(f"Error reading file {file_path}: {str(e)}")

    @staticmethod
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

    @staticmethod
    def download_transcript(video_id: str) -> Tuple[str, VideoMetadata, List[TimestampedSegment]]:
        """Download transcript and metadata for a YouTube video using yt-dlp."""
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download subtitles and metadata using yt-dlp
                cmd = [
                    "yt-dlp",
                    # "--cookies-from-browser",
                    # "chrome",  # Use cookies from Chrome browser
                    "--write-auto-subs",  # Download auto-generated subtitles
                    "--write-subs",  # Download manual subtitles
                    "--write-info-json",  # Download metadata as JSON
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

                # Look for info.json file
                info_files = list(Path(temp_dir).glob("*.info.json"))

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
                        f"Failed to download transcript for video {video_id}: No English subtitle files found",
                        debug_info,
                    )

                # Parse metadata from info.json
                metadata = None
                if info_files:
                    try:
                        with open(info_files[0], "r", encoding="utf-8") as f:
                            info_data = json.load(f)

                        metadata = VideoMetadata(
                            title=info_data.get("title", "Unknown Title"),
                            channel=info_data.get("channel", "Unknown Channel"),
                            channel_id=info_data.get("channel_id", ""),
                            upload_date=info_data.get("upload_date", ""),
                            duration=info_data.get("duration"),
                            description=info_data.get("description"),
                            view_count=info_data.get("view_count"),
                        )
                    except (json.JSONDecodeError, KeyError) as e:
                        # If metadata parsing fails, create a basic metadata object
                        metadata = VideoMetadata(
                            title="Unknown Title", channel="Unknown Channel", channel_id="", upload_date=""
                        )

                # Fallback metadata if no info.json was created
                if not metadata:
                    metadata = VideoMetadata(
                        title="Unknown Title", channel="Unknown Channel", channel_id="", upload_date=""
                    )

                # Use the first available subtitle file
                subtitle_file = subtitle_files[0]

                with open(subtitle_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Parse VTT content and extract clean text
                transcript_text = YouTubeSummarizer._parse_vtt_content(content)
                timestamped_segments = YouTubeSummarizer._parse_vtt_timestamps(content)

                if not transcript_text:
                    raise YouTubeSummarizerError(
                        f"Failed to parse transcript for video {video_id}: No text extracted from VTT content"
                    )

                return transcript_text, metadata, timestamped_segments

        except subprocess.TimeoutExpired:
            raise YouTubeSummarizerError(
                f"Failed to download transcript for video {video_id}: Download timed out after 120 seconds"
            )
        except YouTubeSummarizerError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            raise YouTubeSummarizerError(f"Failed to download transcript for video {video_id}: {str(e)}")

    @staticmethod
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
                cleaned_line = YouTubeSummarizer._clean_vtt_line(line)
                if cleaned_line:
                    transcript_parts.append(cleaned_line)

        return " ".join(transcript_parts)

    @staticmethod
    def _parse_vtt_timestamps(vtt_content: str) -> List[TimestampedSegment]:
        """Parse VTT subtitle content and extract timestamped segments."""
        lines = vtt_content.split("\n")
        segments = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Look for VTT timestamp lines (format: "00:01:23.456 --> 00:01:26.789")
            if "-->" in line and re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}", line):
                start_time_str, end_time_str = line.split(" --> ")

                # Get the text content (next non-empty line)
                text_parts = []
                i += 1
                while i < len(lines):
                    text_line = lines[i].strip()
                    if not text_line:  # Empty line indicates end of this segment
                        break
                    if "-->" in text_line:  # Next timestamp segment
                        i -= 1  # Back up to process this timestamp line next
                        break

                    # Clean the text line
                    cleaned_text = YouTubeSummarizer._clean_vtt_line(text_line)
                    if cleaned_text:
                        text_parts.append(cleaned_text)
                    i += 1

                if text_parts:
                    # Create timestamped segment
                    segment = TimestampedSegment(
                        start_time=start_time_str[:8],  # Remove milliseconds for display
                        end_time=end_time_str[:8],
                        text=" ".join(text_parts),
                        start_seconds=int(YouTubeSummarizer._time_to_seconds(start_time_str)),
                    )
                    segments.append(segment)

            i += 1

        return segments

    @staticmethod
    def _clean_vtt_line(line: str) -> str:
        """Clean a VTT line of timestamp markers and HTML tags."""
        # Remove timestamp markers like <00:00:01.280>
        line = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", line)

        # Remove HTML-like tags like <c>, </c>
        line = re.sub(r"<[^>]+>", "", line)

        # Remove extra whitespace
        line = " ".join(line.split())

        return line.strip()

    @staticmethod
    def _time_to_seconds(time_str: str) -> int:
        """Convert a VTT time string (e.g., "00:01:23.456") to seconds."""
        h, m, s_ms = time_str.split(":")
        s, ms = s_ms.split(".")
        return int(h) * 3600 + int(m) * 60 + int(s)

    @staticmethod
    def create_youtube_timestamp_link(video_id: str, seconds: int) -> str:
        """Create a YouTube URL with timestamp."""
        return f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"

    def summarize(self, transcript: str, timestamped_segments: List[TimestampedSegment], video_id: str) -> str:
        """Generate summary with timestamps using configured LLM."""
        try:
            # Create a sample of timestamped content for the LLM
            sample_segments = timestamped_segments[
                :: max(1, len(timestamped_segments) // 10)
            ]  # Take every 10th segment
            timestamp_examples = []

            for segment in sample_segments[:5]:  # Limit to first 5 examples
                link = self.create_youtube_timestamp_link(video_id, segment.start_seconds)
                timestamp_examples.append(f"[{segment.start_time}]({link}): {segment.text[:100]}...")

            examples_text = "\n".join(timestamp_examples)

            prompt = f"""Please provide a concise summary of the following YouTube video transcript in markdown format. 
Focus on the main points and key takeaways. Use proper markdown formatting including:
- Headers (##, ###) for main sections
- Bullet points (-) for lists
- **Bold text** for emphasis
- Organize the content in a clear, structured way

IMPORTANT: When referencing specific topics or moments, include relevant timestamps as clickable links.
Use this EXACT format for timestamps: [HH:MM:SS](https://www.youtube.com/watch?v={video_id}&t=XXXs)
Where XXX is the timestamp in seconds. You MUST use the video ID "{video_id}" in all timestamp links.

Here are some example timestamp formats that show the correct URL structure with the actual video ID:
{examples_text}

Copy the URL format from these examples exactly, only changing the timestamp seconds as needed.

Full transcript:
{transcript}"""

            # Prepare litellm parameters
            model_name = f"{self.config.provider.value}/{self.config.model}"

            # Set up litellm configuration
            kwargs = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise summaries of video transcripts in markdown format. Always use proper markdown syntax including headers, bullet points, bold text for emphasis, and clickable timestamp links when referencing specific moments. ALWAYS use the exact video ID provided in timestamp URLs.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            # Add provider-specific parameters
            if self.config.effective_base_url:
                kwargs["base_url"] = self.config.effective_base_url

            response = completion(**kwargs)

            summary = response.choices[0].message.content
            if not summary:
                raise YouTubeSummarizerError("Failed to generate summary: LLM returned empty response")

            return summary
        except Exception as e:
            raise YouTubeSummarizerError(f"Failed to generate summary: {str(e)}")

    def summarize_with_llm(self, transcript: str) -> str:
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
            model_name = f"{self.config.provider.value}/{self.config.model}"

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
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            # Add provider-specific parameters
            if self.config.effective_base_url:
                kwargs["base_url"] = self.config.effective_base_url

            response = completion(**kwargs)

            summary = response.choices[0].message.content
            if not summary:
                raise YouTubeSummarizerError("Failed to generate summary: LLM returned empty response")

            return summary
        except Exception as e:
            raise YouTubeSummarizerError(f"Failed to generate summary: {str(e)}")

    @staticmethod
    def generate_filename_from_metadata(metadata: VideoMetadata, video_id: str) -> str:
        """Generate a filesystem-safe filename from video metadata."""
        # Start with the video title
        title = metadata.title or "Unknown_Title"

        # Clean the title for filesystem use
        cleaned_title = re.sub(r'[<>:"/\\|?*]', "_", title)  # Replace invalid chars
        cleaned_title = re.sub(r"[^\w\s-]", "", cleaned_title)  # Remove other special chars
        cleaned_title = re.sub(r"[-_\s]+", "_", cleaned_title)  # Replace multiple separators
        cleaned_title = cleaned_title.strip("_")  # Remove leading/trailing underscores

        # Truncate if too long (leaving room for video_id and extension)
        max_title_length = 80
        if len(cleaned_title) > max_title_length:
            cleaned_title = cleaned_title[:max_title_length].rstrip("_")

        # New format: title.video_id.md
        filename = f"{cleaned_title}.{video_id}.md"

        # Final safety check - ensure filename isn't too long
        if len(filename) > 200:
            # Fallback to shorter format
            filename = f"{cleaned_title[:50]}.{video_id}.md"

        return filename

    def generate_title_from_summary(self, summary: str) -> str:
        """Generate a meaningful filename from the summary using configured LLM.

        DEPRECATED: Use generate_filename_from_metadata instead for better performance and accuracy.
        """
        try:
            prompt = f"""Based on this video summary, create a short, descriptive filename of 5-6 words maximum using only letters, numbers, and underscores. 
The filename should capture the main topic or key concept. Use underscores to separate words.

Summary: {summary}

Return only the filename without any explanation."""

            # Prepare litellm parameters
            model_name = f"{self.config.provider.value}/{self.config.model}"

            kwargs = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise, descriptive filenames from text summaries. Always use underscores instead of spaces and keep it to 5-6 words maximum.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": self.config.title_max_tokens,
                "temperature": self.config.title_temperature,
            }

            # Add provider-specific parameters
            if self.config.effective_base_url:
                kwargs["base_url"] = self.config.effective_base_url

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

    def save_summary(
        self, video_id: str, summary: str, output_dir: str, metadata: Optional[VideoMetadata] = None
    ) -> str:
        """Save summary to a markdown file with a meaningful name. Returns the file path."""
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Try to generate filename from metadata first
            if metadata:
                filename = self.generate_filename_from_metadata(metadata, video_id)
            else:
                # Fallback to old method if no metadata provided
                try:
                    title = self.generate_title_from_summary(summary)
                    filename = f"{title}.{video_id}.md"
                except YouTubeSummarizerError:
                    # Ultimate fallback to video ID if title generation fails
                    filename = f"summary.{video_id}.md"

            file_path = Path(output_dir) / filename

            # Add metadata to the summary if available
            if metadata:
                # Format view count safely
                view_count_str = f"{metadata.view_count:,}" if metadata.view_count else "N/A"
                duration_str = f"{metadata.duration}s" if metadata.duration else "N/A"

                enhanced_summary = f"""# {metadata.title}

**Channel:** {metadata.channel}  
**Upload Date:** {metadata.upload_date}  
**Video ID:** {video_id}  
**Duration:** {duration_str}  
**Views:** {view_count_str}  

---

{summary}"""
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(enhanced_summary)
            else:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(summary)

            return str(file_path)
        except Exception as e:
            raise YouTubeSummarizerError(f"Failed to save summary for video {video_id}: {str(e)}")
