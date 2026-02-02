# Production-Grade Freqtrade Docker Image
# Base: FreqAI enabled (LightGBMRegressor support)
# Features: State recovery, health checks, structured logging
# Target: 24/7 market-neutral statistical arbitrage

FROM freqtradeorg/freqtrade:develop_freqai

# Install additional utilities for crash recovery and monitoring
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    python3-requests \
    && rm -rf /var/lib/apt/lists/*

# Production environment variables
ENV OMP_NUM_THREADS=2
ENV NUMEXPR_MAX_THREADS=2
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC
ENV LOG_LEVEL=INFO

WORKDIR /freqtrade

# Copy state recovery script
COPY scripts/state_recovery.py /freqtrade/scripts/state_recovery.py
RUN chmod +x /freqtrade/scripts/state_recovery.py

# Copy structured logging config
COPY scripts/logging_config.py /freqtrade/scripts/logging_config.py

# Health check endpoint
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8080/api/v1/ping || exit 1
