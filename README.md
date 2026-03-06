# LangChain Chatbot (NexusAI)

NexusAI is a Flask web chatbot built with LangChain + Ollama, with optional Tavily web search for live information.

## Features

- Local LLM responses via Ollama (`ChatOllama`)
- Flask web GUI chat interface
- Session-based chat history
- Token-budget context trimming with `tiktoken`
- Tavily web search support:
- Hard trigger from GUI toggle
- Auto trigger for explicit web/current-event queries
- Auto trigger for out-of-domain questions (router)

## Prerequisites

- Python 3.11+
- Ollama installed and running
- `uv` recommended (`pip` also works)
- Tavily API key (required only for web search)

## Quick Start

1. Clone and enter the repo

```bash
git clone -b main https://github.com/the-schoolofai/langchain-chatbot.git
cd langchain-chatbot
```

2. Install dependencies

```bash
uv sync
```

3. Prepare environment

```bash
cp .env.example .env
```

Set at least:

```env
MODEL_NAME=qwen3.5:cloud
TEMPERATURE=0.7
MAX_TOKENS=3000
RESERVE_TOKENS=800
TAVILY_API_KEY=tvly-your-key-here
BOT_DOMAIN=software engineering, programming, AI tooling, and developer workflows
```

4. Run the app

```bash
uv run python run.py
```

5. Open in browser

```text
http://localhost:5000
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `MODEL_NAME` | `qwen3.5:cloud` | Ollama model name |
| `TEMPERATURE` | `0.7` | Generation temperature |
| `MAX_TOKENS` | `3000` | Total context budget |
| `RESERVE_TOKENS` | `800` | Reserved budget for response |
| `TAVILY_API_KEY` | _(empty)_ | Tavily key for web search |
| `BOT_DOMAIN` | coding-focused text | Used by router for out-of-domain detection |
| `FLASK_PORT` | `5000` | Web server port |
| `FLASK_DEBUG` | `false` | Flask debug mode |

## Project Structure

```text
langchain-chatbot/
|- app/
|  |- chatbot.py          # Core chat + routing + context management
|  |- web_search.py       # Tavily integration
|  |- routes.py           # Flask API endpoints
|  |- templates/          # HTML
|  `- static/             # CSS + JS
|- run.py                 # Flask entry point
|- main.py                # Legacy CLI chatbot example
|- .env.example
|- pyproject.toml
`- requirements.txt
```

## Notes

- If `TAVILY_API_KEY` is missing, forced web search returns an explicit error.
- Non-web queries still work without Tavily using local model knowledge.

## License

MIT. See [LICENSE](LICENSE).
