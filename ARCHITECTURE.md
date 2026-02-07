# Pogbot — Codebase Walkthrough

## What Is This Project?

Pogbot is a **Discord bot** written in Python. It connects to a Discord server ("guild"), listens for messages, and responds to commands like `!pogcheck`, `!playclip`, `!chat`, etc. It can also join voice channels to play audio, record audio, and even speak using AI-generated text-to-speech.

---

## Project Layout (File Tree)

```
pogbot/                      ← Git repo root
├── pogbot.py                ← OLD monolithic version (everything in one file)
├── pogbot/                  ← NEW modular version (a Python "package")
│   ├── __init__.py          ← Makes this folder a package (empty)
│   ├── __main__.py          ← Entry point: `python -m pogbot` runs this
│   ├── config.py            ← Loads secrets/settings, creates the Discord client
│   ├── storage.py           ← Azure Table/Blob storage + token management
│   ├── utils.py             ← Small helper functions (message chunking, Giphy)
│   ├── commands/            ← All bot commands, split by category
│   │   ├── __init__.py      ← Registers commands & the on_message handler
│   │   ├── ai.py            ← !chat and !image (OpenAI)
│   │   ├── audio.py         ← !pogmedaddy, !playclip, !listen, !leave, etc.
│   │   ├── fun.py           ← !pogcheck, !bettermage, !help
│   │   ├── roast.py         ← !roast (AI-generated roast via TTS)
│   │   └── tts.py           ← !say (anonymous text-to-speech)
│   └── clipping/            ← Voice recording & "clip that" feature
│       ├── __init__.py      ← (empty)
│       ├── detector.py      ← Background task: Whisper transcription, detects "clip that"
│       ├── sink.py          ← RollingBufferSink: captures 30s of voice audio
│       └── web/             ← Web UI for trimming captured clips
│           ├── __init__.py  ← (empty)
│           ├── server.py    ← aiohttp web server with trim/download endpoints
│           └── trimmer.html ← Frontend HTML for the clip trimmer UI
├── requirements.txt         ← Python dependencies (pip install -r requirements.txt)
├── assets/                  ← Audio files, images used by the bot
├── temp_clips/              ← Temporary clip storage (auto-cleaned)
├── *.nix                    ← Nix build/shell configs (deployment related)
└── README.md
```

---

## Python Concepts Explained

### 1. Packages & Modules (`__init__.py`)

In Python, a **module** is just a `.py` file. A **package** is a folder that contains an `__init__.py` file.

```
pogbot/              ← This is a PACKAGE (because it has __init__.py)
├── __init__.py      ← Runs when you `import pogbot`. Can be empty.
├── config.py        ← This is a MODULE. You access it as `pogbot.config`
├── commands/        ← This is a SUB-PACKAGE
│   ├── __init__.py
│   └── audio.py     ← Access as `pogbot.commands.audio`
```

**Why `__init__.py`?** It tells Python "this folder is importable." Without it, Python won't recognize the folder as a package. It runs automatically when anything from that package is imported. It can be empty (as in `pogbot/__init__.py`) or contain code (as in `pogbot/commands/__init__.py` which sets up all the commands).

### 2. `__main__.py` — The Entry Point

When you run `python -m pogbot`, Python looks for `pogbot/__main__.py` and executes it. It's the equivalent of `if __name__ == "__main__":` but for packages. This is how the bot starts up.

In this project, `__main__.py`:
1. Imports `CLIENT`, `TOKEN`, `GUILD` from `config.py`
2. Imports `pogbot.commands` (which *registers* all event handlers as a side effect)
3. Starts a web server for the clip trimmer
4. Calls `CLIENT.run(TOKEN)` to connect to Discord and begin listening

### 3. How Imports Work

There are several styles of import used in this project:

#### Standard library imports
```python
import os          # Built into Python — file system operations
import re          # Built into Python — regular expressions
import asyncio     # Built into Python — async/await support
```
These come with Python. No installation needed.

#### Third-party imports
```python
import discord             # discord.py library — Discord API wrapper
import openai              # OpenAI API client
import aiohttp             # Async HTTP client
from azure.identity import DefaultAzureCredential  # Azure auth
```
These are installed via `pip install -r requirements.txt`. They're listed in `requirements.txt`.

#### Relative/project imports
```python
from pogbot.config import CLIENT, TOKEN, GUILD
from pogbot.storage import get_updated_tokens_for_user
from pogbot.commands.audio import play_unmodified_audio_file
```
These import from *other files in this project*. The dotted path matches the folder structure:
- `pogbot.config` → `pogbot/config.py`
- `pogbot.commands.audio` → `pogbot/commands/audio.py`
- `pogbot.clipping.detector` → `pogbot/clipping/detector.py`

`from X import Y` means "from module X, grab just the name Y." So `from pogbot.config import CLIENT` gives you access to the `CLIENT` variable defined in `config.py`.

#### Import side effects (important!)
In `__main__.py`:
```python
import pogbot.commands  # noqa: F401
```
This looks like it does nothing (no `from ... import ...`), but it's crucial. When Python runs `import pogbot.commands`, it executes `pogbot/commands/__init__.py`, which contains the `@CLIENT.event` decorator on `on_message`. That **registers** the message handler with Discord. Without this import, the bot would never respond to messages.

The `# noqa: F401` comment tells linters "yes, I know this import looks unused — it's intentional."

### 4. Decorators (`@`)

A decorator is a function that **wraps** another function to add behavior. The `@` syntax is shorthand.

#### `@CLIENT.event` — Discord event handlers
```python
@CLIENT.event
async def on_message(message):
    ...
```
This is equivalent to:
```python
async def on_message(message):
    ...
CLIENT.event(on_message)  # Register this function with Discord
```
`CLIENT.event()` tells the Discord library: "When a message arrives, call this function." It **registers** `on_message` as a callback. The Discord library defines many events: `on_ready`, `on_connect`, `on_message`, `setup_hook`, etc.

#### `@dataclass` — Auto-generated class boilerplate
```python
from dataclasses import dataclass, field

@dataclass
class TokenUsage:
    RowKey: str
    PartitionKey: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    tokens: int = 1
```
Without `@dataclass`, you'd have to manually write:
```python
class TokenUsage:
    def __init__(self, RowKey, PartitionKey=..., tokens=1, ...):
        self.RowKey = RowKey
        self.PartitionKey = PartitionKey
        self.tokens = tokens
```
`@dataclass` auto-generates `__init__`, `__repr__`, `__eq__`, and more from the field declarations. `field(default_factory=lambda: ...)` means "each time a new instance is created, call this function to generate the default value" (vs a static default).

### 5. `async` / `await`

Discord bots spend most of their time *waiting* — waiting for messages, waiting for HTTP responses, waiting for audio to finish playing. `async`/`await` lets Python do other work while waiting.

```python
async def process_chat_command(message):      # "async" means this function can pause
    completion = openai.ChatCompletion.create(...)  # This blocks (not ideal)
    for m in messages:
        await message.channel.send(m)          # "await" pauses here until send completes
```

- `async def` declares a **coroutine** (a function that can be paused/resumed)
- `await` pauses the current function until the awaited operation finishes, letting other code run in the meantime
- `asyncio.sleep(0.5)` is the async version of `time.sleep()` — it pauses without blocking other tasks

### 6. `lambda`

```python
COMMANDS = {
    "!pogcheck": lambda msg: handle_pogcheck_message(msg),
}
```
`lambda` creates a small anonymous function. `lambda msg: handle_pogcheck_message(msg)` is equivalent to:
```python
def _anonymous(msg):
    return handle_pogcheck_message(msg)
```
It's used here to defer the function call — the function isn't called when the dict is created, only when someone types `!pogcheck`.

---

## What Each File Does

### `pogbot.py` (root) — The Old Monolithic Bot
This is the **original version** of the bot with everything in one file. It's still there but the project has been refactored into the `pogbot/` package. It contains the same core logic (config, commands, storage) but all mixed together.

### `pogbot/config.py` — Configuration & Secrets
Runs at import time. It:
1. Reads secrets from files pointed to by environment variables (`DISCORD_TOKEN`, `OPEN_AI_KEY`, etc.)
2. Creates the Discord `CLIENT` object with message-content intent enabled
3. Loads the Opus audio codec (needed for voice)
4. Sets up the OpenAI API key

Everything else imports `CLIENT`, `TOKEN`, `dir_path`, etc. from here.

### `pogbot/storage.py` — Azure Storage & Token Economy
Connects to Azure Table Storage and Blob Storage. Manages a **token economy**:
- Each user gets tokens over time (1 per week + gifted tokens)
- Playing clips (`!playclip`) costs 1 token
- TTS (`!say`) costs 1 token
- Roasting (`!roast`) costs 2 tokens
- `TokenUsage` dataclass tracks each user's balance

Also provides `upload_image_to_container()` for saving AI-generated images to Azure Blob Storage.

### `pogbot/utils.py` — Shared Utilities
Two helper functions:
- `split_into_chunks()` — Splits long text into ≤2000 char chunks (Discord's message limit)
- `get_random_image_url()` — Fetches a random GIF from the Giphy API

### `pogbot/commands/__init__.py` — Command Registry & Message Router
This is the **brain** of command dispatch. It:
1. Imports all command handler functions from the sub-modules
2. Builds a `COMMANDS` dict mapping `!command` → handler function
3. Defines `on_message` (decorated with `@CLIENT.event`) which:
   - Ignores messages from the bot itself
   - Auto-reacts with an emoji if "pog" is in the message
   - Routes DM-only commands (`!files`, `!say`, `!roast`)
   - Routes channel commands (most only work in the "poggers" channel)

### `pogbot/commands/audio.py` — Voice & Audio Commands
The most complex command file. Handles:
- **`!pogmedaddy`** — Picks a random audio clip, applies random speed/pitch changes via ffmpeg, plays it
- **`!playclip`** — Plays a specific clip (costs 1 token)
- **`!listen`** — Joins voice channel and starts recording with `RollingBufferSink`
- **`!leave`** — Stops recording and disconnects
- **`!tokens`** / **`!files`** — Info commands
- Inactivity auto-disconnect (5 min timeout)

### `pogbot/commands/fun.py` — Fun/Meme Commands
- **`!pogcheck`** — Rolls a 1-10 "pog rating", picks a funny message, attaches a random GIF
- **`!bettermage`** — Inside joke: shows an image and plays audio
- **`!help`** — Lists all available commands

### `pogbot/commands/ai.py` — AI Commands
- **`!chat`** — Sends a question to GPT-3.5-turbo and replies with the answer
- **`!image`** — Generates an image via DALL-E, saves it to Azure Blob Storage, posts it

### `pogbot/commands/tts.py` — Text-to-Speech
- **`!say`** — DM-only. Converts text to speech via OpenAI TTS API, plays it in the user's voice channel. Anonymous (the bot speaks, not the user). Costs 1 token. 500 char limit.

### `pogbot/commands/roast.py` — AI Roast Generator
- **`!roast @user [context]`** — DM-only. Uses GPT to generate a roast, converts it to speech, plays it in voice. Costs 2 tokens.

### `pogbot/clipping/sink.py` — Audio Recording Buffer
`RollingBufferSink` extends Discord's `AudioSink`. It:
- Receives raw PCM audio from all users in a voice channel
- Mixes audio frames into time-indexed slots
- Keeps only the last 30 seconds (rolling buffer)
- Can snapshot the buffer as a WAV file

### `pogbot/clipping/detector.py` — "Clip That" Detection
A background `asyncio` task that:
1. Every 5 seconds, grabs the last 7 seconds of audio from the sink
2. Sends it to OpenAI Whisper for speech-to-text transcription
3. If the transcript contains "clip that", "clip it", or "save that":
   - Snapshots the full 30-second buffer as a WAV file
   - Generates a unique clip ID
   - Posts a link to the web trimmer in Discord
4. Also runs a cleanup task deleting temp files older than 1 hour

### `pogbot/clipping/web/server.py` — Clip Trimmer Web Server
An `aiohttp` web server (runs inside the bot process) with routes:
- `GET /trim/{clip_id}` — Serves the trimmer HTML UI
- `GET /audio/{clip_id}` — Serves the raw WAV audio file
- `POST /trim/{clip_id}` — Accepts trim start/end times, uses ffmpeg to cut & convert to MP3, saves to `assets/audio/`, notifies the Discord channel

---

## How It All Connects (Boot Sequence)

1. `python -m pogbot` → runs `pogbot/__main__.py`
2. `__main__.py` imports `pogbot.config` → secrets are loaded, `CLIENT` is created
3. `__main__.py` imports `pogbot.commands` → `commands/__init__.py` runs, which imports all command files AND registers `@CLIENT.event async def on_message`
4. `__main__.py` defines `setup_hook` → starts the web server + temp cleanup task
5. `CLIENT.run(TOKEN)` → connects to Discord, starts the event loop
6. When a message arrives → `on_message` routes it to the appropriate handler
7. When `!listen` is used → bot joins voice, starts recording + clip detection

---

## Key Dependencies (requirements.txt)

| Package | What it does |
|---|---|
| `discord.py` | Discord API wrapper (messages, voice, events) |
| `openai` | OpenAI API (GPT chat, DALL-E images, Whisper transcription, TTS) |
| `aiohttp` | Async HTTP client/server (Giphy API, TTS API, clip trimmer web server) |
| `azure-identity` | Azure authentication |
| `azure-data-tables` | Azure Table Storage (token economy) |
| `azure-storage-blob` | Azure Blob Storage (AI-generated images) |
| `numpy` | Random number generation for audio pitch/speed effects |
| `pynacl` | Encryption library required by discord.py for voice |
