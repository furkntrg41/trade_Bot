#!/bin/bash
# Production Deployment Command Script
# ====================================
# Execute on Hetzner VPS to deploy bot
# 
# Usage: bash deploy_production.sh
# 
# This script:
# 1. Stops the current bot
# 2. Rebuilds Docker image with production Dockerfile
# 3. Creates .env.production from template
# 4. Starts bot with state recovery
# 5. Monitors initial startup

set -e

echo "========================================"
echo "🚀 PRODUCTION DEPLOYMENT SCRIPT"
echo "========================================"
echo ""

BOT_DIR="/root/freqtrade_bot"
COMPOSE_FILE="$BOT_DIR/docker-compose.production.yml"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Verify files
echo "[1/7] 📋 Verifying files..."
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}ERROR: docker-compose.production.yml not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Production compose file found${NC}"

# Step 2: Stop current bot
echo ""
echo "[2/7] 🛑 Stopping current bot..."
cd "$BOT_DIR"
docker-compose -f docker-compose.production.yml stop freqtrade_bot 2>/dev/null || true
sleep 2
echo -e "${GREEN}✅ Bot stopped${NC}"

# Step 3: Create .env.production if not exists
echo ""
echo "[3/7] 🔐 Checking .env.production..."
if [ ! -f "$BOT_DIR/.env.production" ]; then
    echo -e "${YELLOW}⚠️  .env.production not found${NC}"
    echo "    Creating from template..."
    cp "$BOT_DIR/.env.production.template" "$BOT_DIR/.env.production"
    chmod 600 "$BOT_DIR/.env.production"
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env.production with your API keys!${NC}"
    echo "    Command: nano $BOT_DIR/.env.production"
    exit 1
else
    chmod 600 "$BOT_DIR/.env.production"
    echo -e "${GREEN}✅ .env.production found and secured${NC}"
fi

# Step 4: Rebuild Docker image
echo ""
echo "[4/7] 🔨 Rebuilding Docker image..."
echo "    This may take 2-3 minutes..."
docker-compose -f "$COMPOSE_FILE" build --no-cache 2>&1 | tail -5
echo -e "${GREEN}✅ Docker image rebuilt${NC}"

# Step 5: Verify configuration
echo ""
echo "[5/7] ✔️  Verifying configuration..."
echo "    Pairs found: $(cat $BOT_DIR/pairs_config.json | grep -c '"pair_id"')"
echo "    Trading mode: $(cat $BOT_DIR/config.json | grep '"mode"' | head -1)"
echo -e "${GREEN}✅ Configuration verified${NC}"

# Step 6: Start bot
echo ""
echo "[6/7] 🚀 Starting bot with state recovery..."
docker-compose -f "$COMPOSE_FILE" up -d freqtrade_bot
echo "    Waiting for startup..."
sleep 5
echo -e "${GREEN}✅ Bot started${NC}"

# Step 7: Monitor startup
echo ""
echo "[7/7] 📊 Monitoring startup (30 seconds)..."
echo "========================================"
for i in {1..30}; do
    if docker ps | grep -q "freqtrade_bot.*healthy"; then
        echo -e "${GREEN}✅ Bot is HEALTHY!${NC}"
        echo ""
        echo "========================================"
        echo "🎉 DEPLOYMENT SUCCESSFUL"
        echo "========================================"
        echo ""
        echo "📊 Bot Status:"
        docker ps | grep freqtrade_bot
        echo ""
        echo "📈 Monitor logs:"
        echo "  docker logs -f freqtrade_bot"
        echo ""
        echo "🔍 View API:"
        echo "  curl http://localhost:8080/api/v1/ping"
        echo ""
        echo "✅ Recovery report:"
        echo "  cat /root/freqtrade_bot/user_data/logs/recovery_report.json"
        echo ""
        exit 0
    fi
    
    status=$(docker ps | grep freqtrade_bot | grep -oE 'Up.*|Exited.*' || echo "Not running")
    printf "\r  Status: %s [%d/30 seconds]" "$status" "$i"
    sleep 1
done

echo ""
echo -e "${YELLOW}⚠️  Bot is still starting (may need more time)${NC}"
echo "    Check logs: docker logs freqtrade_bot"
echo ""

# Final check
if docker ps | grep -q freqtrade_bot; then
    echo -e "${GREEN}✅ Container is running${NC}"
    echo ""
    echo "📊 Last 20 log lines:"
    docker logs --tail 20 freqtrade_bot
else
    echo -e "${RED}❌ Container failed to start${NC}"
    echo ""
    echo "📋 Full logs:"
    docker logs freqtrade_bot
    exit 1
fi

echo ""
echo "========================================"
echo "Deployment script finished"
echo "========================================"
