# Ethara AI × ARC AGI Platform

A unified web platform for playing **ARC-AGI-2** puzzles and **ARC-AGI-3** interactive games — built with Flask, SocketIO, and real-time game rendering.

**Live:** Deployed on Railway  
**Stack:** Python 3.12 · Flask · Flask-SocketIO · Eventlet · Gunicorn · arc-agi SDK

---

## Overview

This platform hosts two types of ARC challenges side by side:

- **ARC-AGI-2** — Classic pattern recognition puzzles. Given input/output examples, identify the hidden transformation rule and solve the test grid.
- **ARC-AGI-3** — Real-time interactive game environments. Use keyboard controls to navigate grid-based puzzles with hidden rules, multiple levels, and instant feedback.

The web interface provides a landing page with both sections, card-based browsing with preview thumbnails, and direct game/puzzle launch on click.

---

## Project Structure

```
ARC 3-Game/
├── web/
│   ├── server.py                  # Flask + SocketIO web server
│   ├── templates/
│   │   ├── landing.html           # Home page — AGI-2 + AGI-3 side by side
│   │   ├── index.html             # AGI-3 game player (WebSocket-based)
│   │   ├── grid-test.html         # AGI-3 grid testing page
│   │   └── upload-test.html       # Upload testing page
│   └── static/                    # Static assets
├── ARC-AGI copy/
│   ├── apps/
│   │   ├── index.html             # AGI-2 puzzle player
│   │   ├── js/
│   │   │   └── task_index_data.js # AGI-2 task index (JS)
│   │   └── css/
│   │       └── responsive.css     # AGI-2 responsive styles
│   ├── data/
│   │   ├── training/              # 400 training puzzles
│   │   ├── evaluation/            # 400 evaluation puzzles
│   │   └── my_tasks/              # Custom uploaded tasks
│   └── task_index.json            # AGI-2 task registry
├── environment_files/             # AGI-3 game environments (auto-discovered)
│   ├── ga85/v1/                   # Game: ga85-v1
│   └── pm07/v1/                   # Game: pm07-v1
├── Dockerfile                     # Multi-stage Docker build
├── start.sh                       # Production entrypoint (gunicorn + eventlet)
├── railway.json                   # Railway deployment config
├── railway.toml                   # Railway build config
├── pyproject.toml                 # Python project & dependencies
├── requirements.txt               # Pip fallback dependencies
├── play.py                        # CLI game runner
├── play_gui.py                    # Retro arcade GUI (pygame)
└── README.md                      # This file
```

---

## Getting Started

### Prerequisites

```bash
# Python 3.12+
python --version

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

### Run the Web Server (Development)

```bash
# Start the server on port 8080
python web/server.py

# Custom port
PORT=3000 python web/server.py
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

### Run with Gunicorn (Production)

```bash
./start.sh

# Or manually
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8080 web.server:app
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Server port |
| `HOST` | `0.0.0.0` | Bind address |
| `WORKERS` | `1` | Gunicorn worker count |
| `ADMIN_USERNAME` | `admin` | Admin panel username |
| `ADMIN_PASSWORD` | `12345` | Admin panel password |
| `SECRET_KEY` | `ethara-arc-dev-key` | Flask secret key |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

---

## Features

### Landing Page (`/`)

- **AGI-2 section** — Browse 807 puzzles across My Tasks, Training (400), and Evaluation (400) categories with card previews and tab navigation
- **AGI-3 section** — Browse interactive games with live preview thumbnails
- **Horizontal carousel** — Scroll through cards with ‹ › buttons
- **Upload support** — Upload custom `.json` tasks (AGI-2) or game environments (AGI-3)
- **Admin mode** — Login to delete games/tasks
- **Keyboard shortcuts** — Press `?` for help panel
- **Animated background** — Synthwave perspective grid animation
- **Fully responsive** — Optimized for 13" laptops, tablets, phones (320px–4K)

### AGI-3 Game Player (`/arc-agi-3`)

- **Real-time gameplay** — WebSocket-based communication with the game engine
- **Keyboard controls** — Arrow keys / WASD for movement, Space for action, Ctrl+Z for undo
- **Mobile controls** — D-pad and action buttons with touch support
- **Tap interaction** — Canvas tap support for games using click actions (ACTION6)
- **Live preview** — Game state rendered on HTML5 canvas
- **Progress tracking** — Level progress bar and session management
- **Upload panel** — Upload new game environments (`.py` + `metadata.json`)
- **Admin panel** — Delete games with admin credentials

### AGI-2 Puzzle Player (`/arc-agi-2`)

- **Task browser** — Modal with search, tabs, pagination, and card previews
- **Grid editor** — Interactive grid with color palette for solving puzzles
- **Upload custom tasks** — Load your own `.json` puzzle files
- **Validation** — Input/output grid validation with toast notifications

### Navigation

Both game pages have a minimal navbar: **Logo** (links home) + **🏠 HOME** button. No clutter.

---

## AGI-3 Game Environments

Games are auto-discovered from the `environment_files/` directory. Each game follows this structure:

```
environment_files/
└── <game_id>/
    └── <version>/
        ├── <game_id>.py       # Game logic (extends ARCBaseGame)
        └── metadata.json      # Game metadata
```

### Adding a New Game

1. Create a directory: `environment_files/mygame/v1/`
2. Add `mygame.py` with your game class extending `ARCBaseGame`
3. Add `metadata.json`:

```json
{
  "game_id": "mygame-v1",
  "default_fps": 10,
  "baseline_actions": [15, 20, 25],
  "tags": ["puzzle", "grid"]
}
```

4. Restart the server — the game appears automatically

### Included Games

| Game | Description |
|---|---|
| **pm07-v1** | Pattern Master — 7-level hidden-rule grid puzzle. Arrow keys only. Progressive difficulty from tutorial to Sokoban. |
| **ga85-v1** | Grid puzzle game environment |

### Controls (AGI-3)

| Action | Keyboard | Description |
|---|---|---|
| ACTION1 | `W` / `↑` | Move up |
| ACTION2 | `S` / `↓` | Move down |
| ACTION3 | `A` / `←` | Move left |
| ACTION4 | `D` / `→` | Move right |
| ACTION5 | `Space` / `Enter` | Primary action |
| ACTION6 | Click / Tap | Grid interaction |
| ACTION7 | `Ctrl+Z` | Undo |

---

## Programmatic Usage

```python
import arc_agi
from arcengine import GameAction

arc = arc_agi.Arcade(environments_dir="./environment_files")
env = arc.make("pm07-v1", seed=0)

# Play with actions
env.step(GameAction.ACTION1)  # Up
env.step(GameAction.ACTION2)  # Down
env.step(GameAction.ACTION3)  # Left
env.step(GameAction.ACTION4)  # Right
env.step(GameAction.ACTION7)  # Undo

# View scorecard
print(arc.get_scorecard())
```

### CLI Play

```bash
# Retro arcade GUI (pygame)
uv run python play_gui.py

# Terminal mode
uv run python play.py

# Random agent
uv run python play.py --agent --steps 500
```

---

## Deployment

### Docker

```bash
docker build -t arc-platform .
docker run -p 8080:8080 arc-platform
```

### Railway

The project is configured for one-click Railway deployment:

- **Build:** Dockerfile-based (multi-stage, Python 3.12 slim)
- **Start:** `./start.sh` (gunicorn + eventlet)
- **Health check:** `GET /health`
- **Auto-restart:** On failure, max 5 retries

Push to `main` and Railway deploys automatically.

---

## Responsive Design

The platform is optimized across all device sizes with 11 breakpoints:

| Breakpoint | Target | Card Size |
|---|---|---|
| ≥1400px | Large desktops | 180×238px |
| ≤1399px | Laptops / 13" screens | 150×198px |
| ≤1199px | Smaller desktops | 140×185px |
| ≤1099px | Tablets landscape | 130×172px |
| ≤899px | Tablets portrait | 120×160px |
| ≤767px | Large phones | 115×154px |
| ≤599px | Phones | 105×142px |
| ≤479px | Small phones | 95×128px |
| ≤359px | Tiny phones | 85×115px |

Additional handling for landscape orientation and high-DPI/Retina displays.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, Flask, Flask-SocketIO |
| **Real-time** | WebSocket via Eventlet |
| **Game Engine** | arc-agi SDK, arcengine |
| **Frontend** | Vanilla HTML/CSS/JS, HTML5 Canvas |
| **Production** | Gunicorn + Eventlet workers |
| **Container** | Docker (multi-stage build) |
| **Deployment** | Railway |
| **Local GUI** | Pygame (retro arcade mode) |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/arc-agi-3` | AGI-3 game lobby |
| `GET` | `/arc-agi-3/game/:id` | Direct game launch |
| `GET` | `/arc-agi-2` | AGI-2 puzzle player |
| `GET` | `/api/games` | List available AGI-3 games |
| `GET` | `/api/games/:id/preview` | Game preview thumbnail |
| `POST` | `/api/games/upload` | Upload new game environment |
| `POST` | `/api/games/delete` | Delete game (admin) |
| `POST` | `/api/admin/login` | Admin authentication |
| `GET` | `/api/agi2/task-preview/:cat/:file` | AGI-2 task preview |
| `GET` | `/health` | Health check |

WebSocket events handle real-time game sessions (connect, start_game, action, restart, etc.).

---

## License

Built by [Ethara.AI](https://ethara.ai) for the ARC Prize. See [arcprize.org](https://arcprize.org/) for details.