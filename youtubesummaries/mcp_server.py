"""
MCP Server for YouTube Transcript Summarizer.

This server exposes the YouTube transcript summarization functionality
as MCP tools that can be called from AI assistants like Cursor.
"""

import os

from fastmcp import FastMCP

from .config import Config, load_config
from .core import (
    get_video_id,
    download_transcript,
    summarize_with_llm,
    save_summary,
    YouTubeSummarizerError,
)

# Initialize the FastMCP server
mcp = FastMCP("youtube-summarizer")


def _get_llm_config() -> Config:
    """Get LLM configuration from YAML config."""
    try:
        config = load_config()

        return config
    except Exception as e:
        raise ValueError(f"Failed to get LLM configuration: {str(e)}")


@mcp.tool
def summarize_youtube_video(url: str, save_to_file: bool = False, output_dir: str = "summaries") -> str:
    """Download transcript from a YouTube video and generate a summary using configured LLM.

    Args:
        url: YouTube video URL to summarize
        save_to_file: Whether to save the summary to a file in the summaries directory (default: False)
        output_dir: Directory to save summary files (default: 'summaries')

    Returns:
        Formatted summary in markdown
    """
    try:
        config = _get_llm_config()

        # Extract video ID
        video_id = get_video_id(url)
        if not video_id:
            return f"Error: Invalid YouTube URL: {url}"

        # Download transcript
        transcript = download_transcript(video_id)

        # Generate summary
        summary = summarize_with_llm(transcript, config)

        result_text = f"# YouTube Video Summary\n\n**Video ID:** {video_id}\n**URL:** {url}\n**LLM:** {config.provider.value}/{config.model}\n\n## Summary\n\n{summary}"

        # Save to file if requested
        if save_to_file:
            try:
                file_path = save_summary(video_id, summary, output_dir, config)
                result_text += f"\n\n**File saved** to {file_path}"
            except YouTubeSummarizerError as e:
                result_text += f"\n\n**Warning:** Failed to save file: {str(e)}"

        return result_text
    except YouTubeSummarizerError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def main() -> None:
    """Main entry point function for the script."""
    mcp.run()


if __name__ == "__main__":
    main()
