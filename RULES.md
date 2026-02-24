# PM07 — Pattern Master: Game Rules

**7 levels. Arrow keys only. Discover the hidden rule. Solve the puzzle.**

Pattern Master is a grid-based puzzle game where each level hides a secret rule you must figure out by experimenting. Move your cursor with arrow keys, watch how the grid reacts, and deduce what's going on. The rules are never explained — you learn by doing. Levels start simple and build up to tricky spatial puzzles. Complete all 7 to win.

---

## Controls

| Key | Action |
|-----|--------|
| `W` / `↑` | Move up |
| `S` / `↓` | Move down |
| `A` / `←` | Move left |
| `D` / `→` | Move right |
| `Ctrl+Z` | Undo |
| `R` | Reset level |
| `Ctrl+R` | Restart game |
| `H` | Toggle hints |

---

## Level 1 — Color Echo (8×8) ★☆☆☆☆

Move your cursor around the grid. Colored source cells and gray target cells are scattered on the board. When you step onto a **gray cell**, it gets painted with the color of the cell you just left. Carry colors from source cells to paint all gray cells.

**Win:** No gray cells remain.

---

## Level 2 — Flood Walker (8×8) ★★☆☆☆

The grid is filled with two colors (cyan and orange). Every cell you walk onto **toggles** between the two colors. Plan your path carefully — retracing your steps undoes your work.

**Win:** The entire grid is one uniform color.

---

## Level 3 — Ice Slide (8×8) ★★☆☆☆

You slide on ice — pressing an arrow key sends you **gliding in that direction until you hit a wall or the edge**. You don't stop after one step. Green gems are on the grid; slide through them to collect them. Use walls as stopping points to position yourself.

**Win:** All green gems collected.

---

## Level 4 — Gem Collector (8×8) ★★★☆☆

Navigate a maze of walls. Yellow gems are scattered throughout. Walk into a gem to collect it. All gems are reachable from the start.

**Win:** All yellow gems collected.

---

## Level 5 — Teleport Maze (8×8) ★★★☆☆

Navigate a maze to reach the **green exit cell**. Colored cells (red, blue) are **teleporters** — step on one and you warp to the other cell of the same color. Use teleporters to bypass walls.

**Win:** Reach the green exit.

---

## Level 6 — Mirror Walk (8×8) ★★★★☆

You control **two green blocks** at the same time. One moves **normally** with your arrow keys. The other moves in the **opposite direction**. Gray walls block each block independently — if a block hits a wall, it **stays put (pinned)** while the other keeps moving. Use walls to pin one block and let the other catch up, then align both on the **red destination block**.

**Win:** Both green blocks are on the red block at the same time.

---

## Level 7 — Sokoban (10×10) ★★★★★

Classic Sokoban. Walk into a colored block to **push** it one step in your direction. Blocks cannot be pulled — only pushed. If a wall, another block, or the edge is behind it, the push fails. Push each colored block onto its **matching target marker** (same color family).

| Block | Target |
|-------|--------|
| Red | Brown |
| Blue | Teal |

**Win:** Every block sits on its matching target.

---

## Tips

- **Undo freely** — `Ctrl+Z` lets you experiment without consequence.
- **Observe first** — move once and watch what changes before committing to a plan.
- **Walls are tools** — especially in levels 3 and 6, walls help you control movement.
- **Reset if stuck** — press `R` to restart the current level with a clean slate.