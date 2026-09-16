# Stage 1: Build (Set up the environment and download the dependencies)
FROM python:3.12-slim AS builder

# Officially installs UV inside the container
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN pip install uv

# Sets the internal working directory
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc pkg-config libcairo2-dev && rm -rf /var/lib/apt/lists/*

# Copy the dependency files first (optimizes the Docker cache)
COPY pyproject.toml uv.lock ./

# Installs the project's dependencies in a synchronized manner within the isolated ecosystem
# The --no-install-project flag ensures that only the libraries are downloaded during this step
RUN uv sync --frozen --no-install-project --exact

# Stage 2: Post-Production (Light, Clean Final Image)
FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libcairo2 && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/app/.venv

# Copies the entire virtual environment (.venv) that the build stage prepared
ENV PATH="/app/.venv/bin:$PATH"

# Prevents Python from writing .pyc files and forces output directly to the terminal (good for logs)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy the .venv from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the rest of the application code into the container
COPY . .

# Exposes the API's default port
EXPOSE 8000
