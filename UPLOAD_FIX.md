# AGI-3 Upload Fix - Debugging Guide

## Problem
When trying to upload AGI-3 game files (`.py` + `metadata.json`), the system shows an error:
```
localhost:8080 says
Upload error: metadata.json file required
OK
```

## What Was Fixed

### 1. **Backend Improvements** (`web/server.py`)

- ✅ Added `MAX_CONTENT_LENGTH = 50MB` to Flask config (was unlimited/default 16MB)
- ✅ Added extensive validation and logging to `upload_game()` endpoint
- ✅ Added debug endpoint `/api/upload/debug` to test what server receives
- ✅ Better error messages showing exactly what's missing

### 2. **Frontend Improvements** (`web/templates/landing.html`)

- ✅ Added console logging throughout upload process
- ✅ Added file validation (extension, size, existence)
- ✅ Improved error handling for non-JSON responses
- ✅ Added toast notifications for upload errors
- ✅ Better FormData construction with explicit filenames

### 3. **Test Page Created** (`web/templates/upload-test.html`)

Created isolated test page at `/upload-test` to debug the issue.

## How to Debug the Issue

### Step 1: Use the Upload Test Page

1. Start the server: `python web/server.py`
2. Navigate to: http://localhost:8080/upload-test
3. Select your `.py` and `.json` files
4. Click **"Test File Selection"** - this will verify:
   - Files are selected correctly
   - Files have content (size > 0)
   - File extensions are correct
   - FormData can be created
5. Click **"Debug Upload"** - this sends to `/api/upload/debug` which shows what the server receives
6. Click **"Upload to /api/upload"** - this attempts the real upload

**Check the console log** on the test page - it shows every step and any errors.

### Step 2: Check Server Logs

When you attempt an upload, the server now logs:
```
[INFO] Upload request files: ['game_py', 'metadata']
[INFO] Upload request form: []
[INFO] Uploading: metadata=game_metadata.json, game=my_game.py
```

If you see:
```
[ERROR] metadata file not in request.files
```

This means the browser isn't sending the files correctly.

### Step 3: Check Browser Console

Open the landing page (`/`) and try uploading. Open browser DevTools (F12) and check the Console tab. You should see:
```
Upload button clicked
Python file: File {name: "game.py", size: 1234, ...}
JSON file: File {name: "metadata.json", size: 567, ...}
Files validated, creating FormData
FormData created, sending request to /api/upload
  game_py: game.py size: 1234 bytes
  metadata: metadata.json size: 567 bytes
Response status: 201 Created
Response data: {status: "ok", game_id: "pm07-v1", ...}
```

If files are `undefined` or `null`, the file inputs aren't working.

## Common Issues & Solutions

### Issue 1: "metadata.json file required"

**Cause:** Files aren't being sent to server, or FormData field names are wrong.

**Solution:**
1. Check browser console for JavaScript errors
2. Verify files are selected (not empty file inputs)
3. Use the test page to isolate the issue
4. Check that form field names match: `game_py` and `metadata`

### Issue 2: Empty File Upload

**Cause:** File input is triggering upload before file is loaded.

**Solution:**
- Make sure upload button is disabled until both files are selected
- Check that `files.length > 0` before submitting
- Verify file sizes are > 0 bytes

### Issue 3: File Too Large

**Cause:** File exceeds 50MB limit.

**Solution:**
- Check file sizes in browser console
- Server will now return clear error if file exceeds limit
- Compress/minify game file if needed

### Issue 4: JSON Parse Error

**Cause:** metadata.json has invalid JSON syntax.

**Solution:**
- Validate JSON at https://jsonlint.com/
- Server will now return exact parse error
- Check for trailing commas, missing quotes, etc.

### Issue 5: Missing game_id in metadata.json

**Cause:** The metadata.json doesn't have a `game_id` field.

**Solution:**
```json
{
  "game_id": "my_game-v1",
  "title": "My Game",
  "description": "A test game",
  ...
}
```

The `game_id` field is **required** and should follow format: `name-version` (e.g., `pm07-v1`)

## Sample Valid Files

### metadata.json (minimum required)
```json
{
  "game_id": "test_game-v1",
  "title": "Test Game",
  "description": "A simple test game",
  "author": "Your Name"
}
```

### game.py (minimum required)
```python
"""
A minimal ARC AGI-3 game.
"""
from arcengine import ArcGame, GameEngine, GameState

class TestGame(ArcGame):
    def init_state(self) -> GameState:
        # Initialize game state
        return GameState(...)
    
    def step(self, action: int, state: GameState) -> GameState:
        # Process action and return new state
        return state

def make_engine() -> GameEngine:
    return GameEngine(TestGame())
```

## API Endpoints

### POST `/api/upload`
Upload a new game.

**Request:** `multipart/form-data`
- `game_py`: The Python game file
- `metadata`: The metadata.json file
- `game_name` (optional): Override folder name

**Response (Success - 201):**
```json
{
  "status": "ok",
  "game_id": "test_game-v1",
  "path": "/path/to/environment_files/test_game/v1",
  "games_available": ["game1-v1", "game2-v1", "test_game-v1"]
}
```

**Response (Error - 400/500):**
```json
{
  "error": "metadata.json file required"
}
```

### POST `/api/upload/debug`
Debug endpoint to see what server receives.

**Response:**
```json
{
  "status": "debug_ok",
  "files": {
    "game_py": {
      "filename": "game.py",
      "content_type": "text/x-python",
      "has_content": true
    },
    "metadata": {
      "filename": "metadata.json",
      "content_type": "application/json",
      "has_content": true
    }
  },
  "form": {},
  "content_type": "multipart/form-data; boundary=..."
}
```

## Quick Test with cURL

Test the upload endpoint directly:

```bash
curl -X POST http://localhost:8080/api/upload \
  -F "game_py=@/path/to/game.py" \
  -F "metadata=@/path/to/metadata.json"
```

Expected response:
```json
{"status":"ok","game_id":"my_game-v1","path":"...","games_available":[...]}
```

## Still Having Issues?

1. **Check the test page:** http://localhost:8080/upload-test
2. **Check server logs** for detailed error messages
3. **Check browser console** for JavaScript errors
4. **Try cURL upload** to isolate browser vs server issues
5. **Verify file permissions** on `environment_files/` directory
6. **Check Flask is running** and accessible at the correct port

## Files Modified

- `web/server.py` - Added validation, logging, debug endpoint
- `web/templates/landing.html` - Improved upload error handling
- `web/templates/upload-test.html` - NEW: Isolated test page
- `web/templates/grid-test.html` - NEW: Grid animation test (unrelated)
- `UPLOAD_FIX.md` - THIS FILE: Documentation