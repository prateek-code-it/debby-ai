# DEBBY! — Project Workspace

Local, terminal-driven, fully autonomous Agentic OS Desktop Environment.
Built on Debian + i3 + Ollama, no GPU required.

## Folder guide
- `core/`    — orchestrator logic: the brain, router, tool-calling
- `memory/`  — SQLite database (debby.db) + memory read/write helpers
- `tools/`   — sandbox where DEBBY! saves scripts it builds for itself
- `gui/`     — Pygame dashboard (built in Phase 6, not yet)
- `logs/`    — runtime process logs
- `config/`  — model names, file paths, settings (no hardcoded values in code)

## Models (via Ollama)
- `qwen2.5:7b`        — the Brain / orchestrator, talks to the user directly
- `qwen2.5-coder:7b`  — the Engineer, loaded on demand for coding tasks
- `deepseek-r1:1.5b`  — fast router/classifier

## Current phase
Phase 1 complete — structure + git. See project roadmap for what's next.

## Quick git reference
    git add .
    git commit -m "short description of what changed"
    git log --oneline          # see snapshot history
    git checkout <hash> -- path/to/file   # restore one file from a snapshot
