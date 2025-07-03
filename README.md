# YouTube Transcript Summarizer

A command-line tool that processes YouTube URLs to extract transcripts using **yt-dlp** and generates concise summaries using OpenAI's GPT models. Supports both single URL processing and batch processing via pipes. Includes an **MCP (Model Context Protocol) server** for integration with AI assistants like Cursor!

## Features

- Automatic transcript extraction using yt-dlp
- AI-powered summarization with OpenAI GPT models
- Intelligent filename generation based on content
- Clean markdown output with structured formatting
- **FastMCP Server** for seamless integration with Cursor and other AI assistants

## Prerequisites

- Python 3.12+
- OpenAI API key
- yt-dlp (automatically installed)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd youtubesummaries
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Set your OpenAI API key as an environment variable:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

### Command Line Options

```bash
poetry run youtube-summarizer [OPTIONS] [URL]

Options:
  -o, --output-dir DIR    Directory to save summaries (default: current directory)
  -v, --verbose          Enable verbose logging
  -h, --help             Show help message
```

### Example commands

```bash
# Single video
youtube-summarizer https://www.youtube.com/watch?v=dQw4w9WgXcQ

# For multiple videos
cat urls.txt | youtube-summarizer
```


## FastMCP Server Integration

This tool includes a FastMCP (Model Context Protocol) server that allows you to use the YouTube summarization functionality directly from AI assistants like Cursor with a simple, decorator-based approach.

### Setup in Cursor

1. **Install the tool in your system**:
```bash
pip install dist/youtubesummaries...
```

2. **Configure MCP in Cursor**:
   Add the following configuration to your Cursor MCP settings (usually in `.cursor/mcp.json` or in your project specific settings for cursor):

```json
{
  "mcpServers": {
    "youtube-summarizer": {
      "command": "path/to/youtube-summarizer-mcp",
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key-here"
      }
    }
  }
}
```



### Available MCP Tools

Once configured, you can use these tools from within Cursor:

- **`summarize_youtube_video`**: Summarize a single YouTube video
  - Input: YouTube URL, optional save_to_file flag
  - Returns: Formatted summary in markdown

### Example Usage in Cursor

Simply ask Cursor to use the YouTube summarizer:

```
"Please summarize this YouTube video: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## Output

- Summaries are saved as markdown files in the specified output directory
- Filenames are automatically generated based on content (e.g., `python_tutorial_basics.dQw4w9WgXcQ.md`)
- Existing summaries are automatically skipped to avoid duplicates
- Progress and results are logged with clean, structured messages

## How It Works

1. **URL Processing**: Extracts video IDs from YouTube URLs
2. **Transcript Extraction**: Uses yt-dlp to download subtitle files in VTT format
3. **Text Cleaning**: Parses VTT files and removes timestamps/formatting
4. **AI Summarization**: Sends clean transcript to OpenAI GPT-4.1 for markdown-formatted summarization
5. **Filename Generation**: Creates meaningful filenames from summary content
6. **Output**: Saves summaries with descriptive names as markdown files with structured formatting

## Dependencies

- **yt-dlp**: For downloading YouTube subtitle files
- **openai**: For GPT-powered summarization
- **mcp**: For FastMCP (Model Context Protocol) server functionality
- **Python 3.12+**: Core runtime