"""
Command-line interface for YouTube transcript summarizer.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from .ConfigManager import ConfigManager

from .YouTubeSummarizerError import YouTubeSummarizerError

from .Config import Config
from .YoutubeSummarizer import YouTubeSummarizer


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

    parser.add_argument("--output-dir", "-o", help="Directory to save summaries (overrides config file setting)")

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
        return YouTubeSummarizer.load_urls_from_stdin()


def process_single_url(url: str, summarizer: YouTubeSummarizer, output_dir: str) -> bool:
    """Process a single YouTube URL and return success status."""
    logger = logging.getLogger(__name__)

    # Extract video ID
    video_id = YouTubeSummarizer.get_video_id(url)
    if not video_id:
        logger.error(f"Invalid YouTube URL: {url}")
        return False

    # Check if summary for this video already exists
    existing_files = list(Path(output_dir).glob(f"*.{video_id}.md")) if Path(output_dir).exists() else []
    if existing_files:
        logger.info(f"Summary already exists, skipping: {video_id}")
        return True

    try:
        # Download transcript and metadata
        logger.info(f"Downloading transcript for video ID: {video_id}")
        transcript, metadata, timestamped_segments = YouTubeSummarizer.download_transcript(video_id)
        logger.debug(f"Downloaded transcript ({len(transcript)} characters)")
        logger.debug(f"Video metadata: {metadata.title} by {metadata.channel}")
        logger.debug(f"Extracted {len(timestamped_segments)} timestamped segments")

        # Generate summary with timestamps
        logger.info(f"Generating summary with {summarizer.config.provider.value} ({summarizer.config.model})...")
        summary = summarizer.summarize(transcript, timestamped_segments, video_id)
        logger.debug("Generated summary")

        # Save summary with metadata
        logger.debug("Generating filename from metadata...")
        file_path = summarizer.save_summary(video_id, summary, output_dir, metadata)
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

    # Load configuration
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()

        logger.debug(f"Using LLM provider: {config.provider.value} with model: {config.model}")
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        sys.exit(1)

    # Create summarizer instance
    summarizer = YouTubeSummarizer(config)

    # Determine output directory - CLI argument takes precedence over config file
    output_dir = args.output_dir if args.output_dir is not None else config.default_output_dir
    logger.debug(f"Using output directory: {output_dir} {'(from CLI)' if args.output_dir else '(from config)'}")

    logger.info("🎬 YouTube Transcript Summarizer")
    logger.info("=" * 40)
    logger.info(f"🤖 Using {config.provider.value} with model: {config.model}")

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

        if process_single_url(url, summarizer, output_dir):
            processed += 1
        else:
            failed += 1

    # Final report
    logger.info("=" * 40)
    logger.info("📊 Processing complete!")
    logger.info(f"✓ Successfully processed: {processed}")
    if failed > 0:
        logger.warning(f"✗ Failed: {failed}")
    logger.info(f"📁 Summaries saved in: {Path(output_dir).resolve()}/")


if __name__ == "__main__":
    main()
