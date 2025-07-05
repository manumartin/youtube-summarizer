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

## Configuration

The tool uses a YAML configuration file for all settings. By default, it looks for `config.yaml` in the current directory, but you can specify a custom path with `--config`.

### Quick Start

1. **Set your OpenAI API key**:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

2. **Run the tool** - it works with sensible defaults (GPT-4.1):
   ```bash
   youtube-summarizer https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```

That's it! The tool will automatically use OpenAI's GPT-4.1 model with optimized settings.

### Advanced Configuration

For advanced users who want to customize models, parameters, or use different providers, create a `config.yaml` file:

```yaml
# LLM Provider (openai, anthropic, ollama)
provider: openai

# API Keys (prefer environment variables for security)
api_keys:
  openai: null  # Use OPENAI_API_KEY env var

# Provider configurations
providers:
  openai:
    model: gpt-4.1
    max_tokens: 1500
    temperature: 0.7
    title_max_tokens: 50
    title_temperature: 0.3

# Application settings
app:
  default_output_dir: summaries
  skip_existing: true
```

### Using Different Providers

#### Anthropic Claude
Create a `config.yaml` file:
```yaml
provider: anthropic
api_keys:
  anthropic: null  # Use ANTHROPIC_API_KEY env var
providers:
  anthropic:
    model: claude-3-haiku-20240307
    max_tokens: 1500
    temperature: 0.7
```

#### Ollama (Local)
Create a `config.yaml` file:
```yaml
provider: ollama
providers:
  ollama:
    model: llama3.2:3b
    base_url: http://localhost:11434
    max_tokens: 1500
    temperature: 0.7
```

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

3. Configure your LLM provider (see [LLM Configuration](#llm-configuration) section above)

## Usage

### Command Line Options

```bash
poetry run youtube-summarizer [OPTIONS] [URL]

Options:
  -o, --output-dir DIR    Directory to save summaries (default: from config.yaml)
  -v, --verbose          Enable verbose logging
  -h, --help             Show help message
```

### Example commands

```bash
# Single video with default settings
youtube-summarizer https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Batch processing
cat urls.txt | youtube-summarizer

# Custom output directory
youtube-summarizer --output-dir /path/to/summaries https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

**Note**: All configuration including provider selection, model choice, and parameters are set in the `config.yaml` file.


## FastMCP Server Integration

This tool includes a FastMCP (Model Context Protocol) server that allows you to use the YouTube summarization functionality directly from AI assistants like Cursor with a simple, decorator-based approach.

### Setup in Cursor

1. **Install the tool in your system**:
```bash
# build the dist wheel and install it globally
poetry build
pip install dist/youtubesummaries...
```

2. **Configure MCP in Cursor**:
   Add the following configuration to your Cursor MCP settings (usually in `.cursor/mcp.json` or in your project specific settings for cursor):

#### Basic Configuration (OpenAI):
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

3. **For different providers, create a `config.yaml` file** in your project directory:

```yaml
# For Anthropic (example)
provider: anthropic
api_keys:
  anthropic: null  # Use ANTHROPIC_API_KEY env var

# For Ollama (example)  
provider: ollama
providers:
  ollama:
    model: llama3.2:7b
    base_url: http://localhost:11434
```

**Note**: The MCP server will automatically use the `config.yaml` file in the current directory. If no config file exists, it defaults to OpenAI with GPT-4.1.

### Available MCP Tool

Once configured, you can use this tool from within Cursor:

- **`summarize_youtube_video`**: Summarize a single YouTube video
  - Input: YouTube URL, optional save_to_file flag, optional output_dir
  - Returns: Formatted summary in markdown

### Example Usage in Cursor

Simply ask Cursor to use the YouTube summarizer:

```
"Please summarize this YouTube video: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## Output

- Summaries are saved as markdown files in the specified output directory
- Filenames are automatically generated based on content (e.g., `python_tutorial_basics.dQw4w9WgXcQ.md`)
- Existing summaries are automatically skipped to avoid duplicates based on video id

## How It Works

1. **URL Processing**: Extracts video IDs from YouTube URLs
2. **Transcript Extraction**: Uses yt-dlp to download subtitle files in VTT format
3. **Text Cleaning**: Parses VTT files and removes timestamps/formatting
4. **AI Summarization**: Sends clean transcript to your configured LLM provider for markdown-formatted summarization
5. **Filename Generation**: Creates meaningful filenames from summary content using the LLM
6. **Output**: Saves summaries with descriptive names as markdown files with structured formatting