"""
DEBBY! -- gui/dashboard.py
Phase 6: static dashboard layout. Runs as its OWN process, separate from
brain.py -- reads logs/debby.log on a timer and displays it. No node-graph
animation yet (that's a later polish pass); this just proves the visual
layer can show live activity without slowing down the brain's inference.

Run brain.py in one terminal, this in another (or via xrdp on a second
device), and watch the process log box update as you chat.
"""

import json
import math
import sys
from pathlib import Path

import pygame

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = WORKSPACE_ROOT / "logs" / "debby.log"

# --- theme -----------------------------------------------------
BG_COLOR = (4, 10, 20)
PANEL_BG = (10, 20, 30)
PANEL_BORDER = (0, 200, 180)
TEXT_COLOR = (200, 240, 235)
ACCENT = (0, 230, 200)
DIM_TEXT = (90, 130, 125)
ORB_COLOR = (0, 200, 180)

WIDTH, HEIGHT = 960, 580
FONT_NAME = None  # default pygame font -- swap for a custom monospace later


class LogReader:
    """Polls the shared log file, only returns lines new since last check."""

    def __init__(self, path: Path):
        self.path = path
        self._pos = 0

    def read_new_lines(self):
        if not self.path.exists():
            return []
        entries = []
        with open(self.path, "r") as f:
            f.seek(self._pos)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            self._pos = f.tell()
        return entries


def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("DEBBY!")
    clock = pygame.time.Clock()

    font_header = pygame.font.Font(FONT_NAME, 26)
    font_label = pygame.font.Font(FONT_NAME, 14)
    font_body = pygame.font.Font(FONT_NAME, 16)
    font_log = pygame.font.Font(FONT_NAME, 13)

    reader = LogReader(LOG_PATH)
    chat_lines = []   # list of (role, text)
    process_lines = []  # list of raw strings

    tick = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # --- pull new log entries ---
        for entry in reader.read_new_lines():
            role = entry.get("role")
            etype = entry.get("type")
            content = entry.get("content", "")
            ts = entry.get("timestamp", "")[-8:]  # just HH:MM:SS

            if role in ("user", "assistant"):
                chat_lines.append((role, content))
                chat_lines[:] = chat_lines[-20:]

            process_lines.append(f"[{ts}] [{etype.upper()}] {content[:60]}")
            process_lines[:] = process_lines[-12:]

        screen.fill(BG_COLOR)

        # --- header bar ---
        pygame.draw.rect(screen, PANEL_BG, (0, 0, WIDTH, 50))
        pygame.draw.line(screen, PANEL_BORDER, (0, 50), (WIDTH, 50), 1)
        header_text = font_header.render("D E B B Y !", True, ACCENT)
        screen.blit(header_text, (20, 12))

        # --- center orb (static placeholder for the future neural core) ---
        # Center column is deliberately kept clear -- panels are boxed
        # into the four corners around it, not spanning the full width.
        cx, cy, r = WIDTH // 2, 70 + (HEIGHT - 70) // 2, 60
        pulse = int(6 * math.sin(tick / 30))
        pygame.draw.circle(screen, (0, 60, 55), (cx, cy), r + 30 + pulse, 1)
        pygame.draw.circle(screen, (0, 100, 90), (cx, cy), r + 15, 1)
        pygame.draw.circle(screen, ORB_COLOR, (cx, cy), r, 2)
        status_text = font_label.render("BRAIN: qwen2.5:7b", True, DIM_TEXT)
        screen.blit(status_text, (cx - status_text.get_width() // 2, cy + r + 40))

        # --- layout constants: four corner panels, orb owns the center ---
        margin = 20
        panel_w = 280
        top_y, top_h = 70, 220
        bottom_y, bottom_h = 310, 250
        left_x = margin
        right_x = WIDTH - margin - panel_w

        # --- chat log panel (top-left) ---
        chat_x, chat_y, chat_w, chat_h = left_x, top_y, panel_w, top_h
        pygame.draw.rect(screen, PANEL_BG, (chat_x, chat_y, chat_w, chat_h))
        pygame.draw.rect(screen, PANEL_BORDER, (chat_x, chat_y, chat_w, chat_h), 1)
        label = font_label.render("CONVERSATION", True, ACCENT)
        screen.blit(label, (chat_x + 10, chat_y + 8))

        y_offset = chat_y + 32
        for role, text in chat_lines[-10:]:
            prefix = "YOU: " if role == "user" else "DEBBY!: "
            color = TEXT_COLOR if role == "user" else ACCENT
            wrapped = wrap_text(prefix + text, font_body, chat_w - 20)
            for line in wrapped[:2]:
                rendered = font_body.render(line, True, color)
                screen.blit(rendered, (chat_x + 10, y_offset))
                y_offset += 18
            y_offset += 4
            if y_offset > chat_y + chat_h - 18:
                break

        # --- process log box (bottom-left, matches original architecture doc) ---
        proc_x, proc_y, proc_w, proc_h = left_x, bottom_y, panel_w, bottom_h
        pygame.draw.rect(screen, PANEL_BG, (proc_x, proc_y, proc_w, proc_h))
        pygame.draw.rect(screen, PANEL_BORDER, (proc_x, proc_y, proc_w, proc_h), 1)
        label = font_label.render("SYSTEM_LOG // D.E.B.B.Y", True, ACCENT)
        screen.blit(label, (proc_x + 10, proc_y + 8))

        y_offset = proc_y + 30
        for line in process_lines[-10:]:
            rendered = font_log.render(line, True, DIM_TEXT)
            screen.blit(rendered, (proc_x + 10, y_offset))
            y_offset += 16

        # --- system info panel (top-right) ---
        info_x, info_y, info_w, info_h = right_x, top_y, panel_w, top_h
        pygame.draw.rect(screen, PANEL_BG, (info_x, info_y, info_w, info_h))
        pygame.draw.rect(screen, PANEL_BORDER, (info_x, info_y, info_w, info_h), 1)
        label = font_label.render("SYSTEM_INFO", True, ACCENT)
        screen.blit(label, (info_x + 10, info_y + 8))

        models = ["qwen2.5:7b", "qwen2.5-coder:7b", "deepseek-r1:1.5b"]
        y_offset = info_y + 32
        for m in models:
            rendered = font_body.render(f"- {m}", True, TEXT_COLOR)
            screen.blit(rendered, (info_x + 10, y_offset))
            y_offset += 20

        # --- status panel (bottom-right) ---
        stat_x, stat_y, stat_w, stat_h = right_x, bottom_y, panel_w, bottom_h
        pygame.draw.rect(screen, PANEL_BG, (stat_x, stat_y, stat_w, stat_h))
        pygame.draw.rect(screen, PANEL_BORDER, (stat_x, stat_y, stat_w, stat_h), 1)
        label = font_label.render("STATUS", True, ACCENT)
        screen.blit(label, (stat_x + 10, stat_y + 8))
        hint_text = font_label.render("Run core/brain.py", True, DIM_TEXT)
        screen.blit(hint_text, (stat_x + 10, stat_y + 34))
        hint_text2 = font_label.render("in another terminal to chat", True, DIM_TEXT)
        screen.blit(hint_text2, (stat_x + 10, stat_y + 52))

        pygame.display.flip()
        clock.tick(30)
        tick += 1

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

"""
$""
DEBBY! -- gui/dashboard.py
Phase 6: static dashboard layout. Runs as its OWN process, separate from
brain.py -- reads logs/debby.log on a timer and displays it. No node-graph
animation yet (that's a later polish pass); this just proves the visual
layer can show live activity without slowing down the brain's inference.

Run brain.py in one terminal, this in another (or via xrdp on a second
device), and watch the process log box update as you chat.
""$

import json
import math
import sys
from pathlib import Path

import pygame

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = WORKSPACE_ROOT / "logs" / "debby.log"

# --- theme -----------------------------------------------------
BG_COLOR = (4, 10, 20)
PANEL_BG = (10, 20, 30)
PANEL_BORDER = (0, 200, 180)
TEXT_COLOR = (200, 240, 235)
ACCENT = (0, 230, 200)
DIM_TEXT = (90, 130, 125)
ORB_COLOR = (0, 200, 180)

WIDTH, HEIGHT = 960, 580
FONT_NAME = None  # default pygame font -- swap for a custom monospace later


class LogReader:
    $""Polls the shared log file, only returns lines new since last check.""$

    def __init__(self, path: Path):
        self.path = path
        self._pos = 0

    def read_new_lines(self):
        if not self.path.exists():
            return []
        entries = []
        with open(self.path, "r") as f:
            f.seek(self._pos)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            self._pos = f.tell()
        return entries


def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("DEBBY!")
    clock = pygame.time.Clock()

    font_header = pygame.font.Font(FONT_NAME, 26)
    font_label = pygame.font.Font(FONT_NAME, 14)
    font_body = pygame.font.Font(FONT_NAME, 16)
    font_log = pygame.font.Font(FONT_NAME, 13)

    reader = LogReader(LOG_PATH)
    chat_lines = []   # list of (role, text)
    process_lines = []  # list of raw strings

    tick = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # --- pull new log entries ---
        for entry in reader.read_new_lines():
            role = entry.get("role")
            etype = entry.get("type")
            content = entry.get("content", "")
            ts = entry.get("timestamp", "")[-8:]  # just HH:MM:SS

            if role in ("user", "assistant"):
                chat_lines.append((role, content))
                chat_lines[:] = chat_lines[-20:]

            process_lines.append(f"[{ts}] [{etype.upper()}] {content[:60]}")
            process_lines[:] = process_lines[-12:]

        screen.fill(BG_COLOR)

        # --- header bar ---
        pygame.draw.rect(screen, PANEL_BG, (0, 0, WIDTH, 50))
        pygame.draw.line(screen, PANEL_BORDER, (0, 50), (WIDTH, 50), 1)
        header_text = font_header.render("D E B B Y !", True, ACCENT)
        screen.blit(header_text, (20, 12))

        # --- center orb (static placeholder for the future neural core) ---
        cx, cy, r = WIDTH // 2, 230, 70
        pulse = int(8 * math.sin(tick / 30))
        pygame.draw.circle(screen, (0, 60, 55), (cx, cy), r + 20 + pulse, 1)
        pygame.draw.circle(screen, (0, 100, 90), (cx, cy), r + 10, 1)
        pygame.draw.circle(screen, ORB_COLOR, (cx, cy), r, 2)
        status_text = font_label.render("BRAIN: qwen2.5:7b", True, DIM_TEXT)
        screen.blit(status_text, (cx - status_text.get_width() // 2, cy + r + 15))

        # --- chat log panel (left) ---
        chat_x, chat_y, chat_w, chat_h = 20, 70, 420, 340
        pygame.draw.rect(screen, PANEL_BG, (chat_x, chat_y, chat_w, chat_h))
        pygame.draw.rect(screen, PANEL_BORDER, (chat_x, chat_y, chat_w, chat_h), 1)
        label = font_label.render("CONVERSATION", True, ACCENT)
        screen.blit(label, (chat_x + 10, chat_y + 8))

        y_offset = chat_y + 32
        for role, text in chat_lines[-10:]:
            prefix = "YOU: " if role == "user" else "DEBBY!: "
            color = TEXT_COLOR if role == "user" else ACCENT
            wrapped = wrap_text(prefix + text, font_body, chat_w - 20)
            for line in wrapped[:2]:  # cap wrapped lines per message so panel doesn't overflow
                rendered = font_body.render(line, True, color)
                screen.blit(rendered, (chat_x + 10, y_offset))
                y_offset += 20
            y_offset += 6
            if y_offset > chat_y + chat_h - 20:
                break

        # --- process log box (bottom left, matches original architecture doc) ---
        proc_x, proc_y, proc_w, proc_h = 20, chat_y + chat_h + 15, 420, 130
        pygame.draw.rect(screen, PANEL_BG, (proc_x, proc_y, proc_w, proc_h))
        pygame.draw.rect(screen, PANEL_BORDER, (proc_x, proc_y, proc_w, proc_h), 1)
        label = font_label.render("SYSTEM_LOG // D.E.B.B.Y", True, ACCENT)
        screen.blit(label, (proc_x + 10, proc_y + 8))

        y_offset = proc_y + 30
        for line in process_lines[-6:]:
            rendered = font_log.render(line, True, DIM_TEXT)
            screen.blit(rendered, (proc_x + 10, y_offset))
            y_offset += 16

        # --- right info panel (static placeholder, expand later) ---
        info_x, info_y, info_w, info_h = 460, 70, 480, 475
        pygame.draw.rect(screen, PANEL_BG, (info_x, info_y, info_w, info_h))
        pygame.draw.rect(screen, PANEL_BORDER, (info_x, info_y, info_w, info_h), 1)
        label = font_label.render("SYSTEM_INFO", True, ACCENT)
        screen.blit(label, (info_x + 10, info_y + 8))

        models_text = font_body.render("Models: qwen2.5:7b / qwen2.5-coder:7b / deepseek-r1:1.5b", True, TEXT_COLOR)
        screen.blit(models_text, (info_x + 10, info_y + 40))
        hint_text = font_label.render("(Run core/brain.py in another terminal to chat)", True, DIM_TEXT)
        screen.blit(hint_text, (info_x + 10, info_y + 65))

        pygame.display.flip()
        clock.tick(30)
        tick += 1

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
"""
