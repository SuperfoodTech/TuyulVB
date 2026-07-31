# ==============================================================================
# Dockerfile for FoodMaster Auto Open & Auto Close ShopeeFood Bot
# Multi-Arch Support: Native ARM64 (Raspberry Pi 5) & AMD64 (x86 Server)
# ==============================================================================

FROM python:3.12-slim-bookworm

# Set Environment Variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Jakarta \
    HEADLESS_MODE=True

# Install system dependencies including Chromium, ChromeDriver & tzdata
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    tzdata \
    curl \
    ca-certificates \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Copy requirements file and install Python packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code into container
COPY . /app/

# Ensure data and chromeprofile directories exist
RUN mkdir -p /app/data /app/chromeprofile

# Expose REST API port
EXPOSE 8000

# Default command: Run unified REST API Server & Auto-OC Bot Scheduler
CMD ["python3", "api_server.py"]
