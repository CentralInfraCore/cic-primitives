# Use a slim, modern Python image
FROM python:3.11-slim

# Set a working directory
WORKDIR /app

# Install system dependencies that might be needed for cryptographic libraries
# and pip-tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    git \
    curl \
    jq \
    && curl -fsSL https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 \
       -o /usr/local/bin/yq && chmod +x /usr/local/bin/yq \
    && rm -rf /var/lib/apt/lists/*

# Trust the mounted project directory (host uid != container uid)
RUN git config --system --add safe.directory /app

# Install pip-tools globally in the container for the setup service to use
RUN pip install --no-cache-dir pip-tools
