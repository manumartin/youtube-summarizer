"""
YouTube Transcript Summarizer

A simple CLI tool that reads YouTube URLs from a file, downloads their transcripts,
and generates AI-powered summaries using OpenAI's GPT models.
"""

__version__ = "0.1.0"
__author__ = "Manuel Martin"
__email__ = "manuel.martin@getvisibility.com"

from .cli import main

__all__ = ["main"]
