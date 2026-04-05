# cybershoke-server-picker-tui

The Cybershoke web UI is bloated with pop-ups and wastes a browser tab. This is a lightweight terminal alternative — same live server list, no browser overhead.

A terminal UI for browsing and connecting to [Cybershoke](https://cybershoke.net) CS2 servers. Fetches live data from the Cybershoke API, lets you filter by game mode and category, shows real-time player counts, and launches CS2 via Steam on selection.

## Features

- Live server list with auto-refresh every 30 seconds
- Filter by mode (DM, MULTICFGDM, SURF, BHOP, KZ, RETAKE, and more)
- Filter by category (EASY / MEDIUM / HARD tiers, slot counts, etc.)
- Player count displayed as `current/max`, colour-coded green (joinable) or red (full)
- Connect to a server directly — launches CS2 via Steam
- Selection state (mode + category) preserved across refreshes

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- CS2 installed via Steam
- Linux (uses `xdg-open` for Steam URLs)

## Installation

```bash
git clone https://github.com/tom-jm69/cybershoke-server-picker-tui
cd cybershoke-server-picker-tui
uv sync
```

## Usage

```bash
uv run main.py
```

Or install globally and run from anywhere:

```bash
uv tool install .
cybershoke
```

## Keybindings

| Key | Action |
|-----|--------|
| `h` / `l` | Switch mode tab left / right |
| `H` / `L` | Switch category tab left / right |
| `j` / `k` | Move cursor down / up |
| `g` / `G` | Jump to top / bottom |
| `ctrl+d` / `ctrl+u` | Half-page down / up |
| `enter` | Connect to selected server |
| `s` | Toggle sort (players / ping) |
| `r` | Force refresh |
| `q` | Quit |

## Project structure

```
src/
  cybershoke/
    client.py   — HTTP client for the Cybershoke API
    models.py   — Pydantic models for the API response
  tui/
    app.py      — Textual application + entry point
    service.py  — Data layer (refresh, filtering, sorting)
main.py
```
