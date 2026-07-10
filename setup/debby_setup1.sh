#!/bin/bash
# ============================================================
#  DEBBY! Phase 1 — Project structure + version control
#  Run this INSIDE your VM, from anywhere (it cd's itself)
# ============================================================
set -e

cd ~/debby_ai/workspace

echo "=== Creating folder structure ==="
mkdir -p core memory tools gui logs config
# memory/ already has debby.db and init_memory.py from setup — untouched

echo "=== Git init ==="
git init

echo "=== Git identity (edit these if you want your real name/email) ==="
git config user.name "Debby Dev"
git config user.email "debby@localhost"

echo "=== Writing .gitignore ==="
cat > .gitignore << 'EOF'
# Database — changes constantly, not really "code"
*.db
*.db-journal

# Python cache
__pycache__/
*.pyc

# The virtual environment itself — huge, regenerable, never track it
../debby_ai/bin/
../debby_ai/lib/
../debby_ai/pyvenv.cfg

# Logs — regenerated every run, no need to version them
logs/*.log

# Anything DEBBY! builds for itself at runtime, if it gets noisy
tools/__generated__/
EOF

echo "=== Writing README.md ==="
cat > README.md << 'EOF'
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
EOF

echo "=== First commit ==="
git add .
git commit -m "Phase 1: project structure, gitignore, README"

echo ""
echo "============================================================"
echo " Phase 1 complete."
echo " Folders created: core/ memory/ tools/ gui/ logs/ config/"
echo " Git initialized with first commit."
echo " Run 'git log --oneline' to confirm the commit landed."
echo "============================================================"
