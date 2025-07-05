# YouTube Transcript Summarizer

A command-line tool that processes YouTube URLs to extract transcripts using **yt-dlp** and generates concise summaries using **multiple LLM providers**. Supports OpenAI, Anthropic, and Ollama models, with both single URL processing and batch processing via pipes. Includes an **MCP (Model Context Protocol) server** for integration with AI assistants like Cursor!

## Features

- Automatic transcript extraction using yt-dlp
- **Multi-LLM support**: OpenAI, Anthropic Claude, and Ollama (local models)
- Intelligent filename generation based on content
- Clean markdown output with structured formatting
- **FastMCP Server** for seamless integration with Cursor and other AI assistants
- Flexible configuration via YAML files

## Prerequisites

- Python 3.12+
- At least one of the following:
  - OpenAI API key
  - Anthropic API key
  - Ollama running locally
- yt-dlp (automatically installed)

## Installation

### Option 1: Install from Wheel (Recommended)

1. **Download and install the latest wheel**:
   ```bash
   pip install youtubesummaries-*.whl
   ```

### Option 2: Install from Source (Development)

1. **Clone and install with Poetry**:
   ```bash
   git clone <repository-url>
   cd youtubesummaries
   poetry install
   ```

## Configuration

The tool uses a `config.yaml` file for configuration, it will try to find it in the following paths:

- `~/.config/youtubesummaries/config.yaml`
- `/etc/xdg/youtubesummaries/config.yaml`
- `./config.yaml` (current directory)

If no config is found a default one will be created.

### Default Configuration

The tool works with sensible defaults using OpenAI's GPT-4.1 model. You only need to set your API key:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

## Usage

### Basic Usage

Summarize a single video:
```bash
youtube-summarizer https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Process multiple URLs from a file:
```bash
cat urls.txt | youtube-summarizer --batch
```

## MCP Server Integration

This tool includes a FastMCP (Model Context Protocol) server that allows you to use the YouTube summarization functionality directly from AI assistants like Cursor with a simple, decorator-based approach.

### Setup in Cursor

1. **Install the tool globally** (see Installation section above)

2. **Configure MCP in Cursor**:
   Add the following configuration to your Cursor MCP settings (usually in `.cursor/mcp.json` or in your project specific settings for cursor):

#### Basic Configuration (OpenAI):

```json
{
  "mcpServers": {
    "youtube-summarizer": {
      "command": "youtube-summarizer-mcp",
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key-here"
      }
    }
  }
}
```

**Note**: The MCP server will automatically use the `config.yaml` file in the current directory. If no config file exists, it defaults to OpenAI with GPT-4.1.

### Available MCP Functions

- **`summarize_youtube_video`**: Summarize a single YouTube video
  - Input: YouTube URL, optional save_to_file flag, optional output_dir
  - Returns: Formatted summary in markdown

### Example Usage in Cursor

Simply ask Cursor to use the YouTube summarizer:

```
"Please summarize this YouTube video: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```