# DEBBY! — Local Agentic OS Assistant

A local, terminal-driven, fully autonomous AI assistant running entirely
offline on Debian + Ollama. No GPU, no cloud dependency, no recurring
API costs — built to run on modest hardware (currently a VM with
4 cores / 16GB RAM, targeting a GMKtec G10-class mini PC).

## Architecture

Three-model design, none of them ever running simultaneously — Ollama
loads/unloads on demand:

- **`qwen2.5:7b`** — the Brain. Handles normal conversation, the only
  model that talks to you directly for regular chat.
- **`qwen2.5-coder:7b`** — the Engineer. Loaded only when a coding /
  scripting / automation request comes in.
- **`qwen2.5:1.5b`** — the Router. Fast classification of every
  message (chat / code / internet / app) plus quiet preference
  detection, merged into a single model call per message.
- **`deepseek-r1:1.5b`** — Deep reasoning, on-demand only via `/deep`.
  Not used as the default router because it "thinks" at length on
  every request, which is too slow for routine classification.

## Folder guide

- `core/` — orchestrator logic: brain, router, coder handoff, search,
  voice, file reading, OS bridge, admin auth
- `memory/` — SQLite database (`debby.db`) + `memory_helper.py`
- `tools/` — scripts DEBBY! has built for itself, saved here
- `gui/` — Pygame dashboard (separate process from `brain.py`)
- `logs/` — runtime event log, read live by the GUI
- `config/` — `config.json` (models, settings) and
  `authorized_apps.json` (hard allowlist for app launching)

## Features

- **Persistent memory** — conversations, learned facts, and
  preferences all survive restarts, scoped per authenticated user
- **Internet search with offline caching** — checks what it already
  knows before ever asking permission to search; anything it learns
  gets saved for next time, no repeat searches
- **Real authentication** — PIN-based login, admin-only user
  management (`core/admin.py` is the *only* place accounts can be
  created or deleted — `brain.py` can only log into existing ones)
- **Tool-building** — hands coding requests to the Coder model, saves
  the result to `tools/`, logs it in the database
- **App launching** — natural language ("open chromium") matched
  against a hard-coded allowlist, never launches anything not
  explicitly authorized
- **Voice input/output** — `/voice` records + transcribes offline via
  faster-whisper; replies are spoken back only when you spoke to it,
  typed conversations stay silent
- **File reading** — `/file <path> [question]` reads text files and
  PDFs, answers questions about them
- **Deep reasoning on demand** — `/deep <question>` for when you
  actually want DeepSeek-R1's full chain-of-thought, without paying
  that cost on every routine message
- **AirLLM-ready** — disabled by default (CPU-only hardware doesn't
  benefit from it), but the integration exists and is a one-line
  config flip away for whenever there's a GPU in the picture
- **Live GUI dashboard** — Pygame, runs as its own process, reads a
  shared log file so it never competes with the brain for CPU

## Commands reference

| Command | What it does |
|---|---|
| (plain text) | Normal chat — routed automatically to chat/code/internet/app |
| `/deep <question>` | Full DeepSeek-R1 reasoning, slower but deeper |
| `/voice` or `/voice <seconds>` | Speak instead of typing |
| `/file <path> [question]` | Ask about a text file or PDF |
| `/airllm <question>` | Disabled by default — see config.json |
| `exit` / `quit` | Stop the session |

## Setup

See `setup_debby.sh` for full environment setup (Debian packages,
Ollama, Python venv). Broad strokes:

```bash
bash setup_debby.sh
source ~/debby_ai/bin/activate
python3 memory/init_memory.py       # first time only
python core/admin.py                # create your first user account
python core/brain.py                # start chatting
```

Run the GUI separately, in its own terminal:
```bash
python gui/dashboard.py
```

## Known limitations (by design, not bugs)

- CPU-only inference — no GPU, so response speed is a real, actively
  managed constraint (hence the fast router + on-demand `/deep` split)
- PIN auth is appropriate for a trusted home device, not hardened
  against a determined attacker with database access
- Knowledge-cache topic matching is simple keyword extraction, not
  deep NLP — works well, occasionally misses on very differently
  phrased repeat questions
- File reading caps at ~6000 characters per file, and PDFs need a real
  text layer (no OCR yet — scanned image-only PDFs won't extract)

## Roadmap / what's left

- [ ] Camera / vision input
- [ ] Wire `/file` and app-launching more deeply into natural
      conversation flow (currently explicit commands)
- [ ] Package as a bootable ISO via `live-build` for real hardware
- [ ] Migrate off the VM onto physical mini PC hardware

## Tech stack

Debian · i3 · Ollama · Python · SQLite · Pygame · faster-whisper ·
pyttsx3/espeak-ng · pypdf · ddgs (DuckDuckGo search) 
