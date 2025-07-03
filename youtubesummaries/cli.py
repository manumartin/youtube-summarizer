"""
Command-line interface for YouTube transcript summarizer.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List

from openai import OpenAI

from .core import (
    get_video_id,
    load_urls_from_stdin,
    download_transcript,
    summarize_with_openai,
    save_summary,
    YouTubeSummarizerError,
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s", handlers=[logging.StreamHandler()])


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="YouTube Transcript Summarizer - Generate summaries from YouTube video transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://www.youtube.com/watch?v=dQw4w9WgXcQ
  cat urls.txt | %(prog)s
  %(prog)s --output-dir summaries https://www.youtube.com/watch?v=dQw4w9WgXcQ
        """,
    )

    parser.add_argument("url", nargs="?", help="Single YouTube URL to process (or pipe URLs via stdin)")

    parser.add_argument(
        "--output-dir", "-o", default=".", help="Directory to save summaries (default: current directory)"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    return parser.parse_args()


def get_urls_from_input(args: argparse.Namespace) -> List[str]:
    """Get URLs from various input sources."""
    logger = logging.getLogger(__name__)

    if args.url:
        # Single URL from command line
        logger.debug(f"Processing single URL: {args.url}")
        return [args.url]
    else:
        # URLs from stdin (piped input)
        if sys.stdin.isatty():
            # No piped input and no arguments provided
            logger.error("No input provided. Use --help for usage information.")
            sys.exit(1)

        logger.debug("Reading URLs from stdin")
        return load_urls_from_stdin()


def process_single_url(url: str, client: OpenAI, output_dir: str) -> bool:
    """Process a single YouTube URL and return success status."""
    logger = logging.getLogger(__name__)

    # Extract video ID
    video_id = get_video_id(url)
    if not video_id:
        logger.error(f"Invalid YouTube URL: {url}")
        return False

    # Check if summary for this video already exists
    existing_files = list(Path(output_dir).glob(f"*.{video_id}.md")) if Path(output_dir).exists() else []
    if existing_files:
        logger.info(f"Summary already exists, skipping: {video_id}")
        return True

    try:
        # Download transcript
        logger.info(f"Downloading transcript for video ID: {video_id}")
        transcript = download_transcript(video_id)
        logger.debug(f"Downloaded transcript ({len(transcript)} characters)")

        # Generate summary
        logger.info("Generating summary with OpenAI...")
        summary = summarize_with_openai(transcript, client)
        logger.debug("Generated summary")

        # Save summary
        logger.debug("Generating filename...")
        file_path = save_summary(video_id, summary, output_dir, client)
        logger.info(f"Summary saved: {file_path}")
        return True

    except YouTubeSummarizerError as e:
        logger.error(f"Error processing {url}: {str(e)}")
        if e.details:
            logger.debug(f"Details: {e.details}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing {url}: {e}")
        return False


def main() -> None:
    """Main function to orchestrate the entire process."""
    # Parse arguments first to handle --help and --verbose
    args = parse_arguments()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set.")
        logger.error("Please set it with: export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    logger.info("🎬 YouTube Transcript Summarizer")
    logger.info("=" * 40)

    # Get URLs from input source
    try:
        urls = get_urls_from_input(args)
        logger.info(f"Found {len(urls)} URLs to process...")
    except YouTubeSummarizerError as e:
        logger.error(str(e))
        sys.exit(1)

    if not urls:
        logger.warning("No URLs found to process.")
        sys.exit(0)

    # Process each URL
    processed = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        logger.info(f"[{i}/{len(urls)}] Processing: {url}")

        if process_single_url(url, client, args.output_dir):
            processed += 1
        else:
            failed += 1

    # Final report
    logger.info("=" * 40)
    logger.info("📊 Processing complete!")
    logger.info(f"✓ Successfully processed: {processed}")
    if failed > 0:
        logger.warning(f"✗ Failed: {failed}")
    logger.info(f"📁 Summaries saved in: {Path(args.output_dir).resolve()}/")


if __name__ == "__main__":
    main()
