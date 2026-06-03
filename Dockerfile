# Use Ubuntu 22.04 as base image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PULSE_SERVER=unix:/tmp/pulse-socket

# Update package list and install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    portaudio19-dev \
    pulseaudio \
    pulseaudio-utils \
    alsa-utils \
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    festival \
    festvox-kallpc16k \
    sox \
    libsox-fmt-all \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install PyInstaller for binary creation
RUN pip3 install pyinstaller

# Copy application files
COPY agent_w.py .

# Create a user for running the application
RUN useradd -m -s /bin/bash voiceuser && \
    chown -R voiceuser:voiceuser /app

# Switch to non-root user
USER voiceuser

# Default command
CMD ["python3", "agent_w.py"]
