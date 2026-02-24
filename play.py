"""
play.py — Run the PM07 (Pattern Master) game locally.

Usage:
    python play.py                  # Play with default seed 0 in terminal mode
    python play.py --seed 42        # Play with a specific seed
    python play.py --agent          # Run the sample agent (random actions)

Controls (terminal / human play):
    ACTION1 = W / ↑      (Up)
    ACTION2 = S / ↓      (Down)
    ACTION3 = A / ←      (Left)
    ACTION4 = D / →      (Right)
    ACTION7 = Ctrl+Z     (Undo)

All 7 levels use ONLY arrow keys. No Space bar, no mouse clicking.
"""

import argparse
import random
import sys

import arc_agi
from arcengine import GameAction


def play_human(seed: int = 0) -> None:
    """Launch the game in terminal render mode for human play."""
    arc = arc_agi.Arcade(environments_dir="./environment_files")
    env = arc.make("pm07-v1", seed=seed, render_mode="terminal")

    print("=" * 60)
    print("  PM07 — Pattern Master")
    print("  A 7-level hidden-rule grid puzzle game")
    print("=" * 60)
    print()
    print("  Each level has a HIDDEN RULE you must discover!")
    print("  Experiment with the controls to figure out what to do.")
    print()
    print("  Controls: ARROW KEYS ONLY (+ Ctrl+Z to undo)")
    print("    W/↑ = Up    S/↓ = Down    A/← = Left    D/→ = Right")
    print("    Ctrl+Z = Undo    R = Reset Level    Ctrl+R = Restart Game")
    print()
    print("  Level descriptions (SPOILERS — discover them yourself!):")
    print("    1. Color Echo       — move over gray cells to paint them")
    print("    2. Flood Walker     — toggle cells to make grid uniform")
    print("    3. Ice Slide        — slide on ice, collect all gems")
    print("    4. Gem Collector    — navigate a maze, collect all gems")
    print("    5. Teleport Maze    — find the exit using teleporters")
    print("    6. Mirror Walk      — two green blocks, opposite movement, align on red")
    print("    7. Sokoban          — push multiple blocks onto targets")
    print()
    print("  The game is now running in your terminal.")
    print("  Use the keyboard/mouse to play!")
    print("=" * 60)

    # The terminal render mode handles input automatically.
    # If the environment supports interactive mode, it will block here.
    # Otherwise, we provide a simple input loop.
    try:
        input("\nPress Enter to view scorecard when done...\n")
    except (KeyboardInterrupt, EOFError):
        pass

    print(arc.get_scorecard())


def play_agent(seed: int = 0, max_steps: int = 500) -> None:
    """Run a sample random agent against the game."""
    arc = arc_agi.Arcade(environments_dir="./environment_files")
    env = arc.make("pm07-v1", seed=seed, render_mode="terminal")

    rng = random.Random(seed)
    actions = [
        GameAction.ACTION1,
        GameAction.ACTION2,
        GameAction.ACTION3,
        GameAction.ACTION4,
        GameAction.ACTION7,
    ]

    print(f"Running random agent for up to {max_steps} steps (seed={seed})...")
    print()

    for step_num in range(max_steps):
        chosen = rng.choice(actions)
        env.step(chosen)

    print()
    print(f"Agent completed {max_steps} steps.")
    print(arc.get_scorecard())


def play_scripted_demo(seed: int = 0) -> None:
    """Run a short scripted demo showing a few actions on each level."""
    arc = arc_agi.Arcade(environments_dir="./environment_files")
    env = arc.make("pm07-v1", seed=seed, render_mode="terminal")

    print("Running scripted demo...")
    print()

    demo_actions = [
        # Level 1 — move around to paint gray cells
        (GameAction.ACTION4, None),
        (GameAction.ACTION4, None),
        (GameAction.ACTION2, None),
        (GameAction.ACTION2, None),
        (GameAction.ACTION1, None),
        (GameAction.ACTION3, None),
        (GameAction.ACTION4, None),
        (GameAction.ACTION2, None),

        # Try undo
        (GameAction.ACTION7, None),
        # More movement
        (GameAction.ACTION1, None),
        (GameAction.ACTION1, None),
        (GameAction.ACTION4, None),
        (GameAction.ACTION4, None),
        (GameAction.ACTION2, None),
        (GameAction.ACTION3, None),
        (GameAction.ACTION3, None),
        (GameAction.ACTION2, None),
    ]

    for action_id, data in demo_actions:
        if data is not None:
            env.step(action_id, data=data)
        else:
            env.step(action_id)

    print()
    print("Demo complete.")
    print(arc.get_scorecard())


def main():
    parser = argparse.ArgumentParser(
        description="Play PM07 — Pattern Master (ARC-AGI-3 Game)"
    )
    parser.add_argument(
        "--seed", type=int, default=0,
        help="Random seed for level generation (default: 0)"
    )
    parser.add_argument(
        "--agent", action="store_true",
        help="Run the sample random agent instead of human play"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run a short scripted demo"
    )
    parser.add_argument(
        "--steps", type=int, default=500,
        help="Max steps for agent mode (default: 500)"
    )

    args = parser.parse_args()

    if args.agent:
        play_agent(seed=args.seed, max_steps=args.steps)
    elif args.demo:
        play_scripted_demo(seed=args.seed)
    else:
        play_human(seed=args.seed)


if __name__ == "__main__":
    main()
