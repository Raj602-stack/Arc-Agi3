# ── Build stage: install dependencies with uv ──
FROM python:3.12-slim AS builder

# System deps for building native wheels (numpy, pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual env (no dev deps, no project itself)
RUN uv sync --frozen --no-install-project

# Copy the rest of the project
COPY . .

# Install the project itself
RUN uv sync --frozen


# ── Runtime stage: lean image ──
FROM python:3.12-slim AS runtime

# Pillow runtime deps + SDL2 stubs (in case any game engine touches pygame at import)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libjpeg62-turbo \
    libpng16-16 \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire app + venv from builder
COPY --from=builder /app /app

# Make sure the venv's Python is on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default port (override at runtime via -e PORT=XXXX)
ENV PORT=8080
ENV HOST=0.0.0.0

# Ensure environment_files directory exists (games live here)
RUN mkdir -p /app/environment_files

# Expose the port (Docker doesn't expand ENV vars in EXPOSE, must be literal)
EXPOSE 8080

# start.sh is already copied via COPY . . above; ensure it's executable
RUN chmod +x start.sh

# Production server: gunicorn + eventlet via start.sh
# Reads $PORT at runtime (AWS, Railway, or default 8080)
CMD ["./start.sh"]
