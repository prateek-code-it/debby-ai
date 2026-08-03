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

## Compatibility

**Supported: Debian-based (Debian, Ubuntu) and Arch-based (Arch,
Manjaro) systems.** `install.sh` detects which family you're on and
branches the package-manager commands accordingly. Anything else
(Fedora, openSUSE, etc.) gets a clear error message instead of
failing halfway through with confusing output.

**Debian support is the primary, most-tested path** — it's what this
whole project was built and run on throughout development. **Arch
support was added afterward** and is less battle-tested. A few things
to know if you're on Arch:
- Arch is rolling-release, so package names/versions can drift over
  time in ways Debian's stable releases don't — if a `pacman` command
  fails, check whether a package got renamed upstream.
- The sudo bootstrap step edits `/etc/sudoers` directly to enable the
  `wheel` group (Debian's `sudo` group setup is simpler and doesn't
  need this). The script backs up `/etc/sudoers` first
  (`/etc/sudoers.debby_backup`), but this is inherently a more
  sensitive step than the Debian equivalent — worth double-checking
  sudo works correctly after the reboot.

**Minimum hardware**: 4 CPU cores, 8GB RAM (16GB comfortable), no GPU
required (everything runs CPU-only via Ollama). ~30GB free disk space
for the OS + all four models + Python dependencies.

**Tested on**: Debian 13 (Trixie), minimal/no-GUI install.

## Setup — the short version

If you're starting from a truly minimal system (just Debian + git):

```bash
python3 -m venv ~/debby_ai
cd ~/debby_ai
git clone <your-repo-url> workspace
cd workspace
bash install.sh
```

`install.sh` does everything in one pass: checks your OS is actually
Debian-based, sets up a swapfile, installs all system packages (i3,
X11, xrdp, audio libs, etc), installs Ollama and pulls all four
models, creates the Python venv dependencies, initializes the
database, and configures X11 autostart. Takes a while (mostly Ollama
model downloads) — let it run to completion.

**First-time sudo note**: if you're logged in as `root` when you run
it, it'll set up sudo access for your user and ask you to reboot and
re-run the script — that's expected, not a bug, just how the very
first bootstrap step has to work.

Once it finishes:
```bash
source ~/debby_ai/bin/activate
cd ~/debby_ai/workspace
python core/admin.py     # create your first user account (admin-only, one-time)
python core/brain.py     # start chatting
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
