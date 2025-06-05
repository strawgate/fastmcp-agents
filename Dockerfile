# Use Python 3.10 as the base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY README.md .

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Install dependencies using UV
RUN uv sync

# Set up entrypoint
ENTRYPOINT ["uv", "run", "fastmcp_agents"]

# Default command (can be overridden)
CMD ["--help"] 