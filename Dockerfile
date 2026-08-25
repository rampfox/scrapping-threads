FROM python:3.11-slim

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# Skip playwright's built-in dependency installer (kita install manual)
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

WORKDIR /app

# Install semua system dependency Chromium secara manual
# (playwright --with-deps gagal di Debian Trixie karena rename package font)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Networking & certs
    ca-certificates \
    wget \
    gnupg \
    # Fonts - nama baru di Debian Trixie (bukan ttf-unifont / ttf-ubuntu-font-family)
    fonts-liberation \
    fonts-unifont \
    fonts-ubuntu \
    fonts-noto-color-emoji \
    # Chromium system libs
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    # Audio - nama baru di Debian Trixie (bukan libasound2)
    libasound2t64 \
    # Pango / rendering
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxshmfence1 \
    # Tambahan yang dibutuhkan Chromium headless
    libvulkan1 \
    libegl1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium TANPA --with-deps
# (dependency sudah diinstall manual di atas)
RUN playwright install chromium

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
