"""
web/server.py — Ethara AI × ARC AGI-3 Web Runner.

Admin credentials (override via environment variables):
    ADMIN_USERNAME  (default: admin)
    ADMIN_PASSWORD  (default: 12345)

Drop any ARC-AGI game (game.py + metadata.json) into environment_files/<game>/<version>/
and this server auto-discovers it, spins up sessions, and serves a browser-based player.

No hardcoded game IDs, level names, or hints. Everything is read from the
environment files and the running game engine at runtime.

Usage:
    python web/server.py                                        # from project root
    python -m web.server                                        # module style
    PORT=3000 python web/server.py                              # custom port
    gunicorn --worker-class eventlet -w 1 web.server:app        # production
"""

# ---------------------------------------------------------------------------
# Eventlet monkey-patching — MUST happen before any other imports.
# When running under gunicorn with --worker-class eventlet, the worker does
# its own patching, but importing eventlet early ensures the stdlib is
# patched before Flask/SocketIO/requests touch it.
# ---------------------------------------------------------------------------
try:
    import eventlet
    eventlet.monkey_patch()
except ImportError:
    pass  # eventlet not installed — fall back to threading mode

import base64
import glob
import io
import json
import logging
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from functools import wraps

import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room

# ---------------------------------------------------------------------------
# Project root — one level up from web/
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import arc_agi
from arcengine import GameAction

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask + SocketIO
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "web" / "templates"),
    static_folder=str(PROJECT_ROOT / "web" / "static"),
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ethara-arc-dev-key")

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

# ---------------------------------------------------------------------------
# Admin credentials (override via env vars for production)
# ---------------------------------------------------------------------------
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "12345")


def require_admin(f):
    """Decorator that checks admin credentials from JSON body or query params."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Try JSON body first, then query params
        username = None
        password = None
        if request.is_json:
            data = request.get_json(silent=True) or {}
            username = data.get("username")
            password = data.get("password")
        if not username:
            username = request.args.get("username")
            password = request.args.get("password")
        if not username:
            # Also check form data
            username = request.form.get("username")
            password = request.form.get("password")

        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            return jsonify({"error": "Invalid admin credentials"}), 401
        return f(*args, **kwargs)
    return decorated

# Determine async mode: prefer eventlet (required for gunicorn production),
# fall back to threading for local dev.
_async_mode = "eventlet" if "eventlet" in sys.modules else "threading"
logger.info(f"SocketIO async_mode: {_async_mode}")

socketio = SocketIO(
    app,
    cors_allowed_origins=CORS_ORIGINS,
    async_mode=_async_mode,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1_000_000,
)

# ---------------------------------------------------------------------------
# ARC 16-color palette → RGB (matches the retro CRT aesthetic)
# ---------------------------------------------------------------------------
ARC_PALETTE: dict[int, tuple[int, int, int]] = {
    0:  (235, 235, 220),   # white / empty → warm cream
    1:  (190, 195, 205),   # light gray
    2:  (145, 148, 160),   # gray
    3:  (100, 105, 118),   # dark gray
    4:  (65,  68,  82),    # charcoal
    5:  (35,  38,  50),    # near-black
    6:  (255, 40,  170),   # magenta
    7:  (255, 120, 210),   # pink
    8:  (240, 50,  40),    # red
    9:  (30,  140, 255),   # blue
    10: (50,  210, 240),   # cyan
    11: (255, 220, 20),    # yellow
    12: (255, 145, 25),    # orange
    13: (190, 20,  65),    # crimson
    14: (30,  210, 60),    # green
    15: (165, 85,  235),   # purple
}

# ---------------------------------------------------------------------------
# Environment directory
# ---------------------------------------------------------------------------
# On Railway, mount a persistent volume and set ENVIRONMENTS_DIR to its path
# (e.g. /data/environment_files). Uploaded games will survive redeploys.
# Locally, defaults to the bundled environment_files/ in the project root.
_BUNDLED_ENVS = PROJECT_ROOT / "environment_files"
ENVIRONMENTS_DIR = os.environ.get("ENVIRONMENTS_DIR", str(_BUNDLED_ENVS))

# On first boot with a persistent volume, copy bundled games into it so they
# are available even though the volume starts empty.
if ENVIRONMENTS_DIR != str(_BUNDLED_ENVS) and _BUNDLED_ENVS.is_dir():
    import shutil
    _dest = Path(ENVIRONMENTS_DIR)
    _dest.mkdir(parents=True, exist_ok=True)
    for _game_dir in _BUNDLED_ENVS.iterdir():
        if _game_dir.is_dir():
            _target = _dest / _game_dir.name
            if not _target.exists():
                shutil.copytree(_game_dir, _target)
                logger.info(f"Copied bundled game {_game_dir.name} → {_target}")
            else:
                # Merge: copy any missing version dirs
                for _ver in _game_dir.iterdir():
                    if _ver.is_dir() and not (_target / _ver.name).exists():
                        shutil.copytree(_ver, _target / _ver.name)
                        logger.info(f"Copied bundled version {_game_dir.name}/{_ver.name} → {_target / _ver.name}")

# ---------------------------------------------------------------------------
# Auto-discover games
# ---------------------------------------------------------------------------

def discover_games() -> list[dict]:
    """Scan environment_files/ for all metadata.json files and return game info."""
    games = []
    pattern = os.path.join(ENVIRONMENTS_DIR, "*", "*", "metadata.json")
    for meta_path in sorted(glob.glob(pattern)):
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
            game_id = meta.get("game_id", "")
            if not game_id:
                continue

            # Derive the game directory relative to ENVIRONMENTS_DIR
            version_dir = os.path.dirname(meta_path)
            game_dir = os.path.dirname(version_dir)

            # Find the game .py file (first .py in the version dir)
            py_files = glob.glob(os.path.join(version_dir, "*.py"))
            game_py = py_files[0] if py_files else None

            games.append({
                "game_id": game_id,
                "metadata": meta,
                "version_dir": version_dir,
                "game_dir": game_dir,
                "game_py": game_py,
                "tags": meta.get("tags", []),
                "default_fps": meta.get("default_fps", 10),
                "baseline_actions": meta.get("baseline_actions", []),
            })
            logger.info(f"Discovered game: {game_id} at {version_dir}")
        except Exception as e:
            logger.warning(f"Failed to read {meta_path}: {e}")
    return games


# Run discovery at import time
DISCOVERED_GAMES = discover_games()
GAME_INDEX = {g["game_id"]: g for g in DISCOVERED_GAMES}

# ---------------------------------------------------------------------------
# Frame rendering
# ---------------------------------------------------------------------------

def frame_to_png_base64(frame: np.ndarray, scale: int = 8) -> str:
    """Convert a 64×64 ARC int8 frame to a base64-encoded PNG."""
    try:
        from PIL import Image
    except ImportError:
        return _frame_to_raw_base64(frame, scale)

    h, w = frame.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for val, col in ARC_PALETTE.items():
        mask = frame == val
        rgb[mask] = col

    img = Image.fromarray(rgb, "RGB")
    img = img.resize((w * scale, h * scale), Image.NEAREST)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _frame_to_raw_base64(frame: np.ndarray, scale: int = 8) -> str:
    """Fallback when Pillow isn't available: raw RGB bytes."""
    h, w = frame.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for val, col in ARC_PALETTE.items():
        mask = frame == val
        rgb[mask] = col
    rgb_scaled = np.repeat(np.repeat(rgb, scale, axis=0), scale, axis=1)
    return base64.b64encode(rgb_scaled.tobytes()).decode("ascii")


def frame_to_grid_json(frame: np.ndarray) -> list[list[int]]:
    """Return the raw frame as a 2-D list of ints for the client to render."""
    return frame.tolist()


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------
game_sessions: dict[str, dict] = {}
SESSION_TIMEOUT = 3600  # 1 hour


def create_session(game_id: str, seed: int = 0) -> dict:
    """Create a new game session for any discovered game."""
    if game_id not in GAME_INDEX:
        raise ValueError(f"Unknown game: {game_id}. Available: {list(GAME_INDEX)}")

    session_id = str(uuid.uuid4())[:8]

    arc = arc_agi.Arcade(environments_dir=ENVIRONMENTS_DIR)
    env = arc.make(game_id, seed=seed)
    if env is None:
        raise RuntimeError(f"Could not create environment for {game_id}")

    frame_data = env.reset()
    if frame_data is None:
        raise RuntimeError("env.reset() returned None")

    session = {
        "id": session_id,
        "game_id": game_id,
        "arc": arc,
        "env": env,
        "frame_data": frame_data,
        "seed": seed,
        "total_actions": 0,
        "created_at": time.time(),
        "last_active": time.time(),
        "state": "NOT_FINISHED",
        "levels_completed": 0,
        "total_levels": 0,
        "available_actions": [],
        "player_name": None,
    }

    _sync_state(session)
    game_sessions[session_id] = session
    logger.info(f"Session {session_id} created for {game_id} seed={seed}")
    return session


def _sync_state(session: dict):
    """Pull latest state from the engine into our session dict."""
    fd = session["frame_data"]
    if fd is None:
        return

    session["state"] = fd.state.value if hasattr(fd.state, "value") else str(fd.state)
    session["levels_completed"] = getattr(fd, "levels_completed", 0)

    # Total levels — try to read from the game object
    total = getattr(fd, "total_levels", 0)
    if total == 0:
        try:
            game_obj = session["env"]._game
            total = len(getattr(game_obj, "_levels", []))
        except Exception:
            pass
    if total > 0:
        session["total_levels"] = total

    if hasattr(fd, "available_actions") and fd.available_actions is not None and len(fd.available_actions) > 0:
        session["available_actions"] = list(fd.available_actions)

    session["last_active"] = time.time()


def get_session_state(session: dict) -> dict:
    """Serialize session state for the client."""
    fd = session["frame_data"]

    frame_b64 = ""
    grid = []
    frame_h = 0
    frame_w = 0
    if fd is not None and fd.frame is not None and len(fd.frame) > 0:
        frame_b64 = frame_to_png_base64(fd.frame[0])
        grid = frame_to_grid_json(fd.frame[0])
        frame_h, frame_w = fd.frame[0].shape

    return {
        "session_id": session["id"],
        "game_id": session["game_id"],
        "seed": session["seed"],
        "state": session["state"],
        "levels_completed": session["levels_completed"],
        "total_levels": session["total_levels"],
        "total_actions": session["total_actions"],
        "available_actions": session["available_actions"],
        "frame": frame_b64,
        "grid": grid,
        "frame_width": frame_w,
        "frame_height": frame_h,
        "player_name": session.get("player_name"),
    }


def perform_action(session: dict, action: GameAction, data=None) -> dict:
    """Execute one game action and return the new state."""
    env = session["env"]
    if data is not None:
        session["frame_data"] = env.step(action, data=data)
    else:
        session["frame_data"] = env.step(action)
    session["total_actions"] += 1
    _sync_state(session)
    return get_session_state(session)


def restart_session(session: dict) -> dict:
    """Full restart — back to level 1."""
    game_id = session["game_id"]
    seed = session["seed"]
    arc = session["arc"]

    env = arc.make(game_id, seed=seed)
    frame_data = env.reset()

    session["env"] = env
    session["frame_data"] = frame_data
    session["total_actions"] = 0
    session["levels_completed"] = 0
    session["state"] = "NOT_FINISHED"
    _sync_state(session)

    logger.info(f"Session {session['id']} restarted")
    return get_session_state(session)


def cleanup_stale_sessions():
    """Remove sessions older than SESSION_TIMEOUT."""
    now = time.time()
    stale = [sid for sid, s in game_sessions.items()
             if now - s["last_active"] > SESSION_TIMEOUT]
    for sid in stale:
        del game_sessions[sid]
        logger.info(f"Cleaned up stale session {sid}")


# ---------------------------------------------------------------------------
# Action mapping  (string name → GameAction enum)
# ---------------------------------------------------------------------------
ACTION_MAP = {
    "up":      GameAction.ACTION1,
    "down":    GameAction.ACTION2,
    "left":    GameAction.ACTION3,
    "right":   GameAction.ACTION4,
    "action1": GameAction.ACTION1,
    "action2": GameAction.ACTION2,
    "action3": GameAction.ACTION3,
    "action4": GameAction.ACTION4,
    "action5": GameAction.ACTION5,
    "action6": GameAction.ACTION6,
    "undo":    GameAction.ACTION7,
    "action7": GameAction.ACTION7,
}


# ═══════════════════════════════════════════════════════════════════════════
#  HTTP ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Main page — game picker + player."""
    return render_template("index.html")


@app.route("/game/<game_id>")
def game_direct(game_id):
    """Direct link to a specific game — serves the same SPA, JS reads the URL."""
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "games": len(DISCOVERED_GAMES),
        "sessions": len(game_sessions),
    }), 200


@app.route("/api/games")
def api_games():
    """Return the list of all discovered games."""
    cleanup_stale_sessions()
    out = []
    for g in DISCOVERED_GAMES:
        out.append({
            "game_id": g["game_id"],
            "tags": g["tags"],
            "default_fps": g["default_fps"],
            "baseline_actions": g["baseline_actions"],
        })
    return jsonify({"games": out})


@app.route("/api/games/<game_id>/metadata")
def api_game_metadata(game_id):
    """Return the raw metadata.json for a specific game."""
    info = GAME_INDEX.get(game_id)
    if not info:
        return jsonify({"error": "Game not found"}), 404
    return jsonify(info["metadata"])


@app.route("/api/sessions")
def api_sessions():
    """List active sessions (debug / admin)."""
    cleanup_stale_sessions()
    out = []
    for sid, s in game_sessions.items():
        out.append({
            "id": sid,
            "game_id": s["game_id"],
            "seed": s["seed"],
            "state": s["state"],
            "levels_completed": s["levels_completed"],
            "total_actions": s["total_actions"],
            "player_name": s.get("player_name"),
            "created_at": s["created_at"],
            "last_active": s["last_active"],
        })
    return jsonify({"sessions": out})


@app.route("/api/sessions/<session_id>/scorecard")
def api_scorecard(session_id):
    session = game_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    try:
        scorecard = str(session["arc"].get_scorecard())
    except Exception as e:
        scorecard = f"Could not retrieve scorecard: {e}"
    return jsonify({"scorecard": scorecard})


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


# ═══════════════════════════════════════════════════════════════════════════
#  WEBSOCKET EVENTS
# ═══════════════════════════════════════════════════════════════════════════

@socketio.on("connect")
def on_connect():
    logger.info(f"Client connected: {request.sid}")


@socketio.on("disconnect")
def on_disconnect():
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on("list_games")
def on_list_games(_data=None):
    """Client asks what games are available."""
    out = []
    for g in DISCOVERED_GAMES:
        out.append({
            "game_id": g["game_id"],
            "tags": g["tags"],
            "default_fps": g["default_fps"],
            "baseline_actions": g["baseline_actions"],
        })
    emit("games_list", {"games": out})


@socketio.on("create_game")
def on_create_game(data):
    """Create a new session for the requested game."""
    try:
        game_id = data.get("game_id", "")
        seed = int(data.get("seed", 0))
        player_name = data.get("player_name", "Anonymous")

        # If no game_id given, pick the first discovered game
        if not game_id and DISCOVERED_GAMES:
            game_id = DISCOVERED_GAMES[0]["game_id"]

        cleanup_stale_sessions()

        session = create_session(game_id=game_id, seed=seed)
        session["player_name"] = player_name
        session["socket_sid"] = request.sid
        join_room(session["id"])

        state = get_session_state(session)
        emit("game_created", state)
        emit("frame_update", state)

        logger.info(f"Game {game_id} created for {player_name} "
                     f"(session={session['id']}, seed={seed})")

    except Exception as e:
        logger.error(f"Error creating game: {e}", exc_info=True)
        emit("error", {"message": str(e)})


@socketio.on("join_game")
def on_join_game(data):
    """Rejoin an existing session (e.g. after page refresh)."""
    try:
        session_id = data.get("session_id")
        session = game_sessions.get(session_id)
        if not session:
            emit("error", {"message": "Session not found. Create a new game."})
            return

        session["socket_sid"] = request.sid
        join_room(session_id)

        state = get_session_state(session)
        emit("game_joined", state)
        emit("frame_update", state)

    except Exception as e:
        logger.error(f"Error joining: {e}", exc_info=True)
        emit("error", {"message": str(e)})


@socketio.on("action")
def on_action(data):
    """Handle a game action."""
    try:
        session_id = data.get("session_id")
        action_name = data.get("action")
        action_data = data.get("data")

        session = game_sessions.get(session_id)
        if not session:
            emit("error", {"message": "Session not found"})
            return

        if session["state"] == "WON":
            emit("frame_update", get_session_state(session))
            return

        game_action = ACTION_MAP.get(action_name)
        if game_action is None:
            emit("error", {"message": f"Unknown action: {action_name}"})
            return

        prev_levels = session["levels_completed"]

        state = perform_action(session, game_action, data=action_data)

        # Detect level completion
        if session["levels_completed"] > prev_levels:
            emit("level_complete", {
                "level": prev_levels + 1,
                "new_level": session["levels_completed"] + 1,
                "total_levels": session["total_levels"],
            })

        # Detect game win
        if session["state"] == "WON":
            try:
                scorecard = str(session["arc"].get_scorecard())
            except Exception:
                scorecard = "N/A"
            emit("game_won", {
                "total_actions": session["total_actions"],
                "scorecard": scorecard,
            })

        emit("frame_update", state)

    except Exception as e:
        logger.error(f"Error in action: {e}", exc_info=True)
        emit("error", {"message": str(e)})


@socketio.on("restart")
def on_restart(data):
    """Full game restart."""
    try:
        session_id = data.get("session_id")
        session = game_sessions.get(session_id)
        if not session:
            emit("error", {"message": "Session not found"})
            return

        state = restart_session(session)
        emit("game_restarted", state)
        emit("frame_update", state)

    except Exception as e:
        logger.error(f"Error restarting: {e}", exc_info=True)
        emit("error", {"message": str(e)})


@socketio.on("reset_level")
def on_reset_level(data):
    """Reset current level only."""
    try:
        session_id = data.get("session_id")
        session = game_sessions.get(session_id)
        if not session:
            emit("error", {"message": "Session not found"})
            return

        session["frame_data"] = session["env"].reset()
        session["total_actions"] = 0
        _sync_state(session)

        state = get_session_state(session)
        emit("level_reset", state)
        emit("frame_update", state)

    except Exception as e:
        logger.error(f"Error resetting level: {e}", exc_info=True)
        emit("error", {"message": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
#  UPLOAD ENDPOINT — drop game files at runtime
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/upload", methods=["POST"])
def upload_game():
    """
    Upload a game.py + metadata.json to create a new environment on the fly.

    Expects multipart form with:
      - game_py:      the game Python file
      - metadata:     the metadata.json file
      - game_name:    (optional) folder name, defaults to game_id from metadata
    """
    try:
        if "metadata" not in request.files:
            return jsonify({"error": "metadata.json file required"}), 400
        if "game_py" not in request.files:
            return jsonify({"error": "game .py file required"}), 400

        meta_file = request.files["metadata"]
        game_file = request.files["game_py"]

        meta = json.loads(meta_file.read().decode("utf-8"))
        game_id = meta.get("game_id", "")
        if not game_id:
            return jsonify({"error": "metadata.json must contain game_id"}), 400

        # Derive folder structure: environment_files/<base_name>/<version>/
        # e.g. game_id "pm07-v1" → folder "pm07" version "v1"
        parts = game_id.rsplit("-", 1)
        base_name = parts[0] if len(parts) == 2 else game_id
        version = parts[1] if len(parts) == 2 else "v1"

        # Allow override via form field
        folder_name = request.form.get("game_name", base_name)

        version_dir = Path(ENVIRONMENTS_DIR) / folder_name / version
        version_dir.mkdir(parents=True, exist_ok=True)

        # Write metadata.json
        meta_path = version_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        # Write game .py file (preserve original filename)
        py_filename = game_file.filename or f"{base_name}.py"
        py_path = version_dir / py_filename
        game_file.seek(0)
        py_path.write_bytes(game_file.read())

        # Re-discover games
        global DISCOVERED_GAMES, GAME_INDEX
        DISCOVERED_GAMES = discover_games()
        GAME_INDEX = {g["game_id"]: g for g in DISCOVERED_GAMES}

        logger.info(f"Uploaded game {game_id} to {version_dir}")

        return jsonify({
            "status": "ok",
            "game_id": game_id,
            "path": str(version_dir),
            "games_available": [g["game_id"] for g in DISCOVERED_GAMES],
        }), 201

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    """Verify admin credentials. Returns 200 on success, 401 on failure."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return jsonify({"status": "ok", "message": "Authenticated"}), 200
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/admin/games", methods=["GET"])
@require_admin
def admin_list_games():
    """List all games with their file paths (admin only)."""
    global DISCOVERED_GAMES, GAME_INDEX
    DISCOVERED_GAMES = discover_games()
    GAME_INDEX = {g["game_id"]: g for g in DISCOVERED_GAMES}

    out = []
    for g in DISCOVERED_GAMES:
        out.append({
            "game_id": g["game_id"],
            "tags": g["tags"],
            "version_dir": g["version_dir"],
        })
    return jsonify({"games": out})


@app.route("/api/admin/games/<game_id>", methods=["DELETE"])
@require_admin
def admin_delete_game(game_id):
    """
    Delete a game by game_id. Removes the version directory and the parent
    game directory if it becomes empty. Also kills any active sessions for
    that game.
    """
    global DISCOVERED_GAMES, GAME_INDEX

    info = GAME_INDEX.get(game_id)
    if not info:
        return jsonify({"error": f"Game '{game_id}' not found"}), 404

    version_dir = info["version_dir"]
    game_dir = info["game_dir"]

    try:
        # Remove the version directory (e.g. environment_files/pm07/v1/)
        if os.path.isdir(version_dir):
            shutil.rmtree(version_dir)
            logger.info(f"Deleted version dir: {version_dir}")

        # If the parent game dir is now empty, remove it too
        if os.path.isdir(game_dir) and not os.listdir(game_dir):
            shutil.rmtree(game_dir)
            logger.info(f"Deleted empty game dir: {game_dir}")

        # Kill active sessions for this game
        stale = [sid for sid, s in game_sessions.items() if s["game_id"] == game_id]
        for sid in stale:
            del game_sessions[sid]
            logger.info(f"Killed session {sid} for deleted game {game_id}")

        # Re-discover
        DISCOVERED_GAMES = discover_games()
        GAME_INDEX = {g["game_id"]: g for g in DISCOVERED_GAMES}

        return jsonify({
            "status": "ok",
            "deleted": game_id,
            "games_remaining": [g["game_id"] for g in DISCOVERED_GAMES],
        }), 200

    except Exception as e:
        logger.error(f"Error deleting game {game_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    logger.info(f"Ethara AI × ARC AGI-3 Web Runner starting on {host}:{port}")
    logger.info(f"Environment dir: {ENVIRONMENTS_DIR}")
    logger.info(f"Discovered games: {[g['game_id'] for g in DISCOVERED_GAMES]}")
    logger.info(f"Debug: {debug}")

    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
