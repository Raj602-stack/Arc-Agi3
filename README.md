# PM07 — Pattern Master

**A 7-level hidden-rule grid puzzle game for ARC-AGI-3**

Each level presents a grid with colored cells and a **hidden rule** the player must discover through experimentation. All 7 levels use **ONLY arrow keys** — no Space bar, no mouse clicking on the grid. Just move, observe, and deduce.

---

## 📁 Project Structure

```
ARC 3-Game/
├── README.md                          # This file
├── play.py                            # CLI entry point
├── play_gui.py                        # Retro arcade GUI (pygame)
└── environment_files/
    └── pm07/
        └── v1/
            ├── pm07.py                # Main game logic (7 levels)
            └── metadata.json          # ARC-AGI-3 game metadata
```

---

## 🚀 Getting Started

### Prerequisites

```bash
# Install dependencies with uv
uv init
uv add arc-agi pygame numpy

# or with pip
pip install arc-agi pygame numpy
```

### Set Your API Key (Optional)

```bash
export ARC_API_KEY="your-api-key-here"
```

### Play the Game

```bash
# Launch the retro arcade GUI (recommended)
uv run python play_gui.py

# Play with a specific seed
uv run python play_gui.py --seed 42

# Skip the boot screen
uv run python play_gui.py --no-boot

# Terminal mode (no GUI)
uv run python play.py

# Run a random agent
uv run python play.py --agent --steps 500

# Run a scripted demo
uv run python play.py --demo
```

### Programmatic Usage

```python
import arc_agi
from arcengine import GameAction

arc = arc_agi.Arcade(environments_dir="./environment_files")
env = arc.make("pm07-v1", seed=0)

# Move with arrow key actions
env.step(GameAction.ACTION1)  # Up
env.step(GameAction.ACTION2)  # Down
env.step(GameAction.ACTION3)  # Left
env.step(GameAction.ACTION4)  # Right

# Undo last action
env.step(GameAction.ACTION7)

# View scorecard
print(arc.get_scorecard())
```

---

## 🎮 Controls

**All 7 levels use ONLY arrow keys.** No Space bar. No mouse clicking on the grid.

| Action   | Keyboard (WASD) | Keyboard (Arrows) | Description              |
|----------|------------------|--------------------|--------------------------|
| ACTION1  | `W`              | `↑`                | Move cursor up           |
| ACTION2  | `S`              | `↓`                | Move cursor down         |
| ACTION3  | `A`              | `←`                | Move cursor left         |
| ACTION4  | `D`              | `→`                | Move cursor right        |
| ACTION7  | `Ctrl+Z`         | `Ctrl+Z`           | Undo last action         |

### GUI-Only Controls

| Key        | Effect                                  |
|------------|-----------------------------------------|
| `R`        | Reset current level                     |
| `Ctrl+R`   | Full game restart (back to Level 1)     |
| `H`        | Toggle hint display                     |
| `ESC` / `Q`| Quit                                   |

---

## 🧩 Level Guide

> **Design Principle:** Rules are **hidden**. Players (and agents) discover them through experimentation. The descriptions below are **spoilers** for reference.

### Level 1 — Color Echo (8×8)

**Difficulty:** ★☆☆☆☆ Tutorial

**Hidden Rule:** Move the cursor around the grid. When you step onto a **gray cell**, it copies the color of the cell you just left. Colored "source" cells are scattered around — walk through them to pick up their color, then walk onto gray cells to paint them.

**Win Condition:** No gray cells remain on the grid.

**What to discover:** Stepping onto gray cells paints them with whatever color you were just standing on.

---

### Level 2 — Flood Walker (8×8)

**Difficulty:** ★★☆☆☆ Basic

**Hidden Rule:** The grid is filled with two colors (cyan and orange). Every cell you walk onto **toggles** between the two colors. Make the entire grid a single uniform color.

**Win Condition:** Every cell on the grid is the same color.

**What to discover:** Moving onto a cell flips its color. You need to plan your path to avoid undoing your progress.

---

### Level 3 — Color Trail (8×8)

**Difficulty:** ★★☆☆☆ Easy-Medium

**Hidden Rule:** As you move, you leave a **colored trail** on every cell you visit. The trail color is determined by the last colored "source" cell you stepped on. Source cells (bright colors) stay permanent — black empty cells get painted as you walk over them. Walls (dark gray) block your path.

**Win Condition:** No black empty cells remain. Every cell is filled with color.

**What to discover:**
1. Moving leaves a trail behind you
2. The trail color comes from the last source cell you touched
3. You must visit a source first to "pick up" its color

---

### Level 4 — Gravity Shift (8×8)

**Difficulty:** ★★★☆☆ Medium

**Hidden Rule:** The grid has colored blocks and matching target markers (muted/darker versions of each block color). Every time you press an arrow key, ALL loose colored blocks **slide** in the **same direction** you moved — like tilting a box of marbles. Blocks slide until they hit a wall, another block, or the grid edge.

**Win Condition:** Every colored block is sitting on its matching target marker.

**What to discover:**
1. Blocks move whenever you move (in the same direction)
2. Blocks slide until they're blocked (not just one step)
3. Each bright block must land on its matching dark-colored target
4. The cursor moves freely to set up your next "tilt"

| Block Color | Target Color |
|-------------|-------------|
| Red         | Brown       |
| Blue        | Teal        |
| Yellow      | Orange      |

---

### Level 5 — Mirror Walk (10×10)

**Difficulty:** ★★★★☆ Medium-Hard

**Hidden Rule:** You control **two cursors** simultaneously. The **white cursor** (main) moves normally with arrow keys. A **pink cursor** (mirror) moves in the **opposite direction** at the same time. Walls block each cursor independently — if one cursor is blocked, the other still moves.

**Win Condition:** The white cursor must be on the **green goal** AND the pink cursor must be on the **pink goal** at the same time.

**What to discover:**
1. There's a second (pink) cursor moving opposite to you
2. Walls block each cursor independently
3. Both cursors must be on their respective goals simultaneously
4. Use walls strategically to "pin" one cursor while moving the other

---

### Level 6 — Light Switch (8×8)

**Difficulty:** ★★★★☆ Hard

**Hidden Rule:** The grid is a field of "lights" — either **ON** (yellow) or **OFF** (blue). When you move your cursor onto a cell, it **toggles** that cell AND its **4 orthogonal neighbors** (up, down, left, right). This is a variant of the classic [Lights Out](https://en.wikipedia.org/wiki/Lights_Out_(game)) puzzle.

**Win Condition:** Turn ALL lights ON (every cell yellow).

**What to discover:**
1. Moving onto a cell affects 5 cells at once (the cell + 4 neighbors)
2. Toggling is its own inverse — pressing the same cell twice cancels out
3. Order doesn't matter, only which cells you visit (parity)
4. The puzzle is guaranteed solvable (generated by reverse-scrambling)

---

### Level 7 — Sokoban Escape (10×10)

**Difficulty:** ★★★★★ Very Hard

**Hidden Rule:** Classic [Sokoban](https://en.wikipedia.org/wiki/Sokoban) mechanics! Walk into a colored block to **push** it one step in your movement direction. Blocks can only be pushed, never pulled. If there's a wall, another block, or the grid edge behind the block, the push fails and nothing moves. Push every block onto its matching target marker.

**Win Condition:** Every colored block sits on its matching target marker.

**What to discover:**
1. Walking into a block pushes it (if space behind it)
2. You can't push a block into a wall or another block
3. Blocks can't be pulled — only pushed!
4. Plan push order carefully — blocks can get permanently stuck against walls
5. Use undo (Ctrl+Z) liberally when you make a mistake

| Block Color | Target Color |
|-------------|-------------|
| Red         | Brown       |
| Blue        | Teal        |
| Yellow      | Orange      |
| Magenta     | Purple      |

---

## 🎯 Progressive Difficulty Design

The 7 levels are designed with a smooth learning curve:

| Level | Name           | Grid  | New Concept                          | Difficulty     |
|-------|----------------|-------|--------------------------------------|----------------|
| 1     | Color Echo     | 8×8   | Movement paints cells                | ★☆☆☆☆ Tutorial |
| 2     | Flood Walker   | 8×8   | Movement toggles cells               | ★★☆☆☆ Basic    |
| 3     | Color Trail    | 8×8   | Trail painting + color pickup        | ★★☆☆☆ Easy-Med |
| 4     | Gravity Shift  | 8×8   | Your movement affects ALL blocks     | ★★★☆☆ Medium   |
| 5     | Mirror Walk    | 10×10 | Simultaneous dual-cursor control     | ★★★★☆ Med-Hard |
| 6     | Light Switch   | 8×8   | Neighborhood toggling (Lights Out)   | ★★★★☆ Hard     |
| 7     | Sokoban Escape | 10×10 | Block pushing + spatial planning     | ★★★★★ V. Hard  |

**Design principles:**
- **Arrow keys only** — consistent, minimal controls across all levels
- **Discoverable rules** — hidden mechanics revealed through experimentation
- **Progressive complexity** — each level introduces one new concept
- **Human-intuitive** — all puzzles are solvable through logical deduction
- **Undo-friendly** — Ctrl+Z encourages safe exploration

---

## 🎨 Color Palette

| Value | Name       | Usage                                      |
|-------|------------|--------------------------------------------|
| 0     | Black      | Background / empty cells                   |
| 1     | Dark Gray  | Walls, obstacles                           |
| 2     | Red        | Blocks, sources                            |
| 3     | Green      | Goals, sources                             |
| 4     | Blue       | Blocks, lights (OFF state)                 |
| 5     | Yellow     | Blocks, lights (ON state)                  |
| 6     | Magenta    | Blocks, sources                            |
| 7     | Orange     | Target markers, flood toggle color         |
| 8     | Cyan       | Flood toggle color                         |
| 9     | Brown      | Target markers (for red blocks)            |
| 10    | Pink       | Mirror cursor, mirror goal                 |
| 11    | Lime       | Decorative                                 |
| 12    | Purple     | Target markers (for magenta blocks)        |
| 13    | Teal       | Target markers (for blue blocks)           |
| 14    | White      | Main cursor                                |
| 15    | Light Gray | Paintable target cells (Level 1)           |

---

## 🔧 Technical Details

### ARC-AGI-3 Compliance

- **Grid sizes:** 8×8 to 10×10 (within 64×64 maximum)
- **Cell values:** 0–15 (full 16-color ARC palette)
- **Actions:** All 7 standard actions implemented (levels use only ACTION1-4 + ACTION7)
- **Undo:** Full state history stack with ACTION7
- **Seeded generation:** Deterministic with `random.Random(seed)`
- **Frame output:** 64×64 pixels (standard ARC frame size)

### Architecture

The game extends `ARCBaseGame` from the `arcengine` package:

1. **`__init__`** — Initialize camera, RNG, and base game
2. **`on_set_level`** — Called when a level loads; generates grid content
3. **`step`** — Main game loop; dispatches to per-level handlers
4. **`_render_grid`** — Syncs the 2D color array into level sprites
5. **`_save_state` / `_undo`** — State history management

Each level has:
- A `_setup_level_N` method for initialization and procedural generation
- A `_step_level_N` method for per-action game logic
- A win condition check that calls `self.next_level()` on success

### Seeded Randomness

All procedural generation uses `random.Random(seed)` ensuring:
- Identical seeds produce identical levels
- Results are reproducible across runs
- Different seeds create varied but fair puzzles

### Retro GUI Features

The `play_gui.py` provides a full retro arcade experience:
- **CRT boot screen** with character-by-character typing animation
- **Animated level transitions** with horizontal wipe bars
- **Scrolling marquee** title banner in the sidebar
- **Progress bar** showing completion across all 7 levels
- **Neon grid border** with pulsing glow effect
- **Subtle CRT effects** — scanlines + vignette (adjustable)
- **Coordinate crosshair** on hover for precise navigation
- **Restart buttons** in sidebar and on win screen

---

## 🤖 Building an Agent

To build an agent for PM07, consider:

1. **Observe** — Read the grid state from each frame
2. **Experiment** — Try different arrow key sequences and observe changes
3. **Hypothesize** — Form a theory about the hidden rule
4. **Plan** — Devise a sequence of moves to satisfy the win condition
5. **Undo** — Use ACTION7 to backtrack from dead ends

Since all levels use only 4 directional actions + undo, the action space is very small (5 actions), making systematic exploration feasible.

```python
import arc_agi
from arcengine import GameAction

arc = arc_agi.Arcade(environments_dir="./environment_files")
env = arc.make("pm07-v1", seed=0)

ACTIONS = [
    GameAction.ACTION1,  # Up
    GameAction.ACTION2,  # Down
    GameAction.ACTION3,  # Left
    GameAction.ACTION4,  # Right
    GameAction.ACTION7,  # Undo
]

frame = env.reset()
for step in range(1000):
    # Your agent logic: analyze frame, choose action
    action = choose_action(frame)
    frame = env.step(action)
    if frame.state.value == "WON":
        break

print(arc.get_scorecard())
```

---

## 📋 Metadata

```json
{
  "game_id": "pm07-v1",
  "default_fps": 10,
  "baseline_actions": [15, 20, 25, 30, 35, 40, 50],
  "tags": ["puzzle", "pattern", "hidden-rules", "grid", "interactive"],
  "local_dir": "environment_files/pm07/v1"
}
```

---

## 📚 Further Reading

- [ARC-AGI-3 Documentation](https://docs.arcprize.org/)
- [Game Schema](https://docs.arcprize.org/core-concepts/games/game-schema)
- [Actions Reference](https://docs.arcprize.org/core-concepts/games/actions)
- [Create ARC-AGI-3 Environment](https://docs.arcprize.org/arc-agi-toolkit/create-environment)
- [ARC Engine Documentation](https://docs.arcprize.org/arc-agi-toolkit)
- [ARC Prize](https://arcprize.org/)

---

## License

This game is created for the ARC-AGI-3 benchmark. See [ARC Prize](https://arcprize.org/) for details.